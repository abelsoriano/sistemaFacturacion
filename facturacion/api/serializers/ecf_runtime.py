from rest_framework import serializers

from facturacion.api.serializers.ecf_config import ECFEventLogSerializer, ECFStatusEventSerializer
from facturacion.models import ElectronicFiscalDocument


def _effective_fiscal_status(document):
    if not document:
        return None
    legacy_status = document.status
    if legacy_status in {'accepted', 'rejected'}:
        return legacy_status
    if legacy_status in {'pending', 'processing', 'submitted'} or document.track_id:
        return 'submitted'
    if legacy_status in {'draft', 'xml_generated', 'signed'}:
        return legacy_status
    if document.signed_xml_content:
        return 'signed'
    if document.xml_content:
        return 'xml_generated'
    return document.fiscal_status or 'draft'


def _effective_job_status(document):
    if not document:
        return None
    if document.status == 'queued':
        return 'queued'
    if document.status in {'error', 'cancelled'}:
        return 'failed'
    return document.job_status or 'idle'


class ElectronicFiscalDocumentSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    fiscal_status = serializers.SerializerMethodField()
    job_status = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    job_status_label = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    can_check_status = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    is_terminal_fiscal = serializers.SerializerMethodField()
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    credit_note_number = serializers.CharField(source='credit_note.credit_note_number', read_only=True)
    issuer_name = serializers.CharField(source='issuer.business_name', read_only=True)
    events = ECFEventLogSerializer(many=True, read_only=True)
    status_events = ECFStatusEventSerializer(many=True, read_only=True)
    xml_available = serializers.SerializerMethodField()
    signed_xml_available = serializers.SerializerMethodField()
    dgii_request_available = serializers.SerializerMethodField()
    dgii_response_available = serializers.SerializerMethodField()

    class Meta:
        model = ElectronicFiscalDocument
        fields = [
            'id', 'company', 'invoice', 'invoice_number', 'issuer', 'issuer_name',
            'credit_note', 'credit_note_number', 'sequence', 'ecf_type', 'encf',
            'status', 'fiscal_status', 'job_status', 'status_label', 'job_status_label',
            'can_retry', 'can_check_status', 'can_submit', 'is_terminal_fiscal',
            'track_id',
            'xml_available', 'signed_xml_available', 'dgii_request_available',
            'dgii_response_available', 'dgii_response', 'last_submitted_at',
            'last_status_checked_at', 'accepted_at', 'rejection_reason',
            'async_task_id', 'idempotency_key', 'submission_attempts',
            'status_check_attempts', 'next_retry_at', 'last_error',
            'created_at', 'updated_at', 'events', 'status_events'
        ]
        read_only_fields = [
            'id', 'company', 'sequence', 'encf', 'status', 'fiscal_status', 'job_status',
            'status_label', 'job_status_label', 'can_retry', 'can_check_status', 'can_submit',
            'is_terminal_fiscal', 'track_id',
            'xml_available', 'signed_xml_available', 'dgii_request_available',
            'dgii_response_available', 'dgii_response', 'last_submitted_at',
            'last_status_checked_at', 'accepted_at', 'rejection_reason',
            'async_task_id', 'idempotency_key', 'submission_attempts',
            'status_check_attempts', 'next_retry_at', 'last_error',
            'created_at', 'updated_at', 'events', 'status_events'
        ]

    def get_status(self, obj):
        return _effective_fiscal_status(obj)

    def get_fiscal_status(self, obj):
        return _effective_fiscal_status(obj)

    def get_job_status(self, obj):
        return _effective_job_status(obj)

    def get_status_label(self, obj):
        labels = {
            'draft': 'Borrador',
            'xml_generated': 'XML generado',
            'signed': 'Firmado',
            'submitted': 'Enviado a DGII',
            'accepted': 'Aceptado',
            'rejected': 'Rechazado',
        }
        return labels.get(_effective_fiscal_status(obj), _effective_fiscal_status(obj) or 'N/D')

    def get_job_status_label(self, obj):
        labels = {
            'idle': 'Inactivo',
            'queued': 'En cola',
            'running': 'Ejecutando',
            'retrying': 'Reintentando',
            'failed': 'Fallido',
        }
        return labels.get(_effective_job_status(obj), _effective_job_status(obj) or 'N/D')

    def get_can_retry(self, obj):
        return bool(not obj.track_id and _effective_fiscal_status(obj) not in {'accepted', 'rejected'})

    def get_can_check_status(self, obj):
        return bool(obj.track_id and _effective_fiscal_status(obj) == 'submitted')

    def get_can_submit(self, obj):
        return bool(not obj.track_id and _effective_fiscal_status(obj) == 'signed')

    def get_is_terminal_fiscal(self, obj):
        return _effective_fiscal_status(obj) in {'accepted', 'rejected'}

    def get_xml_available(self, obj):
        return bool(obj.xml_content)

    def get_signed_xml_available(self, obj):
        return bool(obj.signed_xml_content)

    def get_dgii_request_available(self, obj):
        return bool(obj.dgii_request_xml)

    def get_dgii_response_available(self, obj):
        return bool(obj.dgii_response_xml)
