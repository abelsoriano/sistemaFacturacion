from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.models import Asset, AssetCategory


class AssetCategorySerializer(serializers.ModelSerializer):
    assets_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = ['id', 'company', 'name', 'description', 'assets_count', 'created_at', 'updated_at']
        read_only_fields = ['company', 'created_at', 'updated_at']

    def get_assets_count(self, obj):
        return obj.assets.count()


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    needs_maintenance = serializers.BooleanField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and 'category' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['category'].queryset = AssetCategory.objects.filter(company=company)

    class Meta:
        model = Asset
        fields = [
            'id', 'company', 'code', 'name', 'description', 'category', 'category_name',
            'brand', 'model', 'serial_number', 'status', 'status_display',
            'condition', 'condition_display', 'location', 'assigned_to',
            'purchase_price', 'purchase_date', 'warranty_expiry',
            'last_maintenance', 'next_maintenance', 'maintenance_notes',
            'notes', 'is_available', 'needs_maintenance', 'created_at', 'updated_at',
        ]
        read_only_fields = ['company', 'created_at', 'updated_at']

    def validate_code(self, value):
        instance = self.instance
        request = self.context.get('request')
        company = get_current_company(request) if request else None
        queryset = Asset.objects.filter(code=value)
        if company:
            queryset = queryset.filter(company=company)
        if queryset.exclude(pk=instance.pk if instance else None).exists():
            raise serializers.ValidationError("Ya existe un activo con este código.")
        return value.upper()


class AssetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'company', 'code', 'name', 'category_name', 'model', 'brand',
            'serial_number', 'status', 'status_display',
            'condition', 'location', 'assigned_to', 'created_at',
        ]
        read_only_fields = ['company']
