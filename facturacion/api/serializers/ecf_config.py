from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.api.validators import normalize_rnc, validate_phone
from facturacion.models import ECFCertificate, ECFEventLog, ECFIssuerConfig, ECFSequence, ECFStatusEvent


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
