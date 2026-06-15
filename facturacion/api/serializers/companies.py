from rest_framework import serializers

from facturacion.api.validators import normalize_rnc, validate_phone
from facturacion.models import Company, CompanyMembership


class CompanySerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'legal_name', 'rnc', 'email', 'phone', 'address',
            'logo', 'logo_url', 'primary_color', 'is_active', 'role', 'role_label',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_role_label(self, obj):
        membership = self._membership(obj)
        return membership.get_role_display() if membership else None

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if not obj.logo:
            return None
        url = obj.logo.url
        return request.build_absolute_uri(url) if request else url

    def _membership(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        return (
            CompanyMembership.objects
            .filter(user=user, company=obj, is_active=True)
            .first()
        )


class CompanyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'legal_name', 'rnc', 'email', 'phone', 'address',
            'primary_color', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not str(value or '').strip():
            raise serializers.ValidationError('El nombre comercial es obligatorio.')
        return value

    def validate_rnc(self, value):
        rnc = normalize_rnc(value)
        if not rnc:
            return ''
        queryset = Company.objects.filter(rnc=rnc)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe una empresa registrada con este RNC.')
        return rnc

    def validate_phone(self, value):
        return validate_phone(value)


class CompanyMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    role_label = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = CompanyMembership
        fields = [
            'id', 'user_id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_label', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class CompanyMembershipCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=CompanyMembership.ROLE_CHOICES)


class CompanyMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=CompanyMembership.ROLE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)


class CompanySwitchSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
