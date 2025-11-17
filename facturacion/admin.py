from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Product)
# admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(InvoiceDetail)


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