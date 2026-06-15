from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.assets import (
    AssetCategorySerializer,
    AssetListSerializer,
    AssetSerializer,
)
from facturacion.models import Asset, AssetCategory
from facturacion.permissions import HasRequiredPermissions


class AssetCategoryViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_assetcategory'],
        'POST': ['facturacion.add_assetcategory'],
        'PUT': ['facturacion.change_assetcategory'],
        'PATCH': ['facturacion.change_assetcategory'],
        'DELETE': ['facturacion.delete_assetcategory'],
    }
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AssetViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('category').all()
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_asset'],
        'POST': ['facturacion.add_asset'],
        'PUT': ['facturacion.change_asset'],
        'PATCH': ['facturacion.change_asset'],
        'DELETE': ['facturacion.delete_asset'],
    }
    action_required_permissions = {
        'assign': ['facturacion.change_asset'],
        'return_asset': ['facturacion.change_asset'],
    }
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'condition', 'category', 'assigned_to']
    search_fields = ['code', 'name', 'description', 'brand', 'model', 'serial_number', 'location']
    ordering_fields = ['code', 'name', 'created_at', 'purchase_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        return AssetSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        queryset = self.get_queryset()
        total = queryset.count()
        by_status = queryset.values('status').annotate(count=Count('id'))
        by_condition = queryset.values('condition').annotate(count=Count('id'))
        by_category = queryset.values('category__name').annotate(count=Count('id'))
        needs_maintenance = queryset.filter(
            next_maintenance__lte=timezone.now().date()
        ).count()

        return Response({
            'total': total,
            'by_status': list(by_status),
            'by_condition': list(by_condition),
            'by_category': list(by_category),
            'needs_maintenance': needs_maintenance,
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        available_assets = self.get_queryset().filter(status='available')
        serializer = self.get_serializer(available_assets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def maintenance_required(self, request):
        assets = self.get_queryset().filter(next_maintenance__lte=timezone.now().date())
        serializer = self.get_serializer(assets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        asset = self.get_object()
        assigned_to = request.data.get('assigned_to')

        if not assigned_to:
            return Response(
                {'error': 'Se requiere especificar a quién se asignará el activo'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset.assigned_to = assigned_to
        asset.status = 'in_use'
        asset.save()

        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=['post'])
    def return_asset(self, request, pk=None):
        asset = self.get_object()
        asset.assigned_to = None
        asset.status = 'available'
        asset.save()

        return Response(self.get_serializer(asset).data)
