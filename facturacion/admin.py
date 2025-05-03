from django.contrib import admin
from .models import *

admin.site.register(Category)
admin.site.register(Product)
# admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(InvoiceDetail)
