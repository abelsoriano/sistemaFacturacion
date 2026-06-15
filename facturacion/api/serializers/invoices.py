from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.api.serializers.ecf_runtime import _effective_fiscal_status, _effective_job_status
from facturacion.models import Client, Invoice, InvoiceDetail, Product
from facturacion.services.fiscal_rules import FiscalCalculationService


class InvoiceDetailSerializer(serializers.ModelSerializer):
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
        model = InvoiceDetail
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
                    raise serializers.ValidationError(
                        {"product_id": f"Producto ID {product_id} no existe"}
                    )
            else:
                raise serializers.ValidationError({"product": "Se requiere un producto"})
        return data

    def create(self, validated_data):
        validated_data.pop('product_id', None)
        return super().create(validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    details = InvoiceDetailSerializer(many=True)
    client_id = serializers.IntegerField(write_only=True, required=False)
    apply_itbis = serializers.BooleanField(write_only=True, required=False, default=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    origin_quotation_number = serializers.CharField(source='origin_quotation.quotation_number', read_only=True)
    ecf_status = serializers.SerializerMethodField()
    ecf_job_status = serializers.SerializerMethodField()
    encf = serializers.CharField(source='electronic_document.encf', read_only=True)
    track_id = serializers.CharField(source='electronic_document.track_id', read_only=True)
    ecf_last_error = serializers.CharField(source='electronic_document.last_error', read_only=True)
    is_fiscally_locked = serializers.BooleanField(read_only=True)
    fiscal_lock_reason = serializers.CharField(read_only=True)
    can_collect = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and 'client' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['client'].queryset = Client.objects.filter(company=company)

    class Meta:
        model = Invoice
        fields = [
            'id', 'company', 'invoice_number', 'client', 'client_id', 'client_name',
            'apply_itbis',
            'subtotal', 'tax', 'discount', 'total',
            'cash_received', 'change', 'payment_method', 'receipt_type',
            'status', 'inventory_committed_at', 'notes', 'created_at', 'origin_quotation', 'origin_quotation_number', 'details',
            'ecf_status', 'encf', 'track_id', 'ecf_last_error',
            'ecf_job_status', 'is_fiscally_locked', 'fiscal_lock_reason', 'can_collect'
        ]
        read_only_fields = [
            'id', 'company', 'invoice_number', 'inventory_committed_at', 'created_at', 'origin_quotation', 'origin_quotation_number',
            'ecf_status', 'encf', 'track_id', 'ecf_last_error', 'ecf_job_status',
            'is_fiscally_locked', 'fiscal_lock_reason', 'can_collect'
        ]

    def get_ecf_status(self, obj):
        return _effective_fiscal_status(getattr(obj, 'electronic_document', None))

    def get_ecf_job_status(self, obj):
        return _effective_job_status(getattr(obj, 'electronic_document', None))

    def get_can_collect(self, obj):
        document = getattr(obj, 'electronic_document', None)
        return (
            obj.status == 'pending'
            and obj.inventory_committed_at is None
            and document is None
        )

    def validate_change(self, value):
        """Redondea a 2 decimales para evitar errores de punto flotante"""
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def validate_receipt_type(self, value):
        """Solo acepta los valores válidos del modelo: ticket o invoice"""
        valid = {'ticket': 'ticket', 'invoice': 'invoice'}
        return valid.get(value, 'invoice')

    def create(self, validated_data):
        from facturacion.services.invoicing import InvoiceCreationService

        details_data = validated_data.pop('details', [])
        client = validated_data.pop('client', None)
        client_id = validated_data.pop('client_id', None) or getattr(client, 'id', None)
        apply_itbis = validated_data.pop('apply_itbis', True)
        result = InvoiceCreationService().create_invoice(
            client_id=client_id,
            details=details_data,
            payment_method=validated_data.get('payment_method', 'cash'),
            receipt_type=validated_data.get('receipt_type', 'invoice'),
            status='pending',
            subtotal=validated_data.get('subtotal'),
            tax=validated_data.get('tax'),
            discount=validated_data.get('discount'),
            total=validated_data.get('total'),
            cash_received=validated_data.get('cash_received'),
            change=validated_data.get('change'),
            notes=validated_data.get('notes'),
            user=self.context.get('request').user if self.context.get('request') else None,
            auto_ecf=False,
            decrement_stock=False,
            company=get_current_company(self.context.get('request')) if self.context.get('request') else None,
            apply_itbis=apply_itbis,
        )
        return result.invoice

    def update(self, instance, validated_data):
        details_data = validated_data.pop('details', None)
        client = validated_data.pop('client', None)
        client_id = validated_data.pop('client_id', None) or getattr(client, 'id', None)
        has_discount = 'discount' in validated_data
        has_apply_itbis = 'apply_itbis' in validated_data
        apply_itbis = validated_data.pop('apply_itbis', instance.tax > 0)

        if client_id:
            instance.client = Client.objects.filter(
                pk=client_id,
                company=instance.company,
            ).first()

        for field in ('payment_method', 'receipt_type', 'status', 'cash_received', 'change', 'notes'):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if details_data is not None:
            normalized_details = []
            for detail in details_data:
                product = detail.get('product')
                quantity = int(detail.get('quantity') or 0)
                price = Decimal(str(detail.get('price') or getattr(product, 'price', 0))).quantize(Decimal('0.01'))
                normalized_details.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'subtotal': price * quantity,
                })
            instance.subtotal = sum(item['subtotal'] for item in normalized_details)
            instance.details.all().delete()
            InvoiceDetail.objects.bulk_create([
                InvoiceDetail(
                    invoice=instance,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['price'],
                    subtotal=item['subtotal'],
                )
                for item in normalized_details
            ])

        if details_data is not None or has_discount or has_apply_itbis:
            discount = validated_data.get('discount', instance.discount)
            totals = FiscalCalculationService().calculate_invoice_totals(
                instance.subtotal,
                discount,
                apply_itbis=apply_itbis,
            )
            instance.subtotal = totals.subtotal
            instance.tax = totals.tax
            instance.discount = totals.discount
            instance.total = totals.total

        instance.save()
        return instance
