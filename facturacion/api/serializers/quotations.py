from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.models import Client, Product, Quotation, QuotationDetail


class QuotationDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
    )
    product_name = serializers.CharField(source='product.name', read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and 'product' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['product'].queryset = Product.objects.filter(company=company)

    class Meta:
        model = QuotationDetail
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'product_name', 'subtotal']

    def validate(self, data):
        if not data.get('product'):
            product_id = data.get('product_id')
            if product_id:
                try:
                    queryset = Product.objects.all()
                    request = self.context.get('request')
                    company = get_current_company(request) if request else None
                    if company:
                        queryset = queryset.filter(company=company)
                    data['product'] = queryset.get(id=product_id)
                except Product.DoesNotExist:
                    raise serializers.ValidationError({"product_id": f"Producto ID {product_id} no existe"})
            else:
                raise serializers.ValidationError({"product": "Se requiere un producto"})
        return data

    def create(self, validated_data):
        validated_data.pop('product_id', None)
        return super().create(validated_data)


class QuotationSerializer(serializers.ModelSerializer):
    details = QuotationDetailSerializer(many=True)
    client_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    apply_itbis = serializers.BooleanField(write_only=True, required=False, default=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    customer_display = serializers.CharField(read_only=True)
    invoice_id = serializers.IntegerField(source='generated_invoice.id', read_only=True)
    invoice_number = serializers.CharField(source='generated_invoice.invoice_number', read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        self.fields['client'].required = False
        self.fields['client'].allow_null = True
        if request and 'client' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['client'].queryset = Client.objects.filter(company=company)

    class Meta:
        model = Quotation
        fields = [
            'id', 'company', 'quotation_number', 'client', 'client_id', 'client_name',
            'apply_itbis',
            'customer_name', 'customer_display', 'subtotal', 'tax', 'discount',
            'total', 'status', 'notes', 'valid_until', 'sent_at', 'approved_at',
            'rejected_at', 'expired_at', 'converted_at', 'created_by',
            'created_at', 'updated_at', 'invoice_id', 'invoice_number', 'details',
        ]
        read_only_fields = [
            'id', 'company', 'quotation_number', 'subtotal', 'tax', 'total', 'status',
            'sent_at', 'approved_at', 'rejected_at', 'expired_at', 'converted_at',
            'created_by', 'created_at', 'updated_at', 'invoice_id', 'invoice_number',
        ]

    def validate(self, data):
        details = data.get('details', [])
        if not details:
            raise serializers.ValidationError({'details': 'Debe incluir al menos un producto.'})
        client = data.get('client')
        client_id = data.get('client_id')
        customer_name = (data.get('customer_name') or '').strip()
        if not client and not client_id and not customer_name:
            raise serializers.ValidationError({'customer_name': 'Seleccione un cliente o escriba un nombre de cliente.'})
        return data
