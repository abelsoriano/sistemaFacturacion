from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import require_current_company
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.quotations import QuotationSerializer
from facturacion.models import Quotation
from facturacion.permissions import HasRequiredPermissions
from facturacion.services.quotations import QuotationService


class QuotationViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Quotation.objects.select_related('client', 'created_by').prefetch_related('details__product').all()
    serializer_class = QuotationSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_quotation'],
        'POST': ['facturacion.add_quotation'],
        'PUT': ['facturacion.change_quotation'],
        'PATCH': ['facturacion.change_quotation'],
        'DELETE': ['facturacion.delete_quotation'],
    }
    action_required_permissions = {
        'send': ['facturacion.change_quotation'],
        'approve': ['facturacion.change_quotation'],
        'reject': ['facturacion.change_quotation'],
        'expire': ['facturacion.change_quotation'],
        'convert_to_invoice': ['facturacion.change_quotation', 'facturacion.add_invoice'],
    }
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client']
    search_fields = ['quotation_number', 'customer_name', 'client__name', 'client__ruc_ci']
    ordering_fields = ['created_at', 'updated_at', 'valid_until', 'total']
    ordering = ['-created_at']
    service = QuotationService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            company = require_current_company(request)
            result = self.service.create_quotation(
                client_id=serializer.validated_data.get('client_id') or getattr(serializer.validated_data.get('client'), 'id', None),
                customer_name=serializer.validated_data.get('customer_name'),
                details=serializer.validated_data.get('details', []),
                discount=serializer.validated_data.get('discount'),
                notes=serializer.validated_data.get('notes'),
                valid_until=serializer.validated_data.get('valid_until'),
                user=request.user,
                company=company,
                apply_itbis=serializer.validated_data.get('apply_itbis', True),
            )
            return Response(self.get_serializer(result.quotation).data, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_error'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        quotation = self.get_object()
        serializer = self.get_serializer(quotation, data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service.update_quotation(quotation, data=serializer.validated_data, user=request.user)
            return Response(self.get_serializer(updated).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_error'}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        quotation = self.get_object()
        serializer = self.get_serializer(quotation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service.update_quotation(quotation, data=serializer.validated_data, user=request.user)
            return Response(self.get_serializer(updated).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_error'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        try:
            quotation = self.service.mark_sent(self.get_object().id)
            return Response(self.get_serializer(quotation).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_transition_error'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        try:
            quotation = self.service.approve(self.get_object().id)
            return Response(self.get_serializer(quotation).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_transition_error'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        try:
            quotation = self.service.reject(self.get_object().id)
            return Response(self.get_serializer(quotation).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_transition_error'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='expire')
    def expire(self, request, pk=None):
        try:
            quotation = self.service.expire(self.get_object().id)
            return Response(self.get_serializer(quotation).data)
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_transition_error'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='convert-to-invoice')
    def convert_to_invoice(self, request, pk=None):
        try:
            result = self.service.convert_to_invoice(
                quotation_id=self.get_object().id,
                user=request.user,
                payment_method=request.data.get('payment_method', 'cash'),
                status=request.data.get('status', 'pending'),
                cash_received=request.data.get('cash_received'),
                change=request.data.get('change'),
                issuer_id=request.data.get('issuer') or request.data.get('ecf_issuer'),
                ecf_type=request.data.get('ecf_type'),
            )
            return Response(
                {
                    'quotation': self.get_serializer(result.quotation).data,
                    'invoice_id': result.invoice.id,
                    'invoice_number': result.invoice.invoice_number,
                    'ecf_status': getattr(result.electronic_document, 'status', None),
                    'encf': getattr(result.electronic_document, 'encf', None),
                    'ecf_enqueued': result.ecf_enqueued,
                    'ecf_error': result.ecf_error,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({'detail': str(exc), 'code': 'quotation_conversion_error'}, status=status.HTTP_400_BAD_REQUEST)
