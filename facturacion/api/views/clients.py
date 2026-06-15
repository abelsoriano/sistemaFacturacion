from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.clients import ClientSerializer
from facturacion.models import Client
from facturacion.permissions import HasRequiredPermissions


class ClientViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_client'],
        'POST': ['facturacion.add_client'],
        'PUT': ['facturacion.change_client'],
        'PATCH': ['facturacion.change_client'],
        'DELETE': ['facturacion.delete_client'],
    }
