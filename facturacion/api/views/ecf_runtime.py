from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import require_current_company
from facturacion.api.permissions import model_permissions
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_runtime import ElectronicFiscalDocumentSerializer
from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.exceptions import ECFCeleryUnavailable, ECFError
from facturacion.ecf.queues import (
    enqueue_check_status,
    enqueue_generate_xml,
    enqueue_retry_submission,
    enqueue_sign_xml,
    enqueue_submit_dgii,
    enqueue_submission_pipeline,
)
from facturacion.ecf.services.dgii_status import DGIIStatusService
from facturacion.ecf.services.dgii_submission import DGIISubmissionService
from facturacion.ecf.services.document_factory import ECFDocumentFactoryService
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.services.signing import ECFSigningService
from facturacion.ecf.services.xml_generation import ECFXMLGenerationService
from facturacion.models import ECFIssuerConfig, ElectronicFiscalDocument, Invoice
from facturacion.permissions import HasRequiredPermissions


class ElectronicFiscalDocumentViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = (
        ElectronicFiscalDocument.objects
        .select_related('invoice', 'credit_note', 'issuer', 'sequence')
        .prefetch_related('events')
        .all()
    )
    serializer_class = ElectronicFiscalDocumentSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('electronicfiscaldocument')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'ecf_type', 'status', 'fiscal_status', 'job_status']
    search_fields = ['encf', 'track_id', 'invoice__invoice_number', 'credit_note__credit_note_number']
    ordering_fields = ['created_at', 'updated_at', 'encf']
    ordering = ['-created_at']

    def _enqueue_or_503(self, enqueue_callable):
        try:
            return enqueue_callable()
        except ECFCeleryUnavailable as exc:
            return Response(
                {
                    'detail': str(exc),
                    'code': 'celery_unavailable',
                    'hint': 'Levanta Redis en localhost:6379 y ejecuta el worker Celery.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    def _can_view_sensitive_fiscal_artifacts(self):
        user = self.request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.has_perm('facturacion.view_ecfeventlog')
            )
        )

    def create(self, request, *args, **kwargs):
        return Response(
            {'detail': 'Usa /api/ecf/documents/create-from-invoice/ para asignar un e-NCF de forma controlada.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=['post'], url_path='create-from-invoice')
    def create_from_invoice(self, request):
        invoice_id = request.data.get('invoice')
        issuer_id = request.data.get('issuer')
        ecf_type = request.data.get('ecf_type')

        if not invoice_id:
            return Response({'invoice': 'La factura es requerida.'}, status=status.HTTP_400_BAD_REQUEST)
        if not issuer_id:
            return Response({'issuer': 'El emisor es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = require_current_company(request)
            invoice = Invoice.objects.get(pk=invoice_id, company=company)
            issuer = ECFIssuerConfig.objects.get(pk=issuer_id, company=company, is_active=True)

            result = ECFDocumentFactoryService().create_for_invoice(invoice, user=request.user, issuer_id=issuer.id, ecf_type=ecf_type)
            if result.error:
                return Response({'detail': result.error}, status=status.HTTP_400_BAD_REQUEST)
            document = result.document

            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK)

        except Invoice.DoesNotExist:
            return Response({'invoice': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        except ECFIssuerConfig.DoesNotExist:
            return Response({'issuer': 'Emisor activo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as exc:
            return Response({'detail': exc.message if hasattr(exc, 'message') else exc.messages}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='generate-xml')
    def generate_xml(self, request, pk=None):
        document = self.get_object()
        validate_xsd = request.data.get('validate_xsd', True)
        if isinstance(validate_xsd, str):
            validate_xsd = validate_xsd.lower() not in ('false', '0', 'no')

        try:
            result = ECFXMLGenerationService().generate(
                document=document,
                user=request.user,
                validate_xsd=bool(validate_xsd),
            )
            serializer = self.get_serializer(result.document)
            data = serializer.data
            data['xsd_validated'] = result.xsd_validated
            return Response(data, status=status.HTTP_200_OK)
        except ECFError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='generate-xml-async')
    def generate_xml_async(self, request, pk=None):
        document = self.get_object()
        validate_xsd = request.data.get('validate_xsd', True)
        if isinstance(validate_xsd, str):
            validate_xsd = validate_xsd.lower() not in ('false', '0', 'no')
        response = self._enqueue_or_503(
            lambda: enqueue_generate_xml(document.id, user_id=request.user.id, validate_xsd=bool(validate_xsd))
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='sign-xml')
    def sign_xml(self, request, pk=None):
        document = self.get_object()
        certificate_policy = ECFCertificateSigningPolicy()
        policy_result = certificate_policy.evaluate(document.issuer)
        if policy_result.blocked:
            document = certificate_policy.record_blocked(document, policy_result, user=request.user)
            return Response(
                {
                    'detail': policy_result.reason,
                    'code': policy_result.code,
                    'certificate_status': document.issuer.certificate_status,
                    'certificate_rnc_match_status': document.issuer.certificate_rnc_match_status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        certificate_policy.log_warnings(document, policy_result, user=request.user)

        certificate_path, certificate_password = resolve_certificate_credentials(document.issuer)
        validate_xsd = request.data.get('validate_xsd', True)
        if isinstance(validate_xsd, str):
            validate_xsd = validate_xsd.lower() not in ('false', '0', 'no')

        if not certificate_path:
            return Response(
                {'detail': 'El emisor no tiene certificado e-CF configurado y no hay fallback ECF_CERTIFICATE_PATH.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ECFSigningService().sign(
                document=document,
                certificate_path=certificate_path,
                certificate_password=certificate_password,
                user=request.user,
                validate_xsd=bool(validate_xsd),
            )
            serializer = self.get_serializer(result.document)
            data = serializer.data
            data['signature_validated'] = result.signature_validated
            data['xsd_validated'] = result.xsd_validated
            return Response(data, status=status.HTTP_200_OK)
        except ECFError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='sign-xml-async')
    def sign_xml_async(self, request, pk=None):
        document = self.get_object()
        validate_xsd = request.data.get('validate_xsd', True)
        if isinstance(validate_xsd, str):
            validate_xsd = validate_xsd.lower() not in ('false', '0', 'no')
        response = self._enqueue_or_503(
            lambda: enqueue_sign_xml(document.id, user_id=request.user.id, validate_xsd=bool(validate_xsd))
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='submit-dgii')
    def submit_dgii(self, request, pk=None):
        document = self.get_object()
        environment = request.data.get('environment')
        force = request.data.get('force', False)
        if isinstance(force, str):
            force = force.lower() in ('true', '1', 'yes', 'si')

        try:
            result = DGIISubmissionService().submit(
                document=document,
                user=request.user,
                environment=environment,
                force=bool(force),
            )
            serializer = self.get_serializer(result.document)
            data = serializer.data
            data['track_id'] = result.track_id
            data['submission_status'] = result.status
            return Response(data, status=status.HTTP_200_OK)
        except ECFError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='submit-dgii-async')
    def submit_dgii_async(self, request, pk=None):
        document = self.get_object()
        force = request.data.get('force', False)
        if isinstance(force, str):
            force = force.lower() in ('true', '1', 'yes', 'si')
        response = self._enqueue_or_503(
            lambda: enqueue_submit_dgii(
                document.id,
                user_id=request.user.id,
                environment=request.data.get('environment'),
                force=bool(force),
            )
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='check-dgii-status')
    def check_dgii_status(self, request, pk=None):
        document = self.get_object()
        environment = request.data.get('environment')

        try:
            result = DGIIStatusService().check(
                document=document,
                user=request.user,
                environment=environment,
            )
            serializer = self.get_serializer(result.document)
            data = serializer.data
            data['dgii_status'] = result.dgii_status
            data['normalized_status'] = result.status
            return Response(data, status=status.HTTP_200_OK)
        except ECFError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='check-dgii-status-async')
    def check_dgii_status_async(self, request, pk=None):
        document = self.get_object()
        response = self._enqueue_or_503(
            lambda: enqueue_check_status(document.id, user_id=request.user.id, environment=request.data.get('environment'))
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='process-async')
    def process_async(self, request, pk=None):
        document = self.get_object()
        validate_xsd = request.data.get('validate_xsd', True)
        if isinstance(validate_xsd, str):
            validate_xsd = validate_xsd.lower() not in ('false', '0', 'no')
        response = self._enqueue_or_503(
            lambda: enqueue_submission_pipeline(
                document.id,
                user_id=request.user.id,
                validate_xsd=bool(validate_xsd),
                environment=request.data.get('environment'),
            )
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED if result.get('enqueued') else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='retry-submission-async')
    def retry_submission_async(self, request, pk=None):
        document = self.get_object()
        response = self._enqueue_or_503(
            lambda: enqueue_retry_submission(document.id, user_id=request.user.id, environment=request.data.get('environment'))
        )
        if isinstance(response, Response):
            return response
        result = response
        return Response(result, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'], url_path='audit-artifact/(?P<artifact>xml|signed-xml|dgii-request|dgii-response)')
    def audit_artifact(self, request, pk=None, artifact=None):
        if not self._can_view_sensitive_fiscal_artifacts():
            return Response(
                {'detail': 'No tienes permiso para ver artefactos fiscales sensibles.', 'code': 'fiscal_artifact_forbidden'},
                status=status.HTTP_403_FORBIDDEN,
            )

        document = self.get_object()
        field_by_artifact = {
            'xml': 'xml_content',
            'signed-xml': 'signed_xml_content',
            'dgii-request': 'dgii_request_xml',
            'dgii-response': 'dgii_response_xml',
        }
        field = field_by_artifact[artifact]
        content = getattr(document, field, None)
        if not content:
            return Response({'detail': 'Artefacto no disponible.', 'code': 'artifact_not_available'}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(content, content_type='application/xml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{document.encf}-{artifact}.xml"'
        return response

    @action(detail=False, methods=['get'], url_path='async-monitor')
    def async_monitor(self, request):
        queryset = self.get_queryset()
        by_fiscal_status = (
            queryset
            .values('fiscal_status')
            .annotate(count=Count('id'))
            .order_by('fiscal_status')
        )
        by_job_status = (
            queryset
            .values('job_status')
            .annotate(count=Count('id'))
            .order_by('job_status')
        )
        retry_pending = queryset.filter(next_retry_at__isnull=False).count()
        technical_failed = queryset.filter(job_status='failed').count()
        pending_dgii = queryset.filter(fiscal_status='submitted').count()
        currently_running = queryset.filter(job_status='running').count()
        currently_queued = queryset.filter(job_status='queued').count()
        fiscal_rejected = queryset.filter(fiscal_status='rejected').count()
        accepted = queryset.filter(fiscal_status='accepted').count()
        rejected = fiscal_rejected
        submitted = pending_dgii
        queued = currently_queued
        running = currently_running
        retrying = queryset.filter(job_status='retrying').count()
        totals = queryset.aggregate(
            submission_attempts=Coalesce(Sum('submission_attempts'), 0),
            status_check_attempts=Coalesce(Sum('status_check_attempts'), 0),
        )
        recent_errors = list(
            queryset
            .exclude(last_error__isnull=True)
            .exclude(last_error='')
            .order_by('-updated_at')
            .values('id', 'encf', 'fiscal_status', 'job_status', 'last_error', 'next_retry_at', 'updated_at')[:10]
        )
        for item in recent_errors:
            item['status'] = item['fiscal_status']
        by_status = [{'status': item['fiscal_status'], 'count': item['count']} for item in by_fiscal_status]
        return Response(
            {
                'by_status': by_status,
                'by_fiscal_status': list(by_fiscal_status),
                'by_job_status': list(by_job_status),
                'accepted': accepted,
                'rejected': rejected,
                'submitted': submitted,
                'fiscal_rejected': fiscal_rejected,
                'technical_failed': technical_failed,
                'queued': queued,
                'running': running,
                'retrying': retrying,
                'pending_dgii': pending_dgii,
                'currently_running': currently_running,
                'currently_queued': currently_queued,
                'retry_pending': retry_pending,
                'submission_attempts': totals['submission_attempts'],
                'status_check_attempts': totals['status_check_attempts'],
                'recent_errors': recent_errors,
            }
        )
