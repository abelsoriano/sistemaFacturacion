import logging

from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.api.permissions import can_view_financial_totals
from facturacion.models import Product, Sale, SaleDetail


logger = logging.getLogger(__name__)


class SaleDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        write_only=True,
    )
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleDetail
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'subtotal', 'product_name']

    def validate(self, data):
        if data.get('product'):
            return data

        product_id = data.get('product_id')
        if product_id:
            try:
                data['product'] = Product.objects.get(id=product_id)
                return data
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    {"product_id": f"Producto ID {product_id} no existe"}
                )

        raise serializers.ValidationError({"product": "Se requiere un producto"})

    def create(self, validated_data):
        validated_data.pop('product_id', None)
        return super().create(validated_data)


class SaleSerializer(serializers.ModelSerializer):
    details = SaleDetailSerializer(many=True)
    client_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'client_id', 'date', 'total', 'details']
        read_only_fields = ['id', 'date', 'total']

    def validate(self, data):
        details = data.get('details', [])
        if not details:
            raise serializers.ValidationError({"details": "Debe incluir al menos un producto"})

        for detail in details:
            product = detail.get('product')
            quantity = detail.get('quantity', 0)

            if product and product.stock < quantity:
                raise serializers.ValidationError(
                    f"Stock insuficiente para {product.name}. Disponible: {product.stock}"
                )

        return data

    def create(self, validated_data):
        from facturacion.services.invoicing import InvoiceCreationService

        details_data = validated_data.pop('details', [])
        logger.warning(
            "Deprecated SaleSerializer.create used; delegating to InvoiceCreationService.",
            extra={"customer": validated_data.get("customer")},
        )
        result = InvoiceCreationService().create_sale_with_invoice(
            customer=validated_data.get('customer'),
            details=details_data,
            client_id=validated_data.get('client_id'),
            user=self.context.get('request').user if self.context.get('request') else None,
            company=get_current_company(self.context.get('request')) if self.context.get('request') else None,
        )
        return result.sale


class SaleDetailListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleDetail
        fields = ['product_name', 'quantity', 'price', 'subtotal']


class SaleListSerializer(serializers.ModelSerializer):
    details = SaleDetailListSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'date', 'total', 'details']

    def user_can_view_totals(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return can_view_financial_totals(user)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.user_can_view_totals():
            return data

        data.pop('total', None)
        for detail in data.get('details', []):
            detail.pop('price', None)
            detail.pop('subtotal', None)
        return data
