from django.db import models

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
    image = models.ImageField(upload_to='products/', blank=True, null=True)  # Nuevo campo

    min_stock = models.IntegerField(
        default=3, 
        blank=True, 
        null=True,
        verbose_name="Stock Mínimo"
    )

    def __str__(self):
        return self.name
    

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
    
