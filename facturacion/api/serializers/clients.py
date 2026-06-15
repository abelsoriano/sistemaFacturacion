from rest_framework import serializers
from django.db.models import Sum

from facturacion.api.permissions import can_view_financial_totals
from facturacion.api.validators import normalize_rnc, validate_phone
from facturacion.models import Client


class ClientSerializer(serializers.ModelSerializer):
    total_invoices = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'company', 'name', 'email', 'phone', 'address', 'ruc_ci',
            'client_type', 'total_invoices', 'total_spent',
        ]
        read_only_fields = ['company']
        validators = []

    def get_total_invoices(self, obj):
        return obj.invoices.filter(status='paid').count()

    def get_total_spent(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not can_view_financial_totals(user):
            return None

        return obj.invoices.filter(status='paid').aggregate(
            total=Sum('total')
        )['total'] or 0

    def validate_ruc_ci(self, value):
        return normalize_rnc(value, label='RNC/Cedula')

    def validate_phone(self, value):
        return validate_phone(value)
