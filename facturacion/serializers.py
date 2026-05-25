from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from django.db.models import Sum
from django.contrib.auth.models import User, Group, Permission
from .models import (
    Category, Product, ProductHistory, Sale, SaleDetail,
    Client, Invoice, InvoiceDetail, Almacen,
    AssetCategory, Asset, AbonoServicio, ServicioManoObra
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source='content_type.model', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'app_label', 'content_type']


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        required=False
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['permissions'] = PermissionSerializer(instance.permissions.all(), many=True).data
        return data


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Group.objects.all(),
        required=False,
    )
    permissions = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'permissions', 'password'
        ]
        read_only_fields = ['id', 'permissions']

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        groups = validated_data.pop('groups', [])
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password(User.objects.make_random_password())
        user.save()
        if groups:
            user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        groups = validated_data.pop('groups', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        if groups is not None:
            instance.groups.set(groups)
        instance.save()
        return instance


# ============ PRODUCT SERIALIZERS ============
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    barcode = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id']


class ProductHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductHistory
        fields = ['id', 'product', 'product_name', 'action', 'changed_fields', 'timestamp', 'note']
        read_only_fields = ['id', 'product_name', 'timestamp']


class PrintLabelSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    label_width = serializers.IntegerField(default=50)
    label_height = serializers.IntegerField(default=25)


# ============ SALE SERIALIZERS ============
class SaleDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SaleDetail
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'subtotal', 'product_name']

    def validate(self, data):
        # Si ya viene el objeto product, listo
        if data.get('product'):
            return data

        # Si viene product_id, resolvemos
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

    class Meta:
        model = Sale
        fields = ['id', 'customer', 'date', 'total', 'details']
        read_only_fields = ['id', 'date', 'total']

    def validate(self, data):
        details = data.get('details', [])
        if not details:
            raise serializers.ValidationError({"details": "Debe incluir al menos un producto"})

        for detail in details:
            # El producto ya fue resuelto por SaleDetailSerializer.validate()
            product = detail.get('product')
            quantity = detail.get('quantity', 0)

            if product and product.stock < quantity:
                raise serializers.ValidationError(
                    f"Stock insuficiente para {product.name}. Disponible: {product.stock}"
                )

        return data

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])

        total = sum(d['quantity'] * d['price'] for d in details_data)
        sale = Sale.objects.create(total=total, **validated_data)

        for detail_data in details_data:
            product = detail_data['product']
            product.stock -= detail_data['quantity']
            product.save()

            SaleDetail.objects.create(
                sale=sale,
                product=product,
                quantity=detail_data['quantity'],
                price=detail_data['price']
            )

        return sale


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
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.has_perm('facturacion.view_sale_totals'))
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.user_can_view_totals():
            return data

        data.pop('total', None)
        for detail in data.get('details', []):
            detail.pop('price', None)
            detail.pop('subtotal', None)
        return data


# ============ CLIENT SERIALIZER ============
class ClientSerializer(serializers.ModelSerializer):
    total_invoices = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'address', 'ruc_ci',
                  'client_type', 'total_invoices', 'total_spent']

    def get_total_invoices(self, obj):
        return obj.invoices.filter(status='paid').count()

    def get_total_spent(self, obj):
        return obj.invoices.filter(status='paid').aggregate(
            total=Sum('total')
        )['total'] or 0


# ============ INVOICE SERIALIZERS ============
class InvoiceDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False
    )
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = InvoiceDetail
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'product_name', 'subtotal']

    def validate(self, data):
        if not data.get('product'):
            product_id = data.get('product_id')
            if product_id:
                try:
                    data['product'] = Product.objects.get(id=product_id)
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
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'client', 'client_id', 'client_name',
            'subtotal', 'tax', 'discount', 'total',
            'cash_received', 'change', 'payment_method', 'receipt_type',
            'status', 'notes', 'created_at', 'details'
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at']

    def validate_change(self, value):
        """Redondea a 2 decimales para evitar errores de punto flotante"""
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def validate_receipt_type(self, value):
        """Solo acepta los valores válidos del modelo: ticket o invoice"""
        valid = {'ticket': 'ticket', 'invoice': 'invoice'}
        return valid.get(value, 'invoice')

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        client_id = validated_data.pop('client_id', None)

        if client_id:
            try:
                validated_data['client'] = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                pass

        # Validar stock disponible antes de crear la factura
        for detail_data in details_data:
            product = detail_data.get('product')
            if product:
                requested_qty = detail_data.get('quantity', 0)
                if product.stock < requested_qty:
                    raise serializers.ValidationError(
                        f"Stock insuficiente para '{product.name}'. "
                        f"Disponible: {product.stock}, Solicitado: {requested_qty}"
                    )

        invoice = Invoice.objects.create(**validated_data)

        for detail_data in details_data:
            product = detail_data.get('product')
            if product:
                product.stock -= detail_data['quantity']
                product.save()

                InvoiceDetail.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=detail_data['quantity'],
                    price=detail_data['price'],
                    subtotal=detail_data['quantity'] * detail_data['price']
                )

        # No llamar calculate_totals() — los totales ya vienen calculados del frontend
        return invoice


# ============ ALMACEN SERIALIZER ============
class AlmacenSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=False
    )

    class Meta:
        model = Almacen
        fields = ['id', 'name', 'description', 'location', 'stock', 'category', 'category_id']

    def get_category(self, obj):
        return obj.category.name if obj.category else None


# ============ LABOUR SERIALIZER ============
class AbonoServicioSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.CharField(
        source='registrado_por.username',
        read_only=True
    )

    class Meta:
        model = AbonoServicio
        fields = [
            'id', 'servicio', 'monto', 'fecha_abono',
            'notas', 'registrado_por', 'registrado_por_nombre'
        ]
        read_only_fields = ['registrado_por']

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto del abono debe ser mayor a cero.")
        return value

    def validate(self, data):
        servicio = data.get('servicio')
        monto = data.get('monto', Decimal('0.00'))

        if servicio and servicio.esta_pagado:
            raise serializers.ValidationError(
                "Este servicio ya está completamente pagado."
            )
        if servicio and monto > servicio.saldo_pendiente:
            raise serializers.ValidationError(
                f"El monto excede el saldo pendiente (${servicio.saldo_pendiente})."
            )
        return data

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


class ServicioManoObraSerializer(serializers.ModelSerializer):
    abonos = AbonoServicioSerializer(many=True, read_only=True)
    saldo_pendiente = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    esta_pagado = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServicioManoObra
        fields = [
            'id', 'nombre_persona', 'descripcion', 'precio_total',
            'factura_asociada', 'modalidad_pago', 'estado_pago',
            'total_abonado', 'saldo_pendiente', 'esta_pagado',
            'fecha_creacion', 'fecha_actualizacion', 'abonos'
        ]
        read_only_fields = ['estado_pago', 'total_abonado', 'fecha_creacion', 'fecha_actualizacion']


# ============ ASSET SERIALIZERS ============
class AssetCategorySerializer(serializers.ModelSerializer):
    assets_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'description', 'assets_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_assets_count(self, obj):
        return obj.assets.count()


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    needs_maintenance = serializers.BooleanField(read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'code', 'name', 'description', 'category', 'category_name',
            'brand', 'model', 'serial_number', 'status', 'status_display',
            'condition', 'condition_display', 'location', 'assigned_to',
            'purchase_price', 'purchase_date', 'warranty_expiry',
            'last_maintenance', 'next_maintenance', 'maintenance_notes',
            'notes', 'is_available', 'needs_maintenance', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_code(self, value):
        instance = self.instance
        if Asset.objects.filter(code=value).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise serializers.ValidationError("Ya existe un activo con este código.")
        return value.upper()


class AssetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'code', 'name', 'category_name', 'model', 'brand',
            'serial_number', 'status', 'status_display',
            'condition', 'location', 'assigned_to', 'created_at'
        ]


# ============ UTILIDAD / DASHBOARD SERIALIZERS ============
class LowStockProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'category_name', 'stock', 'min_stock',
                  'price', 'stock_status']

    def get_stock_status(self, obj):
        if obj.stock == 0:
            return 'agotado'
        elif obj.stock <= (obj.min_stock or 3):
            return 'critico'
        return 'normal'


class SalesSummarySerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    sales_count = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    average_ticket = serializers.DecimalField(max_digits=10, decimal_places=2)


class TopProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class RecentSaleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer = serializers.CharField()
    date = serializers.DateTimeField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    items_count = serializers.IntegerField()
