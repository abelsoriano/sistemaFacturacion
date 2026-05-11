from rest_framework import serializers
from .models import *
from rest_framework import serializers
from .models import *
from django.db.models import  Sum

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# ============ PRODUCT SERIALIZER CORREGIDO ============
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    barcode = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # ✅ AHORA ESCRIBIBLE
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)
        return None
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['id']  # Solo ID es read_only

class ProductHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductHistory
        fields = ['id', 'product', 'product_name', 'action', 'changed_fields', 'timestamp', 'note']
        read_only_fields = ['id', 'product_name', 'timestamp']

class PrintLabelSerializer(serializers.Serializer):
    """Serializer para la solicitud de impresión de etiquetas"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    label_width = serializers.IntegerField(default=50)  # en mm
    label_height = serializers.IntegerField(default=25)  # en mm
        
# ============ SALE DETAIL SERIALIZER MEJORADO ============
class SaleDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True, required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,  # ← CAMBIAR a False
        write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = SaleDetail
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'subtotal', 'product_name']
    
    def validate(self, data):
        if 'product' in data and data['product']:
            return data
        
        if 'product_id' in data and data['product_id']:
            try:
                product = Product.objects.get(id=data['product_id'])
                data['product'] = product
                return data
            except Product.DoesNotExist:
                raise serializers.ValidationError({"product_id": f"Producto ID {data['product_id']} no existe"})
        
        raise serializers.ValidationError({"product": "Se requiere un producto"})
    
    def create(self, validated_data):
        validated_data.pop('product_id', None)
        return super().create(validated_data)

# ============ SALE SERIALIZER MEJORADO ============
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
        
        # Validar stock
        for detail in details:
            product_id = detail.get('product_id')
            quantity = detail.get('quantity', 0)
            
            try:
                product = Product.objects.get(id=product_id)
                if product.stock < quantity:
                    raise serializers.ValidationError(
                        f"Stock insuficiente para {product.name}. "
                        f"Disponible: {product.stock}"
                    )
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Producto ID {product_id} no existe")
        
        return data
    
    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        
        # Calcular total
        total = 0
        for detail in details_data:
            total += detail['quantity'] * detail['price']
        
        sale = Sale.objects.create(total=total, **validated_data)
        
        for detail_data in details_data:
            product = Product.objects.get(id=detail_data['product_id'])
            
            # Descontar stock
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

# ============ CLIENT SERIALIZER MEJORADO ============
# serializers.py
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

# ============ INVOICE DETAIL SERIALIZER CORREGIDO ============
class InvoiceDetailSerializer(serializers.ModelSerializer):
    # Aceptar tanto 'product' como 'product_id'
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
        # Convertir product_id a product si existe
        if 'product_id' in data and data['product_id']:
            try:
                product = Product.objects.get(id=data['product_id'])
                data['product'] = product
            except Product.DoesNotExist:
                raise serializers.ValidationError({"product_id": f"Producto ID {data['product_id']} no existe"})
        
        # Validar que haya un producto
        if 'product' not in data or not data['product']:
            raise serializers.ValidationError({"product": "Se requiere un producto"})
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('product_id', None)
        return super().create(validated_data)

# ============ INVOICE SERIALIZER CORREGIDO ============
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
    
    def validate_receipt_type(self, value):
        """Normalizar receipt_type"""
        receipt_map = {
            'cash': 'efectivo',
            'efectivo': 'efectivo',
            'card': 'tarjeta',
            'tarjeta': 'tarjeta',
            'transfer': 'transferencia',
            'transferencia': 'transferencia'
        }
        return receipt_map.get(value, value)
    
    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        client_id = validated_data.pop('client_id', None)
        
        # Obtener cliente
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                validated_data['client'] = client
            except Client.DoesNotExist:
                pass
        
        # Normalizar receipt_type
        if 'receipt_type' in validated_data:
            validated_data['receipt_type'] = self.validate_receipt_type(validated_data['receipt_type'])
        
        # Crear factura
        invoice = Invoice.objects.create(**validated_data)
        
        # Crear detalles y descontar stock
        for detail_data in details_data:
            product = detail_data.get('product')
            if not product and 'product_id' in detail_data:
                product = Product.objects.get(id=detail_data['product_id'])
            
            if product:
                # Descontar stock
                product.stock -= detail_data['quantity']
                product.save()
                
                InvoiceDetail.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=detail_data['quantity'],
                    price=detail_data['price'],
                    subtotal=detail_data['quantity'] * detail_data['price']
                )
        
        # Recalcular totales
        invoice.calculate_totals()
        
        return invoice

class AlmacenSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()  # Solo el nombre
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

class LabourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Labour
        fields = '__all__'
    

#Testing serializers for Asset Management Module

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
        """Validar que el código sea único"""
        instance = self.instance
        if Asset.objects.filter(code=value).exclude(pk=instance.pk if instance else None).exists():
            raise serializers.ValidationError("Ya existe un activo con este código.")
        return value.upper()

# ============ LOW STOCK SERIALIZER (NUEVO) ============
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
        elif obj.stock <= obj.min_stock:
            return 'critico'
        else:
            return 'normal'

# ============ DASHBOARD SERIALIZERS (NUEVOS) ============
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

class AssetListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Asset
        fields = [
            'id', 'code', 'name', 'category_name', 'model', 'brand',  'serial_number', 'status', 'status_display',
            'condition', 'location', 'assigned_to', 'created_at'
        ]