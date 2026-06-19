from django.db import models, transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db import models
from django.utils import timezone
from decimal import Decimal

class Category(models.Model):
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='categories',
    )
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'name'],
                condition=models.Q(company__isnull=False),
                name='unique_category_name_per_company',
            ),
        ]

    def __str__(self):
        return self.name


class NumberSequence(models.Model):
    """Transactional numbering for non-DGII commercial/internal sequences."""

    SEQUENCE_KIND_CHOICES = [
        ('commercial', 'Comercial'),
        ('internal', 'Interna'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('invoice', 'Factura'),
        ('quotation', 'Cotizacion'),
        ('credit_note', 'Nota de Credito'),
        ('product_internal_code', 'Codigo interno producto'),
    ]

    code = models.CharField(max_length=80)
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='number_sequences',
    )
    sequence_kind = models.CharField(max_length=20, choices=SEQUENCE_KIND_CHOICES)
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES)
    prefix = models.CharField(max_length=20, blank=True, default='')
    suffix = models.CharField(max_length=20, blank=True, default='')
    next_number = models.PositiveBigIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=8)
    scope_key = models.CharField(max_length=80, default='default')
    issuer = models.ForeignKey(
        'ECFIssuerConfig',
        on_delete=models.PROTECT,
        related_name='number_sequences',
        null=True,
        blank=True,
    )
    branch_code = models.CharField(max_length=40, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Secuencia numerica'
        verbose_name_plural = 'Secuencias numericas'
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code', 'scope_key', 'branch_code'],
                condition=models.Q(company__isnull=False, issuer__isnull=True),
                name='unique_number_sequence_company_default_scope',
            ),
            models.UniqueConstraint(
                fields=['company', 'code', 'scope_key', 'issuer', 'branch_code'],
                condition=models.Q(company__isnull=False, issuer__isnull=False),
                name='unique_number_sequence_company_issuer_scope',
            )
        ]

    def clean(self):
        if self.company_id and self.issuer_id and self.issuer.company_id and self.issuer.company_id != self.company_id:
            raise ValidationError({'issuer': 'El emisor debe pertenecer a la misma empresa que la secuencia.'})
        if not self.company_id and self.issuer_id and self.issuer.company_id:
            self.company_id = self.issuer.company_id

    def format_number(self, number):
        return f"{self.prefix}{number:0{self.padding}d}{self.suffix}"

    def __str__(self):
        return f"{self.code} -> {self.format_number(self.next_number)}"


class Company(models.Model):
    """SaaS company/account boundary introduced before tenant scoping."""

    name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=150, blank=True, default='')
    rnc = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, default='')
    address = models.TextField(blank=True, default='')
    logo = models.ImageField(upload_to='companies/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['name']

    def __str__(self):
        return self.name


class CompanyMembership(models.Model):
    """User membership and role inside one SaaS company."""

    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_SUPERVISOR = 'supervisor'
    ROLE_CASHIER = 'cashier'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_READONLY = 'readonly'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_SUPERVISOR, 'Supervisor'),
        (ROLE_CASHIER, 'Cajero'),
        (ROLE_ACCOUNTANT, 'Contador'),
        (ROLE_READONLY, 'Solo lectura'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='company_memberships')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CASHIER)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Membresía de empresa'
        verbose_name_plural = 'Membresías de empresa'
        ordering = ['company__name', 'user__username']
        constraints = [
            models.UniqueConstraint(fields=['user', 'company'], name='unique_company_membership_user_company'),
        ]

    def __str__(self):
        return f"{self.user} @ {self.company} ({self.role})"


class Product(models.Model):
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='products',
    )
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
        blank=True,
        null=True,
        verbose_name="Código de Barras"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'barcode'],
                condition=(
                    models.Q(company__isnull=False)
                    & models.Q(barcode__isnull=False)
                    & ~models.Q(barcode='')
                ),
                name='unique_product_barcode_per_company',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.barcode:
            from facturacion.services.numbering import NumberingService

            self.barcode = NumberingService().allocate_unique(
                code='product_internal_code',
                model_class=Product,
                field_name='barcode',
                company=self.company,
            )
        super().save(*args, **kwargs)

    def generate_barcode(self):
        """Backward-compatible barcode generator using transactional sequences."""
        from facturacion.services.numbering import NumberingService

        return NumberingService().allocate_unique(
            code='product_internal_code',
            model_class=Product,
            field_name='barcode',
            company=self.company,
        )


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
        # TODO(2A-final-cleanup): Sale permissions are legacy compatibility gates.
        # Invoice permissions should become the commercial reporting source of truth.
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

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='clients',
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    ruc_ci = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUC/CI")
    client_type = models.CharField(
        max_length=20,
        choices=CLIENT_TYPE_CHOICES,
        default='occasional'
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'ruc_ci'],
                condition=(
                    models.Q(company__isnull=False)
                    & models.Q(ruc_ci__isnull=False)
                    & ~models.Q(ruc_ci='')
                ),
                name='unique_client_ruc_ci_per_company',
            ),
        ]


class Quotation(models.Model):
    """Commercial estimate that does not allocate fiscal sequences or affect stock."""

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('expired', 'Expirada'),
    ]

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='quotations',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='quotations',
        null=True,
        blank=True,
        verbose_name='Cliente',
    )
    quotation_number = models.CharField(max_length=20, blank=True, verbose_name='N° Cotización')
    customer_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Cliente no registrado')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    valid_until = models.DateField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    expired_at = models.DateTimeField(blank=True, null=True)
    converted_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'quotation_number'],
                name='unique_quotation_number_per_company',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            from facturacion.services.numbering import NumberingService

            self.quotation_number = NumberingService().allocate_unique(
                code='quotation',
                model_class=Quotation,
                field_name='quotation_number',
                company=self.company,
            )
        super().save(*args, **kwargs)

    @property
    def customer_display(self):
        return self.client.name if self.client_id else (self.customer_name or 'Consumidor Final')

    @property
    def generated_invoice(self):
        return getattr(self, 'invoice', None)

    def __str__(self):
        return f"{self.quotation_number} - {self.customer_display}"


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

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=True,
        blank=True,
        verbose_name="Cliente"
    )
    origin_quotation = models.OneToOneField(
        Quotation,
        on_delete=models.SET_NULL,
        related_name='invoice',
        null=True,
        blank=True,
        verbose_name='Cotización origen',
    )
    invoice_number = models.CharField(max_length=20, blank=True, verbose_name="N° Factura")
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
    inventory_committed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Inventario comprometido"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'invoice_number'],
                name='unique_invoice_number_per_company',
            ),
        ]
        permissions = [
            ('reverse_invoice', 'Can create fiscal invoice reversals'),
            ('view_financial_totals', 'Can view financial totals'),
        ]

    FISCAL_LOCKED_ECF_STATUSES = {'signed', 'submitted', 'accepted'}

    @property
    def fiscal_document(self):
        return getattr(self, 'electronic_document', None)

    @property
    def is_fiscally_locked(self):
        document = self.fiscal_document
        return bool(document and document.fiscal_status in self.FISCAL_LOCKED_ECF_STATUSES)

    @property
    def fiscal_lock_reason(self):
        if not self.is_fiscally_locked:
            return ''
        return 'La factura tiene un e-CF firmado, enviado, en proceso o aceptado. Debe reversarse con nota de credito.'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from facturacion.services.numbering import NumberingService

            self.invoice_number = NumberingService().allocate_unique(
                code='invoice',
                model_class=Invoice,
                field_name='invoice_number',
                company=self.company,
            )

        if self.subtotal is not None and self.tax is not None and self.discount is not None:
            self.total = self.subtotal + self.tax - self.discount

        super().save(*args, **kwargs)

    def calculate_totals(self):
        from facturacion.services.fiscal_rules import FiscalCalculationService

        details = self.details.all()
        self.subtotal = sum(detail.subtotal for detail in details)
        fiscal_totals = FiscalCalculationService().calculate_invoice_totals(self.subtotal, self.discount)
        self.tax = fiscal_totals.tax
        self.total = fiscal_totals.total
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


class QuotationDetail(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (Cotización #{self.quotation_id})"


class CreditNote(models.Model):
    """Fiscal credit note used to reverse an accepted or signed invoice."""

    REVERSAL_TYPE_CHOICES = [
        ('partial', 'Parcial'),
        ('total', 'Total'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('issued', 'Emitida'),
        ('cancelled', 'Anulada'),
    ]

    FISCAL_RESOLUTION_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('rejected', 'Rechazada'),
        ('resolved', 'Resuelta'),
    ]

    INVENTORY_RECONCILIATION_STATUS_CHOICES = [
        ('restored_pending', 'Restaurado Pendiente'),
        ('confirmed', 'Confirmado'),
        ('compensation_required', 'Compensacion Requerida'),
        ('compensated', 'Compensado'),
    ]

    origin_invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='credit_notes',
        verbose_name='Factura origen',
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='credit_notes',
    )
    credit_note_number = models.CharField(max_length=20, blank=True, verbose_name='N° Nota de Crédito')
    reversal_type = models.CharField(max_length=20, choices=REVERSAL_TYPE_CHOICES, default='partial')
    reason = models.TextField(verbose_name='Motivo fiscal')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    inventory_restored_at = models.DateTimeField(null=True, blank=True)
    fiscal_resolution_status = models.CharField(max_length=20, choices=FISCAL_RESOLUTION_STATUS_CHOICES, default='pending')
    inventory_reconciliation_status = models.CharField(max_length=30, choices=INVENTORY_RECONCILIATION_STATUS_CHOICES, default='restored_pending')
    inventory_reconciled_at = models.DateTimeField(null=True, blank=True)
    inventory_compensated_at = models.DateTimeField(null=True, blank=True)
    requires_manual_review = models.BooleanField(default=False)
    manual_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Nota de Crédito'
        verbose_name_plural = 'Notas de Crédito'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'credit_note_number'],
                name='unique_credit_note_number_per_company',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.credit_note_number:
            from facturacion.services.numbering import NumberingService

            self.credit_note_number = NumberingService().allocate_unique(
                code='credit_note',
                model_class=CreditNote,
                field_name='credit_note_number',
                company=self.company,
            )
        super().save(*args, **kwargs)

    @property
    def fiscal_document(self):
        return getattr(self, 'electronic_document', None)

    def __str__(self):
        return f"{self.credit_note_number} -> {self.origin_invoice.invoice_number}"


class CreditNoteDetail(models.Model):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name='details')
    origin_detail = models.ForeignKey(InvoiceDetail, on_delete=models.PROTECT, related_name='credit_note_details')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (NC #{self.credit_note_id})"


class Almacen(models.Model):
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='almacenes',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=20, blank=True, null=True)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='almacenes')

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'name'],
                condition=models.Q(company__isnull=False),
                name='unique_almacen_name_per_company',
            ),
        ]


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

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='servicios_mano_obra',
    )
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

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='abonos_servicio',
    )
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
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='asset_categories',
    )
    name = models.CharField(max_length=100, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría de Activo"
        verbose_name_plural = "Categorías de Activos"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'name'],
                condition=models.Q(company__isnull=False),
                name='unique_asset_category_name_per_company',
            ),
        ]

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
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='assets',
    )
    code = models.CharField(max_length=50, verbose_name="Código")
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
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code'],
                condition=models.Q(company__isnull=False),
                name='unique_asset_code_per_company',
            ),
        ]

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


# ============ DGII E-CF MODULE ============
class ECFIssuerConfig(models.Model):
    """Datos fiscales del emisor autorizados para facturacion electronica."""

    ENVIRONMENT_CHOICES = [
        ('testing', 'Pruebas'),
        ('certification', 'Certificacion'),
        ('production', 'Produccion'),
    ]

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='ecf_issuers',
    )
    business_name = models.CharField(max_length=150, verbose_name="Razón Social")
    trade_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nombre Comercial")
    rnc = models.CharField(max_length=11, unique=True, verbose_name="RNC Emisor")
    address = models.TextField(verbose_name="Dirección")
    municipality = models.CharField(max_length=80, blank=True, null=True, verbose_name="Municipio")
    province = models.CharField(max_length=80, blank=True, null=True, verbose_name="Provincia")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo")
    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default='testing',
        verbose_name="Ambiente DGII",
    )
    default_ecf_type = models.CharField(
        max_length=2,
        choices=[('31', 'Factura de Crédito Fiscal Electrónica'), ('32', 'Factura de Consumo Electrónica')],
        default='32',
        verbose_name='Tipo e-CF por defecto',
    )
    auto_ecf_rules_enabled = models.BooleanField(default=True, verbose_name='Reglas automáticas E31/E32')
    certificate_path = models.CharField(max_length=500, blank=True, null=True, verbose_name='Ruta Certificado P12')
    certificate_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='Clave Certificado')
    certificate_subject = models.CharField(blank=True, max_length=255, null=True, verbose_name='Asunto Certificado')
    certificate_issuer = models.CharField(blank=True, max_length=255, null=True, verbose_name='Emisor Certificado')
    certificate_serial_number = models.CharField(blank=True, max_length=100, null=True, verbose_name='Número de Serie Certificado')
    certificate_fingerprint = models.CharField(blank=True, max_length=128, null=True, verbose_name='Huella SHA-256 Certificado')
    certificate_not_valid_before = models.DateTimeField(blank=True, null=True, verbose_name='Certificado Válido Desde')
    certificate_not_valid_after = models.DateTimeField(blank=True, null=True, verbose_name='Certificado Válido Hasta')
    certificate_rnc_detected = models.CharField(blank=True, max_length=255, null=True, verbose_name='RNC Detectado en Certificado')
    CERTIFICATE_RNC_MATCH_UNKNOWN = 'unknown'
    CERTIFICATE_RNC_MATCH_MATCHED = 'matched'
    CERTIFICATE_RNC_MATCH_MISMATCH = 'mismatch'
    CERTIFICATE_RNC_MATCH_NOT_FOUND = 'not_found'
    CERTIFICATE_RNC_MATCH_CHOICES = [
        (CERTIFICATE_RNC_MATCH_UNKNOWN, 'Desconocido'),
        (CERTIFICATE_RNC_MATCH_MATCHED, 'Coincide'),
        (CERTIFICATE_RNC_MATCH_MISMATCH, 'No coincide'),
        (CERTIFICATE_RNC_MATCH_NOT_FOUND, 'No encontrado'),
    ]
    certificate_rnc_match_status = models.CharField(
        choices=CERTIFICATE_RNC_MATCH_CHOICES,
        default=CERTIFICATE_RNC_MATCH_UNKNOWN,
        max_length=20,
        verbose_name='Coincidencia RNC Certificado',
    )
    CERTIFICATE_STATUS_MISSING = 'missing'
    CERTIFICATE_STATUS_ACTIVE = 'active'
    CERTIFICATE_STATUS_EXPIRING = 'expiring_soon'
    CERTIFICATE_STATUS_EXPIRED = 'expired'
    CERTIFICATE_STATUS_INVALID = 'invalid'
    CERTIFICATE_STATUS_CHOICES = [
        (CERTIFICATE_STATUS_MISSING, 'Faltante'),
        (CERTIFICATE_STATUS_ACTIVE, 'Activo'),
        (CERTIFICATE_STATUS_EXPIRING, 'Por vencer'),
        (CERTIFICATE_STATUS_EXPIRED, 'Vencido'),
        (CERTIFICATE_STATUS_INVALID, 'Inválido'),
    ]
    certificate_status = models.CharField(choices=CERTIFICATE_STATUS_CHOICES, default=CERTIFICATE_STATUS_MISSING, max_length=20, verbose_name='Estado Certificado')
    certificate_status_updated_at = models.DateTimeField(blank=True, null=True, verbose_name='Actualizado Certificado')
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración e-CF del Emisor"
        verbose_name_plural = "Configuraciones e-CF del Emisor"
        ordering = ['-is_active', 'business_name']

    def clean(self):
        digits = ''.join(filter(str.isdigit, self.rnc or ''))
        if len(digits) not in (9, 11):
            raise ValidationError({'rnc': 'El RNC/Cédula debe tener 9 u 11 dígitos.'})
        self.rnc = digits

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_name} ({self.rnc})"


class ECFCertificate(models.Model):
    """Historial de certificados DGII asociados a un emisor fiscal.

    Preparacion para almacenamiento seguro: certificate_reference y
    password_secret_reference son referencias, no deben asumirse como secretos
    finales en produccion.
    """

    STORAGE_BACKEND_LEGACY_LOCAL = 'legacy_local'
    STORAGE_BACKEND_DJANGO_STORAGE = 'django_storage'
    STORAGE_BACKEND_KMS = 'kms'
    STORAGE_BACKEND_VAULT = 'vault'
    STORAGE_BACKEND_CHOICES = [
        (STORAGE_BACKEND_LEGACY_LOCAL, 'Legacy local'),
        (STORAGE_BACKEND_DJANGO_STORAGE, 'Django storage'),
        (STORAGE_BACKEND_KMS, 'KMS / Secret manager'),
        (STORAGE_BACKEND_VAULT, 'Vault'),
    ]

    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='ecf_certificates',
    )
    issuer = models.ForeignKey(
        ECFIssuerConfig,
        on_delete=models.PROTECT,
        related_name='certificates',
    )
    environment = models.CharField(max_length=20, choices=ECFIssuerConfig.ENVIRONMENT_CHOICES, default='testing')
    status = models.CharField(
        max_length=20,
        choices=ECFIssuerConfig.CERTIFICATE_STATUS_CHOICES,
        default=ECFIssuerConfig.CERTIFICATE_STATUS_MISSING,
    )
    storage_backend = models.CharField(
        max_length=40,
        choices=STORAGE_BACKEND_CHOICES,
        default=STORAGE_BACKEND_LEGACY_LOCAL,
    )
    certificate_reference = models.CharField(max_length=500)
    password_secret_reference = models.CharField(max_length=500, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    issuer_name = models.CharField(max_length=255, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    fingerprint = models.CharField(max_length=128, blank=True, null=True)
    not_valid_before = models.DateTimeField(blank=True, null=True)
    not_valid_after = models.DateTimeField(blank=True, null=True)
    rnc_detected = models.CharField(max_length=255, blank=True, null=True)
    rnc_match_status = models.CharField(
        max_length=20,
        choices=ECFIssuerConfig.CERTIFICATE_RNC_MATCH_CHOICES,
        default=ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN,
    )
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='uploaded_ecf_certificates',
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    activated_at = models.DateTimeField(blank=True, null=True)
    deactivated_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    previous_certificate = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='next_certificates',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', '-uploaded_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'issuer', 'environment'],
                condition=models.Q(is_active=True),
                name='unique_active_ecf_certificate_per_issuer_env',
            ),
            models.UniqueConstraint(
                fields=['issuer', 'fingerprint'],
                condition=models.Q(fingerprint__isnull=False) & ~models.Q(fingerprint=''),
                name='unique_ecf_certificate_fingerprint_per_issuer',
            ),
        ]

    def clean(self):
        if self.company_id and self.issuer_id and self.issuer.company_id != self.company_id:
            raise ValidationError({'issuer': 'El certificado debe pertenecer a la misma empresa que el emisor.'})
        if not self.company_id and self.issuer_id:
            self.company_id = self.issuer.company_id
        if not self.environment and self.issuer_id:
            self.environment = self.issuer.environment

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.fingerprint or self.serial_number or self.certificate_reference
        return f"{self.issuer} - {label}"


class ECFSequence(models.Model):
    """Rango autorizado de e-NCF otorgado por DGII."""

    ECF_TYPE_CHOICES = [
        ('31', 'Factura de Crédito Fiscal Electrónica'),
        ('32', 'Factura de Consumo Electrónica'),
        ('33', 'Nota de Débito Electrónica'),
        ('34', 'Nota de Crédito Electrónica'),
        ('41', 'Compras Electrónico'),
        ('43', 'Gastos Menores Electrónico'),
        ('44', 'Regímenes Especiales Electrónico'),
        ('45', 'Gubernamental Electrónico'),
        ('46', 'Exportaciones Electrónico'),
        ('47', 'Pagos al Exterior Electrónico'),
    ]

    issuer = models.ForeignKey(
        ECFIssuerConfig,
        on_delete=models.PROTECT,
        related_name='ecf_sequences',
        verbose_name="Emisor",
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='ecf_sequences',
    )
    ecf_type = models.CharField(max_length=2, choices=ECF_TYPE_CHOICES, verbose_name="Tipo e-CF")
    start_number = models.PositiveBigIntegerField(verbose_name="Secuencia Inicial")
    end_number = models.PositiveBigIntegerField(verbose_name="Secuencia Final")
    next_number = models.PositiveBigIntegerField(verbose_name="Próxima Secuencia")
    authorization_date = models.DateField(blank=True, null=True, verbose_name="Fecha Autorización")
    expiration_date = models.DateField(blank=True, null=True, verbose_name="Fecha Vencimiento")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Secuencia e-NCF"
        verbose_name_plural = "Secuencias e-NCF"
        ordering = ['ecf_type', 'start_number']
        constraints = [
            models.UniqueConstraint(
                fields=['issuer', 'ecf_type', 'start_number', 'end_number'],
                name='unique_ecf_sequence_range',
            )
        ]

    def clean(self):
        if self.start_number > self.end_number:
            raise ValidationError({'end_number': 'La secuencia final debe ser mayor o igual a la inicial.'})
        if self.company_id and self.issuer_id and self.issuer.company_id and self.issuer.company_id != self.company_id:
            raise ValidationError({'issuer': 'El emisor debe pertenecer a la misma empresa que la secuencia.'})
        if not self.company_id and self.issuer_id and self.issuer.company_id:
            self.company_id = self.issuer.company_id
        if not self.next_number:
            self.next_number = self.start_number
        if self.next_number < self.start_number or self.next_number > self.end_number:
            raise ValidationError({'next_number': 'La próxima secuencia debe estar dentro del rango autorizado.'})
        if self.issuer_id and self.ecf_type and self.start_number is not None and self.end_number is not None:
            overlapping = (
                ECFSequence.objects
                .filter(
                    issuer_id=self.issuer_id,
                    ecf_type=self.ecf_type,
                    start_number__lte=self.end_number,
                    end_number__gte=self.start_number,
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if overlapping:
                raise ValidationError({'start_number': 'El rango e-NCF se solapa con otro rango del mismo emisor y tipo e-CF.'})

    @property
    def remaining(self):
        return max(self.end_number - self.next_number + 1, 0)

    def format_encf(self, number):
        return f"E{self.ecf_type}{number:010d}"

    @classmethod
    def allocate_next(cls, issuer, ecf_type):
        with transaction.atomic():
            sequence = (
                cls.objects
                .select_for_update()
                .filter(issuer=issuer, company=issuer.company, ecf_type=ecf_type, is_active=True)
                .order_by('next_number')
                .first()
            )
            if not sequence:
                raise ValidationError(f"No hay secuencia activa para e-CF tipo {ecf_type}.")
            if sequence.next_number > sequence.end_number:
                raise ValidationError(f"La secuencia e-CF tipo {ecf_type} está agotada.")

            assigned_number = sequence.next_number
            sequence.next_number += 1
            sequence.save(update_fields=['next_number', 'updated_at'])
            return sequence.format_encf(assigned_number), sequence

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"E{self.ecf_type} {self.start_number:010d}-{self.end_number:010d}"


class ElectronicFiscalDocument(models.Model):
    """Estado y trazabilidad DGII de una factura emitida como e-CF."""

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('queued', 'En Cola'),
        ('xml_generated', 'XML Generado'),
        ('signed', 'Firmado'),
        ('pending', 'Pendiente DGII'),
        ('submitted', 'Enviado a DGII'),
        ('processing', 'En Proceso DGII'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('error', 'Error DGII'),
        ('cancelled', 'Anulado'),
    ]

    FISCAL_STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('xml_generated', 'XML Generado'),
        ('signed', 'Firmado'),
        ('submitted', 'Enviado a DGII'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
    ]

    JOB_STATUS_CHOICES = [
        ('idle', 'Inactivo'),
        ('queued', 'En Cola'),
        ('running', 'Ejecutando'),
        ('retrying', 'Reintentando'),
        ('failed', 'Fallido'),
    ]

    invoice = models.OneToOneField(
        Invoice,
        on_delete=models.PROTECT,
        related_name='electronic_document',
        verbose_name="Factura",
        null=True,
        blank=True,
    )
    credit_note = models.OneToOneField(
        CreditNote,
        on_delete=models.PROTECT,
        related_name='electronic_document',
        verbose_name='Nota de Crédito',
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.PROTECT,
        related_name='electronic_fiscal_documents',
    )
    issuer = models.ForeignKey(
        ECFIssuerConfig,
        on_delete=models.PROTECT,
        related_name='electronic_documents',
        verbose_name="Emisor",
    )
    sequence = models.ForeignKey(
        ECFSequence,
        on_delete=models.PROTECT,
        related_name='electronic_documents',
        verbose_name="Secuencia",
    )
    ecf_type = models.CharField(max_length=2, choices=ECFSequence.ECF_TYPE_CHOICES, verbose_name="Tipo e-CF")
    encf = models.CharField(max_length=13, verbose_name="e-NCF")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Estado")
    fiscal_status = models.CharField(
        max_length=20,
        choices=FISCAL_STATUS_CHOICES,
        default='draft',
        db_index=True,
        verbose_name="Estado Fiscal",
    )
    job_status = models.CharField(
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default='idle',
        db_index=True,
        verbose_name="Estado Técnico",
    )
    track_id = models.CharField(max_length=80, blank=True, null=True, verbose_name="TrackID DGII")
    xml_content = models.TextField(blank=True, null=True, verbose_name="XML")
    signed_xml_content = models.TextField(blank=True, null=True, verbose_name="XML Firmado")
    dgii_request_xml = models.TextField(blank=True, null=True, verbose_name="Request DGII")
    dgii_response_xml = models.TextField(blank=True, null=True, verbose_name="Response DGII")
    dgii_response = models.JSONField(blank=True, null=True, verbose_name="Respuesta DGII")
    last_submitted_at = models.DateTimeField(blank=True, null=True, verbose_name="Último Envío")
    last_status_checked_at = models.DateTimeField(blank=True, null=True, verbose_name="Última Consulta Estado")
    accepted_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha Aceptación")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Motivo Rechazo")
    async_task_id = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Task Celery Actual")
    idempotency_key = models.CharField(max_length=120, blank=True, null=True, db_index=True, verbose_name="Clave Idempotencia")
    submission_attempts = models.PositiveIntegerField(default=0, verbose_name="Intentos de Envío")
    status_check_attempts = models.PositiveIntegerField(default=0, verbose_name="Intentos Consulta Estado")
    next_retry_at = models.DateTimeField(blank=True, null=True, verbose_name="Próximo Reintento")
    last_error = models.TextField(blank=True, null=True, verbose_name="Último Error")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento Fiscal Electrónico"
        verbose_name_plural = "Documentos Fiscales Electrónicos"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['issuer', 'encf'],
                name='unique_ecf_document_encf_per_issuer',
            ),
        ]

    def clean(self):
        if self.encf and (len(self.encf) != 13 or not self.encf.startswith(f"E{self.ecf_type}")):
            raise ValidationError({'encf': 'El e-NCF debe tener formato E + tipo e-CF + 10 dígitos.'})
        if bool(self.invoice_id) == bool(self.credit_note_id):
            raise ValidationError('El documento fiscal debe pertenecer a una factura o a una nota de credito, pero no a ambas.')
        if not self.company_id:
            if self.invoice_id and self.invoice.company_id:
                self.company_id = self.invoice.company_id
            elif self.credit_note_id and self.credit_note.company_id:
                self.company_id = self.credit_note.company_id
            elif self.issuer_id and self.issuer.company_id:
                self.company_id = self.issuer.company_id

        if self.company_id:
            if self.invoice_id and self.invoice.company_id and self.invoice.company_id != self.company_id:
                raise ValidationError({'invoice': 'La factura debe pertenecer a la misma empresa que el e-CF.'})
            if self.credit_note_id and self.credit_note.company_id and self.credit_note.company_id != self.company_id:
                raise ValidationError({'credit_note': 'La nota de credito debe pertenecer a la misma empresa que el e-CF.'})
            if self.issuer_id and self.issuer.company_id and self.issuer.company_id != self.company_id:
                raise ValidationError({'issuer': 'El emisor debe pertenecer a la misma empresa que el e-CF.'})
            if self.sequence_id and self.sequence.company_id and self.sequence.company_id != self.company_id:
                raise ValidationError({'sequence': 'La secuencia debe pertenecer a la misma empresa que el e-CF.'})

    def save(self, *args, **kwargs):
        fiscal_values = {choice[0] for choice in self.FISCAL_STATUS_CHOICES}
        if self.status in fiscal_values and (not self.fiscal_status or self.fiscal_status == 'draft'):
            self.fiscal_status = self.status
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        source = self.invoice.invoice_number if self.invoice_id else self.credit_note.credit_note_number
        return f"{self.encf} - {source}"


class ECFStatusEvent(models.Model):
    """Auditable fiscal/job status transition history for e-CF documents."""

    document = models.ForeignKey(
        ElectronicFiscalDocument,
        on_delete=models.CASCADE,
        related_name='status_events',
    )
    previous_fiscal_status = models.CharField(max_length=20, blank=True, null=True)
    new_fiscal_status = models.CharField(max_length=20, blank=True, null=True)
    previous_job_status = models.CharField(max_length=20, blank=True, null=True)
    new_job_status = models.CharField(max_length=20, blank=True, null=True)
    source = models.CharField(max_length=80)
    reason = models.TextField(blank=True, null=True)
    task_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de Estado e-CF"
        verbose_name_plural = "Eventos de Estado e-CF"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document.encf} {self.previous_fiscal_status}->{self.new_fiscal_status}"


class ECFEventLog(models.Model):
    """Bitácora de eventos de generación, firma, envío y consulta e-CF."""

    EVENT_CHOICES = [
        ('created', 'Creado'),
        ('queued', 'Encolado'),
        ('xml_generated', 'XML Generado'),
        ('signed', 'Firmado'),
        ('submitted', 'Enviado'),
        ('status_checked', 'Estado Consultado'),
        ('retry_scheduled', 'Reintento Programado'),
        ('skipped', 'Omitido'),
        ('inventory_restored', 'Inventario Restaurado'),
        ('inventory_compensated', 'Inventario Compensado'),
        ('manual_review', 'Revision Manual'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Anulado'),
        ('error', 'Error'),
    ]

    electronic_document = models.ForeignKey(
        ElectronicFiscalDocument,
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    message = models.TextField(blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento e-CF"
        verbose_name_plural = "Eventos e-CF"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.electronic_document.encf} - {self.event_type}"


class DGIICertificationPlan(models.Model):
    """Plan importado desde el set Excel DGII para pruebas de certificacion."""

    STATUS_IMPORTED = 'imported'
    STATUS_CHOICES = [
        (STATUS_IMPORTED, 'Importado'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='dgii_certification_plans',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IMPORTED)
    source_filename = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64, db_index=True)
    imported_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dgii_certification_imports',
    )
    imported_at = models.DateTimeField(default=timezone.now)
    total_items = models.PositiveIntegerField(default=0)
    group_counts = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plan de certificacion DGII'
        verbose_name_plural = 'Planes de certificacion DGII'
        ordering = ['-imported_at']

    def __str__(self):
        return f"{self.company} - {self.source_filename}"


class DGIICertificationItem(models.Model):
    """Escenario e-CF detectado en el Excel DGII."""

    STATUS_PENDING = 'pending'
    STATUS_GENERATED = 'generated'
    STATUS_SIGNED = 'signed'
    STATUS_SENT = 'sent'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_GENERATED, 'Generado'),
        (STATUS_SIGNED, 'Firmado'),
        (STATUS_SENT, 'Enviado'),
        (STATUS_ACCEPTED, 'Aceptado'),
        (STATUS_REJECTED, 'Rechazado'),
    ]

    ECF_TYPE_CHOICES = [
        ('31', 'Factura Credito Fiscal'),
        ('32', 'Factura Consumo'),
        ('33', 'Nota Debito'),
        ('34', 'Nota Credito'),
        ('41', 'Compras'),
        ('43', 'Gastos Menores'),
        ('44', 'Regimenes Especiales'),
        ('45', 'Gubernamental'),
        ('46', 'Exportaciones'),
        ('47', 'Pagos Exterior'),
        ('RFCE', 'Resumen Factura Consumo'),
    ]

    plan = models.ForeignKey(
        DGIICertificationPlan,
        on_delete=models.CASCADE,
        related_name='items',
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='dgii_certification_items',
    )
    ecf_type = models.CharField(max_length=10, choices=ECF_TYPE_CHOICES)
    dgii_group = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    encf = models.CharField(max_length=30, blank=True, default='')
    document_type = models.CharField(max_length=120, blank=True, default='')
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    receiver_rnc = models.CharField(max_length=20, blank=True, default='')
    receiver_name = models.CharField(max_length=180, blank=True, default='')
    observations = models.TextField(blank=True, default='')
    source_sheet = models.CharField(max_length=120)
    source_row = models.PositiveIntegerField()
    raw_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Item de certificacion DGII'
        verbose_name_plural = 'Items de certificacion DGII'
        ordering = ['dgii_group', 'ecf_type', 'source_sheet', 'source_row']
        constraints = [
            models.UniqueConstraint(
                fields=['plan', 'source_sheet', 'source_row'],
                name='unique_dgii_cert_item_source_row_per_plan',
            ),
        ]

    def __str__(self):
        return f"Grupo {self.dgii_group} - {self.ecf_type} - fila {self.source_row}"


class DGIICertificationEvent(models.Model):
    """Auditoria del importador y plan de certificacion DGII."""

    EVENT_EXCEL_IMPORTED = 'excel_imported'
    EVENT_PLAN_CREATED = 'plan_created'
    EVENT_ITEM_DETECTED = 'item_detected'
    EVENT_IMPORT_ERROR = 'import_error'
    EVENT_CHOICES = [
        (EVENT_EXCEL_IMPORTED, 'Excel importado'),
        (EVENT_PLAN_CREATED, 'Plan creado'),
        (EVENT_ITEM_DETECTED, 'Item detectado'),
        (EVENT_IMPORT_ERROR, 'Error de importacion'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='dgii_certification_events',
    )
    plan = models.ForeignKey(
        DGIICertificationPlan,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
    )
    item = models.ForeignKey(
        DGIICertificationItem,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    message = models.TextField(blank=True, default='')
    payload = models.JSONField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento certificacion DGII'
        verbose_name_plural = 'Eventos certificacion DGII'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.company}"


class DGIIPublicRequestLog(models.Model):
    """Auditoria segura de endpoints publicos solicitados por postulacion DGII."""

    endpoint = models.CharField(max_length=120, db_index=True)
    method = models.CharField(max_length=10)
    content_type = models.CharField(max_length=120, blank=True, default='')
    safe_headers = models.JSONField(blank=True, null=True)
    body_sha256 = models.CharField(max_length=64, blank=True, default='')
    body_preview = models.TextField(blank=True, default='')
    rnc = models.CharField(max_length=20, blank=True, default='', db_index=True)
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    response_status = models.PositiveSmallIntegerField()
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Request publico DGII"
        verbose_name_plural = "Requests publicos DGII"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.method} {self.endpoint} -> {self.response_status}"
