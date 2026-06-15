from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.models import Category, Product, ProductHistory


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ['company']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    barcode = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and 'category' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['category'].queryset = Category.objects.filter(company=company)

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id', 'company']
        validators = []


class ProductHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductHistory
        fields = ['id', 'product', 'product_name', 'action', 'changed_fields', 'timestamp', 'note']
        read_only_fields = ['id', 'product_name', 'timestamp']


class LowStockProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category_name', 'stock', 'min_stock',
            'price', 'stock_status',
        ]

    def get_stock_status(self, obj):
        if obj.stock == 0:
            return 'agotado'
        elif obj.stock <= (obj.min_stock or 3):
            return 'critico'
        return 'normal'
