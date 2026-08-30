from io import BytesIO
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import get_current_company, get_current_membership
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_config import DGIICertificationItemSerializer, DGIICertificationPlanSerializer
from facturacion.models import CompanyMembership, DGIICertificationDocument, DGIICertificationEvent, DGIICertificationItem, DGIICertificationPlan, ECFIssuerConfig
from facturacion.services.dgii_certification import (
    CertificationDocumentImmutableError,
    CertificationDocumentImmutableForSigning,
    CertificationGenerationAttemptFailed,
    CertificationResignAuthorizationError,
    CertificationSigningAttemptFailed,
    DGIICertificationDocumentGenerator,
    DGIICertificationDataTestsRunner,
    DGIICertificationRFCERebuilder,
    DGIICertificationDocumentSigner,
    DGIICertificationDGIISubmitter,
    DGIICertificationExcelImporter,
    DGIICertificationXMLGenerator,
)
from facturacion.services.certification_locking import CertificationArtifactChanged, CertificationMutationBlocked


MANAGER_ROLES = {CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN}


class DGIICertificationPlanViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = (
        DGIICertificationPlan.objects
        .select_related('company', 'imported_by')
        .prefetch_related('items', 'events')
        .all()
    )
    serializer_class = DGIICertificationPlanSerializer
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='import-set',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_set(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para importar el set DGII.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede importar el set DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'file': ['Debe cargar el Excel entregado por DGII.']}, status=status.HTTP_400_BAD_REQUEST)
        if Path(uploaded_file.name).suffix.lower() not in {'.xlsx', '.xls'}:
            return Response({'file': ['El set DGII debe ser un archivo .xlsx o .xls.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = DGIICertificationExcelImporter().import_workbook(
                uploaded_file=uploaded_file,
                company=company,
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {
                    'detail': 'No se pudo importar el Excel DGII.',
                    'code': 'dgii_excel_import_error',
                    'error': str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/generate-xml')
    def generate_item_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        item = DGIICertificationXMLGenerator().generate_item(item=item, user=request.user)
        serializer = DGIICertificationItemSerializer(item, context={'request': request})
        response_status = status.HTTP_200_OK
        if item.status == DGIICertificationItem.STATUS_GENERATION_ERROR:
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/generate-xml')
    def generate_group_xml(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        summary = DGIICertificationXMLGenerator().generate_group(
            plan=plan,
            group_number=int(group_number),
            user=request.user,
        )
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'summary': summary, 'plan': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path=r'items/(?P<item_id>[^/.]+)/download-xml')
    def download_item_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not item.generated_xml_path:
            return Response({'detail': 'Este item todavia no tiene escenario generado.'}, status=status.HTTP_404_NOT_FOUND)
        if not default_storage.exists(item.generated_xml_path):
            return Response({'detail': 'El escenario generado no esta disponible en almacenamiento.'}, status=status.HTTP_404_NOT_FOUND)

        filename = item.generated_xml_path.rsplit('/', 1)[-1]
        return FileResponse(default_storage.open(item.generated_xml_path, 'rb'), as_attachment=True, filename=filename)

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/generate-document')
    def generate_item_document(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            document = DGIICertificationDocumentGenerator().generate_item(item=item, user=request.user)
        except CertificationGenerationAttemptFailed as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (CertificationDocumentImmutableError, CertificationMutationBlocked) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        item.refresh_from_db()
        serializer = DGIICertificationItemSerializer(item, context={'request': request})
        response_status = status.HTTP_200_OK
        if document.status == DGIICertificationDocument.STATUS_GENERATION_ERROR:
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/generate-documents')
    def generate_group_documents(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        group_number = int(group_number)
        summary = DGIICertificationDocumentGenerator().generate_group(
            plan=plan,
            group_number=group_number,
            user=request.user,
        )
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'summary': summary, 'plan': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path=r'items/(?P<item_id>[^/.]+)/download-document-xml')
    def download_item_document_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        document = getattr(item, 'certification_document', None)
        if not document or document.status != DGIICertificationDocument.STATUS_GENERATED or not document.xml_content:
            return Response({'detail': 'Este item todavia no tiene documento e-CF generado.'}, status=status.HTTP_404_NOT_FOUND)

        filename = f"{document.ecf_type}-{document.encf or document.id}-certificacion.xml"
        response = HttpResponse(document.xml_content, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/sign-document')
    def sign_item_document(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            document = DGIICertificationDocumentSigner().sign_item(item=item, user=request.user)
        except (CertificationDocumentImmutableForSigning, CertificationMutationBlocked, CertificationArtifactChanged) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        item.refresh_from_db()
        serializer = DGIICertificationItemSerializer(item, context={'request': request})
        response_status = status.HTTP_200_OK
        if document.status == DGIICertificationDocument.STATUS_SIGNING_ERROR:
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/resign-document')
    def resign_item_document(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response
        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            document = DGIICertificationDocumentSigner().resign_item(
                item=item, actor=request.user, reason=request.data.get('reason', ''),
            )
        except (CertificationDocumentImmutableForSigning, CertificationResignAuthorizationError, CertificationMutationBlocked, CertificationArtifactChanged) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except (CertificationSigningAttemptFailed, ValueError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        item.refresh_from_db()
        serializer = DGIICertificationItemSerializer(item, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/sign-documents')
    def sign_group_documents(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        summary = DGIICertificationDocumentSigner().sign_group(
            plan=plan,
            group_number=int(group_number),
            user=request.user,
        )
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'summary': summary, 'plan': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path=r'items/(?P<item_id>[^/.]+)/download-signed-xml')
    def download_item_signed_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        document = getattr(item, 'certification_document', None)
        if (
            not document
            or not document.signed_xml_path
        ):
            return Response({'detail': 'Este item todavia no tiene XML firmado.'}, status=status.HTTP_404_NOT_FOUND)
        if not default_storage.exists(document.signed_xml_path):
            return Response({'detail': 'El XML firmado no esta disponible en almacenamiento.'}, status=status.HTTP_404_NOT_FOUND)

        filename = self._portal_upload_filename(document) if int(item.dgii_group) == 4 else document.signed_xml_path.rsplit('/', 1)[-1]
        return FileResponse(default_storage.open(document.signed_xml_path, 'rb'), as_attachment=True, filename=filename)

    @action(detail=True, methods=['get'], url_path=r'groups/(?P<group_number>[1-4])/download-signed-zip')
    def download_group_signed_zip(self, request, pk=None, group_number=None):
        plan = self.get_object()
        group_number = int(group_number)
        if group_number == 4:
            validation_error = self._low_consumption_zip_validation_error(plan)
            if validation_error:
                return Response({'detail': validation_error}, status=status.HTTP_400_BAD_REQUEST)
        documents = (
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(
                plan=plan,
                company=plan.company,
                item__dgii_group=group_number,
            )
            .exclude(signed_xml_path='')
            .order_by('item__source_row', 'id')
        )

        zip_buffer = BytesIO()
        written = 0
        filenames = set()
        with ZipFile(zip_buffer, 'w', ZIP_DEFLATED) as archive:
            for document in documents:
                if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
                    continue
                filename = self._signed_zip_filename(document, filenames)
                with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
                    archive.writestr(filename, signed_file.read())
                written += 1

        if written == 0:
            return Response(
                {'detail': 'Este grupo no tiene XML firmados disponibles para descargar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zip_buffer.seek(0)
        filename = f"plan-{plan.id}-grupo-{group_number}-xml-firmados.zip"
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/submit-dgii')
    def submit_group_dgii(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        group_number = int(group_number)

        try:
            summary = DGIICertificationDGIISubmitter().submit_group(
                plan=plan,
                group_number=group_number,
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') and not summary.get('rejected') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/submit-dgii')
    def submit_item_dgii(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            summary = DGIICertificationDGIISubmitter().submit_item(
                plan=plan,
                item=item,
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') and not summary.get('rejected') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/portal-status')
    def update_item_portal_status(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if int(item.dgii_group) != 4:
            return Response(
                {'detail': 'Solo las facturas de consumo <250K pueden registrar estado manual de portal.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        document = getattr(item, 'certification_document', None)
        if not document:
            return Response({'detail': 'Este item no tiene documento generado.'}, status=status.HTTP_400_BAD_REQUEST)

        portal_status = request.data.get('status')
        allowed_statuses = {
            DGIICertificationDocument.STATUS_READY_FOR_PORTAL_UPLOAD,
            DGIICertificationDocument.STATUS_UPLOADED_TO_PORTAL,
            DGIICertificationDocument.STATUS_ACCEPTED_BY_PORTAL,
        }
        if portal_status not in allowed_statuses:
            return Response({'detail': 'Estado de portal no valido.'}, status=status.HTTP_400_BAD_REQUEST)

        document.status = portal_status
        document.dgii_status = document.get_status_display()
        document.dgii_response_message = request.data.get('message') or document.get_status_display()
        document.save(update_fields=['status', 'dgii_status', 'dgii_response_message', 'updated_at'])
        DGIICertificationEvent.objects.create(
            company=document.company,
            plan=document.plan,
            item=document.item,
            event_type=DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED,
            message=f'Estado manual de portal actualizado: {document.get_status_display()}.',
            payload={
                'certification_document_id': document.id,
                'ecf_type': document.ecf_type,
                'dgii_group': document.item.dgii_group,
                'encf': document.encf,
                'portal_status': portal_status,
                'message': document.dgii_response_message,
            },
            created_by=request.user,
        )

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'plan': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/check-dgii-results')
    def check_group_dgii_results(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        group_number = int(group_number)

        try:
            summary = DGIICertificationDGIISubmitter().check_group_results(
                plan=plan,
                group_number=group_number,
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path='data-ecf/submit-dgii')
    def submit_data_ecf_dgii(self, request, pk=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        try:
            summary = DGIICertificationDGIISubmitter().submit_data_ecf(
                plan=plan,
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') and not summary.get('rejected') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path='data-ecf/check-dgii-results')
    def check_data_ecf_dgii_results(self, request, pk=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        try:
            summary = DGIICertificationDGIISubmitter().check_data_ecf_results(
                plan=plan,
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path='sync-reset-state')
    def sync_reset_state(self, request, pk=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        summary = DGIICertificationDGIISubmitter().sync_reset_state_from_stored_responses(
            plan=plan,
            user=request.user,
        )
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'summary': summary, 'plan': serializer.data})

    @action(detail=True, methods=['post'], url_path='low-consumption/rebuild-rfce')
    def rebuild_low_consumption_rfce(self, request, pk=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        try:
            summary = DGIICertificationRFCERebuilder().rebuild(plan=plan, user=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    @action(detail=True, methods=['post'], url_path='data-tests/run')
    def run_data_tests(self, request, pk=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        try:
            summary = DGIICertificationDataTestsRunner().run(plan=plan, user=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_200_OK if not summary.get('failed') else status.HTTP_400_BAD_REQUEST
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    def _manager_permission_response(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para generar XML DGII.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.is_superuser:
            return None
        if membership and membership.role in MANAGER_ROLES and membership.is_active:
            return None
        return Response(
            {'detail': 'Solo un owner o admin puede generar XML del plan DGII.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def _get_plan_item(self, plan, item_id):
        try:
            return plan.items.get(id=item_id, company=plan.company)
        except DGIICertificationItem.DoesNotExist:
            return None

    def _signed_zip_filename(self, document, filenames):
        base_name = self._portal_upload_filename(document) if int(document.item.dgii_group) == 4 else f"{document.encf or document.item.encf or document.id}.xml"
        filename = base_name
        if filename in filenames:
            stem = base_name.rsplit('.', 1)[0]
            filename = f"{stem}-item-{document.item_id}.xml"
        filenames.add(filename)
        return filename

    def _portal_upload_filename(self, document):
        raw_data = document.item.raw_data or {}
        issuer_rnc = ''.join(ch for ch in str(raw_data.get('RNCEmisor') or '') if ch.isdigit())
        if not issuer_rnc:
            issuer = ECFIssuerConfig.objects.filter(company=document.company, is_active=True).order_by('id').first()
            issuer_rnc = ''.join(ch for ch in str(getattr(issuer, 'rnc', '') or '') if ch.isdigit())
        return f"{issuer_rnc}{document.encf or document.item.encf or document.id}.xml"

    def _low_consumption_zip_validation_error(self, plan):
        data_accepted = DGIICertificationDocument.objects.filter(
            plan=plan,
            company=plan.company,
            item__dgii_group__in=[1, 2],
            status=DGIICertificationDocument.STATUS_ACCEPTED,
            accepted_stale=False,
        ).count()
        if data_accepted != 21:
            return f'Datos e-CF debe estar 21/21 aceptado antes de descargar estas facturas. Actual: {data_accepted}/21.'

        rfce_documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(
                plan=plan,
                company=plan.company,
                item__dgii_group=3,
                status=DGIICertificationDocument.STATUS_ACCEPTED,
                accepted_stale=False,
            )
        )
        if len(rfce_documents) != 4:
            return f'RFCE debe estar 4/4 aceptado antes de descargar estas facturas. Actual: {len(rfce_documents)}/4.'
        rfce_by_encf = {document.encf: document for document in rfce_documents}

        integral_documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company, item__dgii_group=4)
            .order_by('item__source_row', 'id')
        )
        if len(integral_documents) != 4:
            return f'Deben existir 4 facturas integras del grupo 4. Actual: {len(integral_documents)}/4.'

        for document in integral_documents:
            try:
                signature_prefix = self._signed_xml_signature_prefix(document)
            except ValueError as exc:
                return str(exc)
            rfce_document = rfce_by_encf.get(document.encf)
            if rfce_document is None:
                return f'{document.encf}: no existe RFCE aceptado asociado.'
            try:
                rfce_code = self._rfce_security_code_from_xml(rfce_document)
            except ValueError as exc:
                return str(exc)
            if rfce_code != signature_prefix:
                return f'{document.encf}: CodigoSeguridadeCF RFCE no coincide con SignatureValue[:6].'
        return ''

    def _signed_xml_signature_prefix(self, document):
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            raise ValueError(f'{document.encf}: XML integro firmado no disponible.')
        with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
            signed_xml = signed_file.read()
        actual_hash = hashlib.sha256(signed_xml).hexdigest()
        if document.signed_xml_hash and actual_hash != document.signed_xml_hash:
            raise ValueError(f'{document.encf}: hash del XML firmado no coincide con el registrado.')
        root = ET.fromstring(signed_xml)
        signature_node = root.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        if signature_node is None:
            raise ValueError(f'{document.encf}: XML integro firmado no contiene SignatureValue.')
        signature_value = re.sub(r'\s+', '', ''.join(signature_node.itertext()).strip())
        if len(signature_value) < 6:
            raise ValueError(f'{document.encf}: SignatureValue del XML integro es demasiado corto.')
        return signature_value[:6]

    def _rfce_security_code_from_xml(self, document):
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            raise ValueError(f'{document.encf}: XML RFCE firmado no disponible.')
        with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
            root = ET.fromstring(signed_file.read())
        code_node = root.find('.//CodigoSeguridadeCF')
        if code_node is None:
            raise ValueError(f'{document.encf}: RFCE no contiene CodigoSeguridadeCF.')
        return ''.join(code_node.itertext()).strip()
