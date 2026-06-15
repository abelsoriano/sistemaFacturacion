from rest_framework import serializers

from facturacion.api.serializers.ecf_runtime import _effective_fiscal_status, _effective_job_status
from facturacion.models import CreditNote, CreditNoteDetail


class CreditNoteDetailSerializer(serializers.ModelSerializer):
    origin_detail_id = serializers.IntegerField(source='origin_detail.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = CreditNoteDetail
        fields = ['id', 'origin_detail', 'origin_detail_id', 'product', 'product_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'origin_detail_id', 'product', 'product_name', 'price', 'subtotal']


class CreditNoteSerializer(serializers.ModelSerializer):
    details = CreditNoteDetailSerializer(many=True, read_only=True)
    origin_invoice_number = serializers.CharField(source='origin_invoice.invoice_number', read_only=True)
    origin_client_name = serializers.SerializerMethodField()
    origin_encf = serializers.CharField(source='origin_invoice.electronic_document.encf', read_only=True)
    electronic_document_id = serializers.IntegerField(source='electronic_document.id', read_only=True)
    encf = serializers.CharField(source='electronic_document.encf', read_only=True)
    fiscal_status = serializers.SerializerMethodField()
    job_status = serializers.SerializerMethodField()
    track_id = serializers.CharField(source='electronic_document.track_id', read_only=True)
    last_error = serializers.CharField(source='electronic_document.last_error', read_only=True)
    ecf_status = serializers.SerializerMethodField()
    ecf_job_status = serializers.SerializerMethodField()
    dgii_rejection_reason = serializers.CharField(source='electronic_document.rejection_reason', read_only=True)
    can_retry = serializers.SerializerMethodField()
    can_check_status = serializers.SerializerMethodField()
    can_reconcile_inventory = serializers.SerializerMethodField()
    can_mark_reviewed = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = CreditNote
        fields = [
            'id', 'company', 'credit_note_number', 'origin_invoice', 'origin_invoice_number',
            'origin_client_name', 'origin_encf', 'reversal_type', 'reason',
            'subtotal', 'tax', 'discount', 'total', 'status',
            'fiscal_resolution_status', 'inventory_reconciliation_status',
            'inventory_restored_at', 'inventory_reconciled_at', 'inventory_compensated_at',
            'requires_manual_review', 'manual_reviewed_at', 'created_by', 'created_by_username',
            'created_at', 'updated_at', 'electronic_document_id', 'encf',
            'fiscal_status', 'job_status', 'track_id', 'last_error',
            'ecf_status', 'ecf_job_status',
            'dgii_rejection_reason', 'can_retry', 'can_check_status', 'can_reconcile_inventory',
            'can_mark_reviewed', 'details'
        ]
        read_only_fields = [
            'id', 'company', 'credit_note_number', 'reversal_type', 'subtotal', 'tax',
            'discount', 'total', 'status', 'fiscal_resolution_status',
            'inventory_reconciliation_status', 'inventory_restored_at', 'inventory_reconciled_at',
            'inventory_compensated_at', 'requires_manual_review', 'manual_reviewed_at',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
            'electronic_document_id', 'encf', 'fiscal_status', 'job_status',
            'track_id', 'last_error', 'ecf_status', 'ecf_job_status',
            'dgii_rejection_reason', 'can_retry', 'can_check_status',
            'can_reconcile_inventory', 'can_mark_reviewed', 'details'
        ]

    def get_origin_client_name(self, obj):
        client = getattr(obj.origin_invoice, 'client', None)
        return getattr(client, 'name', None) or 'Consumidor Final'

    def get_fiscal_status(self, obj):
        return _effective_fiscal_status(getattr(obj, 'electronic_document', None))

    def get_job_status(self, obj):
        return _effective_job_status(getattr(obj, 'electronic_document', None))

    def get_ecf_status(self, obj):
        return self.get_fiscal_status(obj)

    def get_ecf_job_status(self, obj):
        return self.get_job_status(obj)

    def get_can_retry(self, obj):
        document = getattr(obj, 'electronic_document', None)
        return bool(document and document.job_status == 'failed' and document.fiscal_status not in {'accepted', 'rejected'})

    def get_can_check_status(self, obj):
        document = getattr(obj, 'electronic_document', None)
        return bool(document and document.track_id and document.fiscal_status == 'submitted')

    def get_can_reconcile_inventory(self, obj):
        return bool(obj.inventory_reconciliation_status == 'compensation_required' and not obj.inventory_compensated_at)

    def get_can_mark_reviewed(self, obj):
        return bool(obj.requires_manual_review and not obj.manual_reviewed_at)
