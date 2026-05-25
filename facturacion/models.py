from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db import models
from django.utils import timezone
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
        if not self.barcode:
            self.barcode = self.generate_barcode()
        super().save(*args, **kwargs)

    def generate_barcode(self):
        """Genera un código de barras secuencial único basado en el ID más alto"""
        productos_con_codigo = Product.objects.exclude(
            barcode__isnull=True
        ).exclude(
            barcode=''
        ).values_list('barcode', flat=True)

        max_number = 0

        for barcode in productos_con_codigo:
            try:
                digits = ''.join(filter(str.isdigit, barcode))
                if digits:
                    number = int(digits)
                    if number > max_number:
                        max_number = number
            except ValueError:
                continue

        new_number = max_number + 1
        return f"BB{new_number:05d}"


class ProductHistory(models.Model):
    ACTION_CHOICES = [
        ('created', 'Creado'),
        ('updated', 'Actualizado'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    changed_fields = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Historial de Producto'
        verbose_name_plural = 'Historiales de Productos'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Historial de {self.product.name} ({self.action}) - {self.timestamp:%Y-%m-%d %H:%M:%S}"


@receiver(pre_save, sender=Product)
def create_product_history_record(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        previous = Product.objects.get(pk=instance.pk)
    except Product.DoesNotExist:
        return

    changed = {}
    fields_to_check = ['name', 'description', 'price', 'stock', 'category_id', 'min_stock']

    for field in fields_to_check:
        old_value = getattr(previous, field)
        new_value = getattr(instance, field)
        if old_value != new_value:
            if field == 'category_id':
                changed['category'] = {
                    'old': previous.category.name if previous.category else None,
                    'new': instance.category.name if instance.category else None,
                }
            else:
                changed[field] = {
                    'old': str(old_value) if old_value is not None else None,
                    'new': str(new_value) if new_value is not None else None,
                }

    if changed:
        ProductHistory.objects.create(product=instance, action='updated', changed_fields=changed)


@receiver(post_save, sender=Product)
def create_product_history_on_create(sender, instance, created, **kwargs):
    if not created:
        return

    ProductHistory.objects.create(
        product=instance,
        action='created',
        changed_fields={
            'name': {'old': None, 'new': instance.name},
            'description': {'old': None, 'new': instance.description},
            'price': {'old': None, 'new': str(instance.price)},
            'stock': {'old': None, 'new': str(instance.stock)},
            'category': {'old': None, 'new': instance.category.name if instance.category else None},
            'min_stock': {'old': None, 'new': str(instance.min_stock)},
            'barcode': {'old': None, 'new': instance.barcode},
        }
    )


class Sale(models.Model):
    customer = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        permissions = [
            ('view_sale_totals', 'Can view sale totals'),
        ]

    def calculate_total(self):
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
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"


class Client(models.Model):
    CLIENT_TYPE_CHOICES = [
        ('regular', 'Regular'),
        ('frequent', 'Frecuente'),
        ('occasional', 'Ocasional'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    ruc_ci = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC/CI")
    client_type = models.CharField(
        max_length=20,
        choices=CLIENT_TYPE_CHOICES,
        default='occasional'
    )

    def __str__(self):
        return self.name


class Invoice(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Efectivo'),
        ('card', 'Tarjeta'),
        ('transfer', 'Transferencia'),
    ]

    RECEIPT_TYPES = [
        ('ticket', 'Ticket (Venta Rápida)'),
        ('invoice', 'Factura (Completa)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagada'),
        ('cancelled', 'Anulada'),
        ('refunded', 'Reembolsada'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=True,
        blank=True,
        verbose_name="Cliente"
    )
    invoice_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name="N° Factura")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Subtotal")
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="IVA")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Descuento")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total")
    cash_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Efectivo Recibido")
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Cambio")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name="Método de Pago")
    receipt_type = models.CharField(
        max_length=20,
        choices=RECEIPT_TYPES,
        default='invoice',
        verbose_name="Tipo de Comprobante"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_num = int(last_invoice.invoice_number.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            self.invoice_number = f"FAC-{new_num:08d}"

        if self.subtotal is not None and self.tax is not None and self.discount is not None:
            self.total = self.subtotal + self.tax - self.discount

        super().save(*args, **kwargs)

    def calculate_totals(self):
        details = self.details.all()
        self.subtotal = sum(detail.subtotal for detail in details)
        self.tax = self.subtotal * Decimal('0.16')
        self.total = self.subtotal + self.tax - self.discount
        self.save()

    def __str__(self):
        client_name = self.client.name if self.client else "Consumidor Final"
        return f"{self.invoice_number} - {client_name} - ${self.total}"


class InvoiceDetail(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="details")
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
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


class ServicioManoObra(models.Model):
    """Registro del servicio prestado"""
    
    MODALIDAD_PAGO = [
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
    ]
    
    ESTADO_PAGO = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcialmente Pagado'),
        ('pagado', 'Pagado'),
    ]

    nombre_persona = models.CharField(max_length=70)
    descripcion = models.TextField(blank=True, null=True)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2)
    factura_asociada = models.CharField(max_length=10, blank=True, null=True)
    modalidad_pago = models.CharField(
        max_length=10,
        choices=MODALIDAD_PAGO,
        default='contado'
    )
    estado_pago = models.CharField(
        max_length=10,
        choices=ESTADO_PAGO,
        default='pendiente'
    )
    total_abonado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    @property
    def saldo_pendiente(self):
        return self.precio_total - self.total_abonado

    @property
    def esta_pagado(self):
        return self.saldo_pendiente <= Decimal('0.00')

    def actualizar_estado(self):
        if self.total_abonado <= Decimal('0.00'):
            self.estado_pago = 'pendiente'
        elif self.total_abonado >= self.precio_total:
            self.total_abonado = self.precio_total  # no pasar del total
            self.estado_pago = 'pagado'
        else:
            self.estado_pago = 'parcial'
        self.save(update_fields=['estado_pago', 'total_abonado'])

    def __str__(self):
        return f"{self.nombre_persona} - ${self.precio_total} ({self.estado_pago})"

    class Meta:
        verbose_name = "Servicio de Mano de Obra"
        verbose_name_plural = "Servicios de Mano de Obra"
        ordering = ['-fecha_creacion']


class AbonoServicio(models.Model):
    """Registro de cada pago/abono hecho al servicio"""

    servicio = models.ForeignKey(
        ServicioManoObra,
        on_delete=models.CASCADE,
        related_name='abonos'
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_abono = models.DateTimeField(default=timezone.now)
    notas = models.TextField(blank=True, null=True)
    registrado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalcular total abonado en el servicio
        total = self.servicio.abonos.aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')
        self.servicio.total_abonado = total
        self.servicio.actualizar_estado()

    def __str__(self):
        return f"Abono ${self.monto} → {self.servicio.nombre_persona}"

    class Meta:
        verbose_name = "Abono"
        verbose_name_plural = "Abonos"
        ordering = ['-fecha_abono']
 

# ============ ASSET MANAGEMENT MODULE ============
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
