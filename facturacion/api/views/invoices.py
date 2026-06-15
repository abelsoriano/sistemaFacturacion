from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework import filters, status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.permissions import model_permissions
from facturacion.api.company_context import require_current_company
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.invoices import InvoiceSerializer
from facturacion.api.validators import normalize_rnc
from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.models import Client, Invoice
from facturacion.permissions import HasRequiredPermissions
from facturacion.services.invoicing import InvoiceCreationService


class InvoiceViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.prefetch_related('details__product').select_related('electronic_document').all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('invoice')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'client']
    search_fields = ['invoice_number', 'client__name', 'client__ruc_ci', 'electronic_document__encf']
    ordering_fields = ['created_at', 'updated_at', 'invoice_number', 'total', 'status']
    ordering = ['-created_at']
    fiscal_state_machine = ECFStateMachine()
    money_fields = {'subtotal', 'tax', 'discount', 'total', 'cash_received', 'change'}

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        client = params.get('client') or params.get('client_id')
        if client:
            queryset = queryset.filter(client_id=client)

        invoice_number = params.get('invoice_number')
        if invoice_number:
            queryset = queryset.filter(invoice_number__icontains=invoice_number)

        fiscal_status = params.get('fiscal_status') or params.get('ecf_fiscal_status')
        if fiscal_status:
            queryset = queryset.filter(electronic_document__fiscal_status=fiscal_status)

        created_at_from = params.get('created_at_from') or params.get('date_from')
        if created_at_from:
            queryset = queryset.filter(created_at__date__gte=created_at_from)

        created_at_to = params.get('created_at_to') or params.get('date_to')
        if created_at_to:
            queryset = queryset.filter(created_at__date__lte=created_at_to)

        return queryset

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            source = str(data.pop('source', '') or '').lower()
            customer_name = str(data.pop('customer_name', '') or data.get('customer', '') or '').strip()
            raw_customer_rnc = str(data.pop('customer_rnc', '') or '').strip()
            customer_rnc = normalize_rnc(raw_customer_rnc, label='RNC del cliente') if raw_customer_rnc else ''
            is_pos_source = source == 'pos'

            if is_pos_source:
                for client_key in ('client_id', 'client'):
                    if data.get(client_key) in (None, '', 'null', 'undefined'):
                        data.pop(client_key, None)

            # Normalizar payment_method
            payment_map = {
                'efectivo': 'cash',
                'tarjeta': 'card',
                'transferencia': 'transfer',
            }
            if is_pos_source and not data.get('payment_method'):
                data['payment_method'] = 'cash'
            if 'payment_method' in data:
                data['payment_method'] = payment_map.get(
                    data['payment_method'], data['payment_method']
                )

            # Asegurar que receipt_type sea válido
            if data.get('receipt_type') not in ('ticket', 'invoice'):
                data['receipt_type'] = 'invoice'

            if is_pos_source:
                data['status'] = 'paid'
            else:
                data['status'] = 'pending'

            if is_pos_source and customer_name and not data.get('notes'):
                data['notes'] = f"Venta POS: {customer_name}"

            self._normalize_money_payload(data)

            # Convertir product_id -> product en los detalles
            if 'details' in data:
                for detail in data['details']:
                    if 'product_id' in detail:
                        detail['product'] = detail.pop('product_id')

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            validated = serializer.validated_data
            details = validated.pop('details', [])
            client = validated.pop('client', None)
            client_id = data.get('client_id') or data.get('client') or getattr(client, 'id', None)
            ecf_type = data.get('ecf_type')
            company = require_current_company(request)

            with transaction.atomic():
                if is_pos_source and customer_rnc and not client_id:
                    if not customer_name:
                        return Response(
                            {'customer_name': 'Nombre requerido cuando customer_rnc viene sin cliente registrado.'},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    quick_client = Client.objects.filter(company=company, ruc_ci=customer_rnc).order_by('id').first()
                    if not quick_client:
                        quick_client = Client.objects.create(
                            company=company,
                            name=customer_name,
                            ruc_ci=customer_rnc,
                            client_type='occasional',
                        )
                    client_id = quick_client.id

                if is_pos_source and not ecf_type:
                    fiscal_client = Client.objects.filter(company=company, pk=client_id).only('ruc_ci').first() if client_id else None
                    ecf_type = '31' if customer_rnc or (fiscal_client and fiscal_client.ruc_ci) else '32'

                result = InvoiceCreationService().create_invoice(
                    client_id=client_id,
                    details=details,
                    payment_method=validated.get('payment_method', 'cash'),
                    receipt_type=validated.get('receipt_type', 'invoice'),
                    status='paid' if is_pos_source else 'pending',
                    subtotal=validated.get('subtotal'),
                    tax=validated.get('tax'),
                    discount=validated.get('discount'),
                    total=validated.get('total'),
                    cash_received=validated.get('cash_received'),
                    change=validated.get('change'),
                    notes=validated.get('notes'),
                    user=request.user,
                    auto_ecf=data.get('auto_ecf', True) if is_pos_source else False,
                    issuer_id=data.get('ecf_issuer') or data.get('issuer'),
                    ecf_type=ecf_type,
                    decrement_stock=is_pos_source,
                    company=company,
                    apply_itbis=validated.get('apply_itbis', True),
                )

            return Response(
                {
                    **self.get_serializer(result.invoice).data,
                    'ecf_type': getattr(result.electronic_document, 'ecf_type', None) or ecf_type,
                    'ecf_enqueued': result.ecf_enqueued,
                    'ecf_error': result.ecf_error,
                },
                status=status.HTTP_201_CREATED
            )

        except DRFValidationError:
            # Deja que DRF devuelva el 400 normalmente
            raise
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='collect')
    def collect(self, request, pk=None):
        invoice = self.get_object()
        try:
            result = InvoiceCreationService().collect_and_issue_invoice(
                invoice_id=invoice.id,
                user=request.user,
                issuer_id=request.data.get('ecf_issuer') or request.data.get('issuer'),
                ecf_type=request.data.get('ecf_type'),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                **self.get_serializer(result.invoice).data,
                'ecf_type': getattr(result.electronic_document, 'ecf_type', None),
                'ecf_enqueued': result.ecf_enqueued,
                'ecf_error': result.ecf_error,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        invoice = self.get_object()
        try:
            self.fiscal_state_machine.assert_mutable_invoice(invoice)
        except ECFError as exc:
            return Response({'detail': str(exc), 'code': 'fiscal_lock'}, status=status.HTTP_409_CONFLICT)
        request._full_data = self._normalized_request_data(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        invoice = self.get_object()
        try:
            self.fiscal_state_machine.assert_mutable_invoice(invoice)
        except ECFError as exc:
            return Response({'detail': str(exc), 'code': 'fiscal_lock'}, status=status.HTTP_409_CONFLICT)
        request._full_data = self._normalized_request_data(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        invoice = self.get_object()
        if getattr(invoice, 'electronic_document', None):
            return Response(
                {'detail': 'No se puede borrar una factura con documento e-CF. Usa nota de credito o anulacion fiscal.', 'code': 'fiscal_delete_blocked'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    def _normalized_request_data(self, request):
        data = request.data.copy()
        self._normalize_money_payload(data)
        return data

    def _normalize_money_payload(self, data):
        for field in self.money_fields:
            if field in data and data[field] not in (None, ''):
                data[field] = str(
                    Decimal(str(data[field])).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                )
        for detail in data.get('details') or []:
            if 'price' in detail and detail['price'] not in (None, ''):
                detail['price'] = str(
                    Decimal(str(detail['price'])).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                )
            if 'subtotal' in detail and detail['subtotal'] not in (None, ''):
                detail['subtotal'] = str(
                    Decimal(str(detail['subtotal'])).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                )
