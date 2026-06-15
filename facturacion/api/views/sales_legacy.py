import logging

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from facturacion.api.company_context import get_current_company
from facturacion.api.serializers.sales_legacy import SaleListSerializer, SaleSerializer
from facturacion.models import Sale
from facturacion.permissions import HasRequiredPermissions
from facturacion.services.invoicing import InvoiceCreationService


logger = logging.getLogger(__name__)


LEGACY_SALE_DEPRECATION_META = {
    'deprecated': True,
    'replacement': '/api/v1/invoices/',
    'removal_phase': '2A-final-cleanup',
}

LEGACY_SALE_DEPRECATION_HEADERS = {
    'Deprecation': 'true',
    'Sunset-Phase': '2A-legacy-sale-removal',
}


SALE_LEGACY_PERMISSIONS = {
    'GET': ['facturacion.view_sale'],
    'POST': ['facturacion.add_sale'],
    'PUT': ['facturacion.change_sale'],
    'PATCH': ['facturacion.change_sale'],
    'DELETE': ['facturacion.delete_sale'],
}


class HasSaleListReadPermission(HasRequiredPermissions):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return (
                request.user
                and request.user.is_authenticated
                and (
                    request.user.is_superuser
                    or request.user.has_perm('facturacion.view_sale')
                    or request.user.has_perm('facturacion.view_invoice')
                )
            )

        return super().has_permission(request, view)


def legacy_sale_response(data=None, *, http_status=None):
    if isinstance(data, dict):
        payload = {**data, **LEGACY_SALE_DEPRECATION_META}
    else:
        payload = {'results': data, **LEGACY_SALE_DEPRECATION_META}

    response = Response(payload, status=http_status)
    for header, value in LEGACY_SALE_DEPRECATION_HEADERS.items():
        response[header] = value
    return response


class SaleCreateView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'POST': ['facturacion.add_sale']}

    def post(self, request, *args, **kwargs):
        logger.warning(
            "Deprecated /sales/ flow used; delegating to InvoiceCreationService.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        serializer = SaleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = InvoiceCreationService().create_sale_with_invoice(
                    customer=serializer.validated_data.get('customer'),
                    details=serializer.validated_data.get('details', []),
                    client_id=serializer.validated_data.get('client_id') or request.data.get('client_id'),
                    user=request.user,
                    issuer_id=request.data.get('ecf_issuer') or request.data.get('issuer'),
                    ecf_type=request.data.get('ecf_type'),
                    company=get_current_company(request),
                )
                response_serializer = SaleListSerializer(result.sale, context={'request': request})
                return legacy_sale_response(
                    {
                        **response_serializer.data,
                        'invoice_id': result.invoice.id,
                        'invoice_number': result.invoice.invoice_number,
                        'ecf_type': getattr(result.electronic_document, 'ecf_type', None),
                        'ecf_status': getattr(result.electronic_document, 'status', None),
                        'encf': getattr(result.electronic_document, 'encf', None),
                        'track_id': getattr(result.electronic_document, 'track_id', None),
                        'ecf_enqueued': result.ecf_enqueued,
                        'ecf_error': result.ecf_error,
                    },
                    http_status=status.HTTP_201_CREATED,
                )
            except ValueError as exc:
                return legacy_sale_response({'detail': str(exc)}, http_status=status.HTTP_400_BAD_REQUEST)
        return legacy_sale_response(serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)


class SaleListView(generics.ListAPIView):
    queryset = Sale.objects.prefetch_related('details__product').all()
    serializer_class = SaleListSerializer
    permission_classes = [IsAuthenticated, HasSaleListReadPermission]
    required_permissions = {'GET': ['facturacion.view_sale']}

    def list(self, request, *args, **kwargs):
        logger.warning(
            "Deprecated /sales/list/ legacy report endpoint used.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        response = super().list(request, *args, **kwargs)
        return legacy_sale_response(response.data, http_status=response.status_code)


class SalesUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleListSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = SALE_LEGACY_PERMISSIONS

    def retrieve(self, request, *args, **kwargs):
        logger.warning(
            "Deprecated /salesUpdate/ retrieve endpoint used.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        response = super().retrieve(request, *args, **kwargs)
        return legacy_sale_response(response.data, http_status=response.status_code)

    def update(self, request, *args, **kwargs):
        logger.warning(
            "Blocked deprecated /salesUpdate/ update endpoint; Sale is read-only history.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        return legacy_sale_response(
            {
                'detail': 'Sale es un historico de solo lectura. Usa Invoice como fuente oficial.',
                'code': 'sale_legacy_read_only',
            },
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        logger.warning(
            "Blocked deprecated /salesUpdate/ partial update endpoint; Sale is read-only history.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        return legacy_sale_response(
            {
                'detail': 'Sale es un historico de solo lectura. Usa Invoice como fuente oficial.',
                'code': 'sale_legacy_read_only',
            },
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        logger.warning(
            "Blocked deprecated /salesUpdate/ delete endpoint; Sale is read-only history.",
            extra={"path": request.path, "user_id": getattr(request.user, "id", None)},
        )
        return legacy_sale_response(
            {
                'detail': 'Sale es un historico de solo lectura. No se puede borrar desde endpoints legacy.',
                'code': 'sale_legacy_read_only',
            },
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class SalesDetail(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'DELETE': ['facturacion.delete_sale']}

    def delete(self, request, pk):
        logger.warning(
            "Blocked deprecated SalesDetail delete endpoint; Sale is read-only history.",
            extra={"sale_id": pk, "user_id": getattr(request.user, "id", None)},
        )
        return legacy_sale_response(
            {
                'detail': 'Sale es un historico de solo lectura. No se puede borrar desde endpoints legacy.',
                'code': 'sale_legacy_read_only',
            },
            http_status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
