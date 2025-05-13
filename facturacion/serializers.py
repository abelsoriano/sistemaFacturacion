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
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_stock_status(self, obj):
        return "Disponible" if obj.stock > 0 else "Agotado"
    

class SaleDetailSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all()) 
    class Meta:
        model = SaleDetail
        fields = ['product', 'quantity', 'price']

class SaleSerializer(serializers.ModelSerializer):
    details = SaleDetailSerializer(many=True)

    class Meta:
        model = Sale
        fields = ['customer', 'details']

    def to_internal_value(self, data):
        """
        Modifica los datos entrantes para que `products` sea tratado como `details`.
        """
        # Convertir 'products' a 'details' si existe
        if 'products' in data:
            data['details'] = [
                {
                    "product": product['product_id'],
                    "quantity": product['quantity'],
                    "price": product['subtotal'] / product['quantity']
                }
                for product in data['products']
            ]
            data.pop('products')  # Eliminar el campo 'products' para evitar conflictos

        return super().to_internal_value(data)

    def create(self, validated_data):
        # Extraer detalles de la venta
        details_data = validated_data.pop('details')
        # Crear la venta
        sale = Sale.objects.create(**validated_data)

        # Crear los detalles
        for detail_data in details_data:
            product = detail_data['product']
            quantity = detail_data['quantity']

            # Validar stock del producto
            if product.stock < quantity:
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
    
