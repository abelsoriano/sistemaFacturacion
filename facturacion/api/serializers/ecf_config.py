from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.api.validators import normalize_rnc, validate_phone
from facturacion.models import (
    DGIICertificationDocument,
    DGIICertificationCommercialApprovalEvent,
    DGIICertificationCommercialApprovalItem,
    DGIICertificationCommercialApprovalPlan,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
    ECFCertificate,
    ECFEventLog,
    ECFIssuerConfig,
    ECFSequence,
    ECFStatusEvent,
)


class DGIICertificationDocumentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    signed_xml_available = serializers.SerializerMethodField()
    needs_resubmit = serializers.SerializerMethodField()

    class Meta:
        model = DGIICertificationDocument
        fields = [
            'id', 'company', 'plan', 'item', 'ecf_type', 'encf',
            'status', 'status_label', 'xml_hash', 'generated_at',
            'generation_error', 'signed_xml_hash', 'signed_at',
            'signing_error', 'dgii_track_id', 'dgii_status',
            'dgii_response_code', 'dgii_response_message', 'submitted_at',
            'accepted_at', 'rejected_at', 'accepted_stale', 'stale_reason',
            'stale_at', 'needs_resubmit', 'submit_error', 'signed_xml_available',
            'submission_outcome',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_signed_xml_available(self, obj):
        return bool(obj.signed_xml_path)

    def get_needs_resubmit(self, obj):
        return bool(obj.accepted_stale)


class DGIICertificationItemSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    ecf_type_label = serializers.CharField(source='get_ecf_type_display', read_only=True)
    certification_document = DGIICertificationDocumentSerializer(read_only=True)

    class Meta:
        model = DGIICertificationItem
        fields = [
            'id', 'plan', 'company', 'ecf_type', 'ecf_type_label', 'dgii_group',
            'status', 'status_label', 'encf', 'document_type', 'amount',
            'receiver_rnc', 'receiver_name', 'observations', 'source_sheet',
            'source_row', 'raw_data', 'generated_xml_path', 'generated_xml_hash',
            'generated_at', 'generation_error', 'created_at', 'updated_at',
            'certification_document',
        ]
        read_only_fields = fields


class DGIICertificationEventSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = DGIICertificationEvent
        fields = [
            'id', 'company', 'plan', 'item', 'event_type', 'message',
            'payload', 'created_by', 'created_by_username', 'created_at',
        ]
        read_only_fields = fields


class DGIICertificationPlanSerializer(serializers.ModelSerializer):
    items = DGIICertificationItemSerializer(many=True, read_only=True)
    events = DGIICertificationEventSerializer(many=True, read_only=True)
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True)

    class Meta:
        model = DGIICertificationPlan
        fields = [
            'id', 'company', 'status', 'source_filename', 'file_sha256',
            'imported_by', 'imported_by_username', 'imported_at',
            'total_items', 'group_counts', 'items', 'events',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class DGIICertificationCommercialApprovalItemSerializer(serializers.ModelSerializer):
    dgii_status_label = serializers.CharField(source='get_dgii_status_display', read_only=True)
    source_approval_status_label = serializers.CharField(source='get_source_approval_status_display', read_only=True)
    submission_status_label = serializers.CharField(source='get_submission_status_display', read_only=True)
    match_status_label = serializers.CharField(source='get_match_status_display', read_only=True)

    class Meta:
        model = DGIICertificationCommercialApprovalItem
        fields = [
            'id', 'plan', 'company', 'version', 'issuer_rnc', 'encf',
            'issue_date', 'total_amount', 'buyer_rnc', 'dgii_status',
            'dgii_status_label', 'source_approval_status',
            'source_approval_status_label', 'submission_status',
            'submission_status_label', 'approval_receiver_rnc',
            'rejection_reason', 'commercial_approval_at', 'raw_data',
            'generated_xml_path', 'generated_at', 'signed_xml_path',
            'signed_xml_hash', 'signed_at', 'signature_metadata',
            'dgii_track_id', 'dgii_response_code', 'dgii_response_message',
            'dgii_response', 'accepted_at', 'rejected_at', 'submission_error',
            'matched_document_type', 'matched_document_id', 'match_status',
            'match_status_label', 'match_observations', 'source_row',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class DGIICertificationCommercialApprovalEventSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = DGIICertificationCommercialApprovalEvent
        fields = [
            'id', 'company', 'plan', 'item', 'event_type', 'message',
            'payload', 'created_by', 'created_by_username', 'created_at',
        ]
        read_only_fields = fields


class DGIICertificationCommercialApprovalPlanSerializer(serializers.ModelSerializer):
    items = DGIICertificationCommercialApprovalItemSerializer(many=True, read_only=True)
    events = DGIICertificationCommercialApprovalEventSerializer(many=True, read_only=True)
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True)
    is_step_complete = serializers.SerializerMethodField()
    submission_summary = serializers.SerializerMethodField()

    class Meta:
        model = DGIICertificationCommercialApprovalPlan
        fields = [
            'id', 'company', 'source_filename', 'file_sha256', 'imported_at',
            'imported_by', 'imported_by_username', 'status', 'total_records',
            'approved_count', 'rejected_count', 'pending_count', 'raw_summary',
            'is_step_complete', 'submission_summary', 'items', 'events',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_is_step_complete(self, obj):
        summary = self.get_submission_summary(obj)
        return obj.total_records > 0 and summary['accepted_by_dgii'] == obj.total_records

    def get_submission_summary(self, obj):
        items = list(obj.items.all())
        return {
            'total': len(items),
            'source_approved': sum(1 for item in items if item.source_approval_status == DGIICertificationCommercialApprovalItem.SOURCE_APPROVED),
            'source_rejected': sum(1 for item in items if item.source_approval_status == DGIICertificationCommercialApprovalItem.SOURCE_REJECTED),
            'source_pending': sum(1 for item in items if item.source_approval_status == DGIICertificationCommercialApprovalItem.SOURCE_PENDING),
            'pending_submission': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_PENDING),
            'generated': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_GENERATED),
            'signed': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_SIGNED),
            'submitted': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_SUBMITTED),
            'accepted_by_dgii': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_ACCEPTED),
            'rejected_by_dgii': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_REJECTED),
            'failed': sum(1 for item in items if item.submission_status == DGIICertificationCommercialApprovalItem.SUBMISSION_FAILED),
        }


class ECFCertificateSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = ECFCertificate
        fields = [
            'id', 'company', 'issuer', 'environment', 'status',
            'storage_backend', 'certificate_reference', 'subject',
            'issuer_name', 'serial_number', 'fingerprint',
            'not_valid_before', 'not_valid_after', 'rnc_detected',
            'rnc_match_status', 'uploaded_by', 'uploaded_by_username',
            'uploaded_at', 'activated_at', 'deactivated_at',
            'is_active', 'previous_certificate', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ECFIssuerConfigSerializer(serializers.ModelSerializer):
    certificate_configured = serializers.SerializerMethodField()

    class Meta:
        model = ECFIssuerConfig
        fields = [
            'id', 'company', 'business_name', 'trade_name', 'rnc', 'address',
            'municipality', 'province', 'phone', 'email', 'environment',
            'default_ecf_type', 'auto_ecf_rules_enabled', 'certificate_configured',
            'certificate_path', 'certificate_password', 'certificate_subject',
            'certificate_issuer', 'certificate_serial_number', 'certificate_fingerprint',
            'certificate_not_valid_before', 'certificate_not_valid_after',
            'certificate_status', 'certificate_status_updated_at',
            'certificate_rnc_detected', 'certificate_rnc_match_status',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'company', 'certificate_subject', 'certificate_issuer',
            'certificate_serial_number', 'certificate_fingerprint',
            'certificate_not_valid_before', 'certificate_not_valid_after',
            'certificate_status', 'certificate_status_updated_at',
            'certificate_rnc_detected', 'certificate_rnc_match_status',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'certificate_password': {'write_only': True, 'required': False},
            'certificate_path': {'write_only': True, 'required': False},
        }

    def get_certificate_configured(self, obj):
        return bool(obj.certificate_path or obj.certificate_password)

    def validate_rnc(self, value):
        return normalize_rnc(value, required=True)

    def validate_phone(self, value):
        return validate_phone(value)


class ECFSequenceSerializer(serializers.ModelSerializer):
    issuer_name = serializers.CharField(source='issuer.business_name', read_only=True)
    remaining = serializers.IntegerField(read_only=True)
    current_encf_preview = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and 'issuer' in self.fields:
            company = get_current_company(request)
            if company:
                self.fields['issuer'].queryset = ECFIssuerConfig.objects.filter(company=company, is_active=True)

    class Meta:
        model = ECFSequence
        fields = [
            'id', 'company', 'issuer', 'issuer_name', 'ecf_type', 'start_number',
            'end_number', 'next_number', 'remaining', 'current_encf_preview',
            'authorization_date', 'expiration_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'company', 'remaining', 'current_encf_preview', 'created_at', 'updated_at']

    def get_current_encf_preview(self, obj):
        if obj.next_number > obj.end_number:
            return None
        return obj.format_encf(obj.next_number)


class ECFEventLogSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ECFEventLog
        fields = [
            'id', 'electronic_document', 'event_type', 'message',
            'payload', 'created_by', 'created_by_username', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_username', 'created_at']


class ECFStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ECFStatusEvent
        fields = [
            'id', 'document', 'previous_fiscal_status', 'new_fiscal_status',
            'previous_job_status', 'new_job_status', 'source', 'reason',
            'task_id', 'created_at',
        ]
        read_only_fields = fields
