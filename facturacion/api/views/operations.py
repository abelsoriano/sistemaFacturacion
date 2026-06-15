from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import require_current_company
from facturacion.api.serializers.operations import (
    AbonoServicioSerializer,
    AlmacenSerializer,
    ServicioManoObraSerializer,
)
from facturacion.api.permissions import model_permissions
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.models import AbonoServicio, Almacen, ServicioManoObra
from facturacion.permissions import HasRequiredPermissions


class AlmacenViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('almacen')


class ServicioManoObraViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ServicioManoObra.objects.prefetch_related('abonos').all()
    serializer_class = ServicioManoObraSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('servicio_mano_obra')

    @action(detail=True, methods=['post'], url_path='pagar-completo')
    def pagar_completo(self, request, pk=None):
        """Registra un abono por el saldo pendiente completo"""
        servicio = self.get_object()

        if servicio.esta_pagado:
            return Response(
                {'detail': 'Este servicio ya está pagado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        abono = AbonoServicio.objects.create(
            company=servicio.company,
            servicio=servicio,
            monto=servicio.saldo_pendiente,
            notas='Pago completo del saldo pendiente',
            registrado_por=request.user,
        )

        return Response(
            AbonoServicioSerializer(abono, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='resumen')
    def resumen(self, request, pk=None):
        """Devuelve un resumen del estado de pago"""
        servicio = self.get_object()
        return Response({
            'nombre_persona': servicio.nombre_persona,
            'precio_total': servicio.precio_total,
            'total_abonado': servicio.total_abonado,
            'saldo_pendiente': servicio.saldo_pendiente,
            'estado_pago': servicio.estado_pago,
            'modalidad_pago': servicio.modalidad_pago,
            'cantidad_abonos': servicio.abonos.count(),
        })


class AbonoServicioViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AbonoServicio.objects.select_related('servicio', 'registrado_por').all()
    serializer_class = AbonoServicioSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('abono_servicio')

    def get_queryset(self):
        qs = super().get_queryset()
        servicio_id = self.request.query_params.get('servicio')
        if servicio_id:
            qs = qs.filter(servicio_id=servicio_id)
        return qs

    def perform_create(self, serializer):
        company = require_current_company(self.request)
        servicio = serializer.validated_data.get('servicio')
        if servicio and servicio.company_id != company.id:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("El servicio no pertenece a la empresa activa.")
        serializer.save(company=company)

class ServicioManoObraUpdateDeleteView(CompanyScopedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ServicioManoObra.objects.all()
    serializer_class = ServicioManoObraSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('servicio_mano_obra')
