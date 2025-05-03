# forms.py
from django import forms
from .models import Invoice, InvoiceDetail

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client', 'status']

class InvoiceDetailForm(forms.ModelForm):
    class Meta:
        model = InvoiceDetail
        fields = ['product', 'quantity', 'price']
