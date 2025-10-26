from rest_framework import serializers
from .models import *
from rest_framework import serializers
from .models import *

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    barcode = serializers.CharField(read_only=True)  # Solo lectura, se genera automáticamente
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)
        return None
    
    class Meta:
        model = Product
        fields = '__all__'

class PrintLabelSerializer(serializers.Serializer):
    """Serializer para la solicitud de impresión de etiquetas"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    label_width = serializers.IntegerField(default=50)  # en mm
    label_height = serializers.IntegerField(default=25)  # en mm
        
class SaleDetailSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all()) 
    class Meta:
        model = SaleDetail
        fields = ['product', 'quantity', 'price']

class SaleSerializer(serializers.ModelSerializer):
    details = SaleDetailSerializer(many=True)
    # Campos opcionales que vienen del frontend pero no se guardan directamente
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        write_only=True
    )
    tax = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        write_only=True
    )
    # El campo total se puede sobrescribir opcionalmente
    total = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False
    )

    class Meta:
        model = Sale
        fields = ['customer', 'details', 'subtotal', 'tax', 'total']

    def to_internal_value(self, data):
        """
        Modifica los datos entrantes para que `products` sea tratado como `details`.
        También acepta `items` como alternativa.
        """
        # Convertir 'products' o 'items' a 'details' si existe
        if 'products' in data:
            data['details'] = [
                {
                    "product": product['product_id'] if 'product_id' in product else product['product'],
                    "quantity": product['quantity'],
                    "price": product.get('price', product['subtotal'] / product['quantity'])
                }
                for product in data['products']
            ]
            data.pop('products')
        elif 'items' in data:
            # Si viene 'items' (como en tu ejemplo)
            data['details'] = [
                {
                    "product": item['product'],
                    "quantity": item['quantity'],
                    "price": item['price']
                }
                for item in data['items']
            ]
            data.pop('items')

        return super().to_internal_value(data)

    def create(self, validated_data):
        # Extraer detalles y campos opcionales
        details_data = validated_data.pop('details')
        validated_data.pop('subtotal', None)  # Remover si existe
        validated_data.pop('tax', None)  # Remover si existe
        
        # Crear la venta
        sale = Sale.objects.create(**validated_data)

        # Crear los detalles
        for detail_data in details_data:
            product = detail_data['product']
            quantity = detail_data['quantity']

            # Validar stock del producto
            if product.stock < quantity:
                sale.delete()  # Eliminar la venta si falla
                raise serializers.ValidationError(
                    f"No hay suficiente stock para {product.name}. Disponible: {product.stock}"
                )

            # Reducir el stock del producto
            product.stock -= quantity
            product.save()

            # Crear el detalle
            SaleDetail.objects.create(sale=sale, **detail_data)

        # Calcular el total
        sale.calculate_total()

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

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'address']

class InvoiceDetailSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)
    # product_name = serializers.CharField(source='product.name', read_only=True)
    # product_description = serializers.CharField(source='product.description', read_only=True)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), 
        required=False, 
        write_only=True
    )

    class Meta:
        model = InvoiceDetail
        fields = ['product_id', 'product', 'quantity', 'price', 'subtotal']

    def create(self, validated_data):
        # If product_id is provided, use it to set the product
        if 'product_id' in validated_data:
            validated_data['product'] = Product.objects.get(id=validated_data.pop('product_id'))
        return super().create(validated_data)

class InvoiceSerializer(serializers.ModelSerializer):
    details = InvoiceDetailSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [ 'details', 'id','total', 'receipt_type', 'cash_received', 'change']

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        
        # Create invoice first
        invoice = Invoice.objects.create(**validated_data)
        
        # Create invoice details
        for detail_data in details_data:
            detail_data['invoice'] = invoice
            InvoiceDetail.objects.create(**detail_data)
        
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
    