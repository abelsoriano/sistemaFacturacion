from django.db import models
import uuid 
from django.core.validators import MinValueValidator
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    min_stock = models.IntegerField(
        default=3, 
        blank=True, 
        null=True,
        verbose_name="Stock Mínimo"
    )
    barcode = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True,
        verbose_name="Código de Barras"
    )

    def save(self, *args, **kwargs):
        # Generar código de barras automáticamente si no existe
        if not self.barcode:
            self.barcode = self.generate_barcode()
        super().save(*args, **kwargs)

    def generate_barcode(self):
        """Genera un código de barras secuencial único basado en el ID más alto"""
        # Obtener el número más alto de todos los códigos existentes
        productos_con_codigo = Product.objects.exclude(
            barcode__isnull=True
        ).exclude(
            barcode=''
        ).values_list('barcode', flat=True)
        
        max_number = 0
        
        for barcode in productos_con_codigo:
            try:
                # Extrae todos los dígitos del código
                digits = ''.join(filter(str.isdigit, barcode))
                if digits:
                    number = int(digits)
                    if number > max_number:
                        max_number = number
            except ValueError:
                continue
        
        # El siguiente número
        new_number = max_number + 1
        
        return f"BB{new_number:05d}"  # PRD00001, PRD00002...
        

class Sale(models.Model):
    customer = models.CharField(max_length=100, blank=True, null=True)  
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def calculate_total(self):
        """
        Calcula el total sumando los subtotales de los detalles de la venta.
        """
        self.total = sum(detail.subtotal for detail in self.details.all())
        self.save()

    def __str__(self):
        return f"Venta #{self.id} - {self.date.strftime('%Y-%m-%d %H:%M:%S')}"

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        """
        Calcula el subtotal de este detalle de venta.
        """
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"

class Client(models.Model):   
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Invoice(models.Model):
    total = models.DecimalField(max_digits=10, decimal_places=2)
    cash_received = models.DecimalField(max_digits=10, decimal_places=2)
    change = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_type = models.CharField(max_length=20, choices=[('ticket', 'Ticket'), ('invoice', 'Invoice')])
    created_at = models.DateTimeField(auto_now_add=True)



    def __str__(self):
        return f"Factura #{self.id} - {self.client.name}"

class InvoiceDetail(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="details")
    product = models.ForeignKey('Product', on_delete=models.PROTECT)  # Uso de comillas
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (Factura #{self.invoice.id})"

class Almacen(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=20, blank=True, null=True)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='almacenes')

    def __str__(self):
        return self.name
    
class Labour(models.Model):
    name = models.CharField(max_length=70)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    factura_asociada = models.CharField(max_length = 10, blank=True, null=True)
    # factura = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='servicios', null=True, blank=True)
    

# Testing models for Asset Management Module
class AssetCategory(models.Model):
    """Categorías de activos"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Categoría de Activo"
        verbose_name_plural = "Categorías de Activos"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Asset(models.Model):
    """Modelo principal de Activos/Herramientas"""
    
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('in_use', 'En Uso'),
        ('maintenance', 'En Mantenimiento'),
        ('damaged', 'Dañado'),
        ('retired', 'Dado de Baja'),
    ]
    
    CONDITION_CHOICES = [
        ('excellent', 'Excelente'),
        ('good', 'Bueno'),
        ('fair', 'Regular'),
        ('poor', 'Malo'),
    ]
    
    # Información básica
    code = models.CharField(max_length=50, unique=True, verbose_name="Código")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    category = models.ForeignKey(
        AssetCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assets',
        verbose_name="Categoría"
    )
    
    # Detalles del activo
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name="Modelo")
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Serie")
    
    # Estado y condición
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='available',
        verbose_name="Estado"
    )
    condition = models.CharField(
        max_length=20, 
        choices=CONDITION_CHOICES, 
        default='good',
        verbose_name="Condición"
    )
    
    # Ubicación y asignación
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="Ubicación")
    assigned_to = models.CharField(max_length=200, blank=True, null=True, verbose_name="Asignado a")
    
    # Información financiera
    purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        blank=True,
        null=True,
        verbose_name="Precio de Compra"
    )
    purchase_date = models.DateField(blank=True, null=True, verbose_name="Fecha de Compra")
    warranty_expiry = models.DateField(blank=True, null=True, verbose_name="Vencimiento de Garantía")
    
    # Mantenimiento
    last_maintenance = models.DateField(blank=True, null=True, verbose_name="Último Mantenimiento")
    next_maintenance = models.DateField(blank=True, null=True, verbose_name="Próximo Mantenimiento")
    maintenance_notes = models.TextField(blank=True, null=True, verbose_name="Notas de Mantenimiento")
    
    # Campos de auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas Adicionales")
    
    class Meta:
        verbose_name = "Activo"
        verbose_name_plural = "Activos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_available(self):
        return self.status == 'available'
    
    @property
    def needs_maintenance(self):
        if self.next_maintenance:
            from django.utils import timezone
            return self.next_maintenance <= timezone.now().date()
        return False