from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Product)
# admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(InvoiceDetail)
admin.site.register(CreditNote)
admin.site.register(CreditNoteDetail)
admin.site.register(Quotation)
admin.site.register(QuotationDetail)
admin.site.register(Company)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']





@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category', 'status', 'condition', 
        'location', 'assigned_to', 'created_at'
    ]
    list_filter = ['status', 'condition', 'category', 'created_at']
    search_fields = ['code', 'name', 'brand', 'model', 'serial_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'description', 'category')
        }),
        ('Detalles del Activo', {
            'fields': ('brand', 'model', 'serial_number')
        }),
        ('Estado y Ubicación', {
            'fields': ('status', 'condition', 'location', 'assigned_to')
        }),
        ('Información Financiera', {
            'fields': ('purchase_price', 'purchase_date', 'warranty_expiry')
        }),
        ('Mantenimiento', {
            'fields': ('last_maintenance', 'next_maintenance', 'maintenance_notes')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(ECFIssuerConfig)
class ECFIssuerConfigAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'rnc', 'environment', 'is_active', 'updated_at']
    list_filter = ['environment', 'is_active']
    search_fields = ['business_name', 'trade_name', 'rnc']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ECFSequence)
class ECFSequenceAdmin(admin.ModelAdmin):
    list_display = ['issuer', 'ecf_type', 'start_number', 'end_number', 'next_number', 'remaining', 'is_active']
    list_filter = ['ecf_type', 'is_active', 'issuer']
    search_fields = ['issuer__business_name', 'issuer__rnc']
    readonly_fields = ['created_at', 'updated_at']


class ECFEventLogInline(admin.TabularInline):
    model = ECFEventLog
    extra = 0
    readonly_fields = ['event_type', 'message', 'payload', 'created_by', 'created_at']
    can_delete = False


@admin.register(ElectronicFiscalDocument)
class ElectronicFiscalDocumentAdmin(admin.ModelAdmin):
    list_display = ['encf', 'invoice', 'credit_note', 'issuer', 'ecf_type', 'status', 'track_id', 'submission_attempts', 'created_at']
    list_filter = ['status', 'ecf_type', 'issuer']
    search_fields = ['encf', 'track_id', 'invoice__invoice_number', 'credit_note__credit_note_number', 'issuer__business_name']
    readonly_fields = [
        'created_at', 'updated_at', 'last_submitted_at', 'accepted_at',
        'last_status_checked_at', 'xml_content', 'signed_xml_content',
        'dgii_request_xml', 'dgii_response_xml', 'dgii_response',
        'async_task_id', 'idempotency_key', 'submission_attempts',
        'status_check_attempts', 'next_retry_at', 'last_error',
    ]
    inlines = [ECFEventLogInline]


@admin.register(ECFEventLog)
class ECFEventLogAdmin(admin.ModelAdmin):
    list_display = ['electronic_document', 'event_type', 'created_by', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['electronic_document__encf', 'message']
    readonly_fields = ['created_at']


@admin.register(ECFStatusEvent)
class ECFStatusEventAdmin(admin.ModelAdmin):
    list_display = ['document', 'previous_fiscal_status', 'new_fiscal_status', 'previous_job_status', 'new_job_status', 'source', 'created_at']
    list_filter = ['source', 'new_fiscal_status', 'new_job_status', 'created_at']
    search_fields = ['document__encf', 'reason', 'task_id']
    readonly_fields = [
        'document', 'previous_fiscal_status', 'new_fiscal_status',
        'previous_job_status', 'new_job_status', 'source', 'reason',
        'task_id', 'created_at',
    ]


@admin.register(DGIIPublicRequestLog)
class DGIIPublicRequestLogAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'method', 'rnc', 'response_status', 'created_at']
    list_filter = ['endpoint', 'method', 'response_status', 'created_at']
    search_fields = ['rnc', 'body_sha256', 'error']
    readonly_fields = [
        'endpoint', 'method', 'content_type', 'safe_headers', 'body_sha256',
        'body_preview', 'rnc', 'remote_addr', 'response_status', 'error', 'created_at',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class DGIICertificationItemInline(admin.TabularInline):
    model = DGIICertificationItem
    extra = 0
    readonly_fields = [
        'ecf_type', 'dgii_group', 'status', 'encf', 'amount',
        'receiver_rnc', 'receiver_name', 'source_sheet', 'source_row',
    ]
    can_delete = False


@admin.register(DGIICertificationPlan)
class DGIICertificationPlanAdmin(admin.ModelAdmin):
    list_display = ['company', 'source_filename', 'total_items', 'imported_by', 'imported_at']
    list_filter = ['company', 'imported_at']
    search_fields = ['source_filename', 'file_sha256', 'company__name']
    readonly_fields = [
        'company', 'status', 'source_filename', 'file_sha256', 'imported_by',
        'imported_at', 'total_items', 'group_counts', 'created_at', 'updated_at',
    ]
    inlines = [DGIICertificationItemInline]

    def has_add_permission(self, request):
        return False


@admin.register(DGIICertificationEvent)
class DGIICertificationEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'company', 'plan', 'item', 'created_by', 'created_at']
    list_filter = ['event_type', 'company', 'created_at']
    search_fields = ['message', 'company__name', 'plan__source_filename']
    readonly_fields = ['company', 'plan', 'item', 'event_type', 'message', 'payload', 'created_by', 'created_at']

    def has_add_permission(self, request):
        return False
