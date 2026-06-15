from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import require_current_company
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.credit_notes import CreditNoteSerializer
from facturacion.ecf.exceptions import ECFCeleryUnavailable
from facturacion.ecf.queues import enqueue_check_status, enqueue_retry_submission
from facturacion.models import CreditNote, Invoice
from facturacion.permissions import HasRequiredPermissions
from facturacion.services.credit_note_reconciliation import CreditNoteReconciliationService
from facturacion.services.credit_notes import CreditNoteService


def _legacy_queue_callable(name, default):
    try:
        from facturacion import views as legacy_views
    except ImportError:
        return default
    return getattr(legacy_views, name, default)


class CreditNoteViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CreditNote.objects.select_related('origin_invoice__client', 'origin_invoice__electronic_document', 'created_by', 'electronic_document').prefetch_related('details__product').all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_creditnote'],
        'POST': ['facturacion.add_creditnote', 'facturacion.reverse_invoice'],
        'PUT': ['facturacion.change_creditnote'],
        'PATCH': ['facturacion.change_creditnote'],
        'DELETE': ['facturacion.delete_creditnote'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get('ecf_fiscal_status'):
            queryset = queryset.filter(electronic_document__fiscal_status=params['ecf_fiscal_status'])
        if params.get('ecf_job_status'):
            queryset = queryset.filter(electronic_document__job_status=params['ecf_job_status'])
        if params.get('fiscal_resolution_status'):
            queryset = queryset.filter(fiscal_resolution_status=params['fiscal_resolution_status'])
        if params.get('inventory_reconciliation_status'):
            queryset = queryset.filter(inventory_reconciliation_status=params['inventory_reconciliation_status'])
        if params.get('requires_manual_review') not in (None, ''):
            value = str(params.get('requires_manual_review')).lower() in {'true', '1', 'yes', 'si'}
            queryset = queryset.filter(requires_manual_review=value)
        if params.get('origin_invoice'):
            queryset = queryset.filter(origin_invoice_id=params['origin_invoice'])
        if params.get('client'):
            queryset = queryset.filter(origin_invoice__client_id=params['client'])
        if params.get('created_at_from'):
            queryset = queryset.filter(created_at__date__gte=params['created_at_from'])
        if params.get('created_at_to'):
            queryset = queryset.filter(created_at__date__lte=params['created_at_to'])
        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(credit_note_number__icontains=search)
                | Q(origin_invoice__invoice_number__icontains=search)
                | Q(origin_invoice__client__name__icontains=search)
                | Q(electronic_document__encf__icontains=search)
            )
        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        try:
            company = require_current_company(request)
            origin_invoice_id = request.data.get('origin_invoice') or request.data.get('origin_invoice_id')
            origin_invoice = Invoice.objects.get(pk=origin_invoice_id)
            if origin_invoice.company_id != company.id:
                return Response(
                    {'origin_invoice': 'La factura origen no pertenece a la empresa activa.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result = CreditNoteService().create_credit_note(
                origin_invoice_id=origin_invoice_id,
                details=request.data.get('details'),
                reason=request.data.get('reason'),
                user=request.user,
                issuer_id=request.data.get('issuer') or request.data.get('ecf_issuer'),
                restore_inventory=request.data.get('restore_inventory', True),
                company=company,
            )
            data = self.get_serializer(result.credit_note).data
            document = result.electronic_document
            data.update({
                'ecf_enqueued': result.ecf_enqueued,
                'ecf_error': result.ecf_error,
                'fiscal_status': getattr(document, 'fiscal_status', None),
                'job_status': getattr(document, 'job_status', None),
            })
            return Response(data, status=status.HTTP_201_CREATED)
        except Invoice.DoesNotExist:
            return Response({'origin_invoice': 'Factura origen no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reconcile-inventory')
    def reconcile_inventory(self, request, pk=None):
        try:
            result = CreditNoteReconciliationService().compensate_inventory(self.get_object(), user=request.user)
            data = self.get_serializer(result.credit_note).data
            data['message'] = result.message
            data['changed'] = result.changed
            return Response(data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='mark-reviewed')
    def mark_reviewed(self, request, pk=None):
        result = CreditNoteReconciliationService().mark_reviewed(self.get_object(), user=request.user)
        data = self.get_serializer(result.credit_note).data
        data['message'] = result.message
        data['changed'] = result.changed
        return Response(data)

    @action(detail=True, methods=['post'], url_path='check-status')
    def check_status(self, request, pk=None):
        note = self.get_object()
        document = getattr(note, 'electronic_document', None)
        if not document:
            return Response({'detail': 'La nota no tiene e-CF E34 relacionado.'}, status=status.HTTP_400_BAD_REQUEST)
        enqueue = _legacy_queue_callable('enqueue_check_status', enqueue_check_status)
        response = self._enqueue_or_503(
            lambda: enqueue(document.id, user_id=request.user.id, environment=request.data.get('environment'))
        )
        if isinstance(response, Response):
            return response
        data = self.get_serializer(note).data
        data['queue'] = response
        return Response(data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='retry')
    def retry(self, request, pk=None):
        note = self.get_object()
        document = getattr(note, 'electronic_document', None)
        if not document:
            return Response({'detail': 'La nota no tiene e-CF E34 relacionado.'}, status=status.HTTP_400_BAD_REQUEST)
        enqueue = _legacy_queue_callable('enqueue_retry_submission', enqueue_retry_submission)
        response = self._enqueue_or_503(
            lambda: enqueue(document.id, user_id=request.user.id, environment=request.data.get('environment'))
        )
        if isinstance(response, Response):
            return response
        data = self.get_serializer(note).data
        data['queue'] = response
        return Response(data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='fiscal-summary')
    def fiscal_summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        accepted = queryset.filter(electronic_document__fiscal_status='accepted')
        pending = queryset.filter(electronic_document__fiscal_status__in=['draft', 'xml_generated', 'signed', 'submitted'])
        rejected = queryset.filter(electronic_document__fiscal_status='rejected')
        return Response({
            'accepted': accepted.count(),
            'pending': pending.count(),
            'rejected': rejected.count(),
            'requires_manual_review': queryset.filter(requires_manual_review=True).count(),
            'inventory_restored_pending': queryset.filter(inventory_reconciliation_status='restored_pending').count(),
            'inventory_confirmed': queryset.filter(inventory_reconciliation_status='confirmed').count(),
            'inventory_compensation_required': queryset.filter(inventory_reconciliation_status='compensation_required').count(),
            'inventory_compensated': queryset.filter(inventory_reconciliation_status='compensated').count(),
            'total_confirmed': accepted.aggregate(total=Coalesce(Sum('total'), Decimal('0.00')))['total'],
            'total_pending': pending.aggregate(total=Coalesce(Sum('total'), Decimal('0.00')))['total'],
            'total_rejected': rejected.aggregate(total=Coalesce(Sum('total'), Decimal('0.00')))['total'],
        })

    def _enqueue_or_503(self, callback):
        try:
            return callback()
        except ECFCeleryUnavailable as exc:
            return Response({'detail': str(exc), 'code': 'ecf_queue_unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    def update(self, request, *args, **kwargs):
        return Response({'detail': 'Las notas de credito fiscales no se editan; emite otra nota si corresponde.'}, status=status.HTTP_409_CONFLICT)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'Las notas de credito fiscales no se borran; quedan como auditoria fiscal.'}, status=status.HTTP_409_CONFLICT)
