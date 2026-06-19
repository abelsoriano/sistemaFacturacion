from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import get_current_company, get_current_membership
from facturacion.api.permissions import model_permissions
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_config import (
    ECFCertificateSerializer,
    ECFEventLogSerializer,
    ECFIssuerConfigSerializer,
    ECFSequenceSerializer,
)
from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.certificates.metadata import ECFCertificateMetadataService
from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.signer.xml_signer import ECFXMLSigner
from facturacion.models import CompanyMembership, ECFCertificate, ECFEventLog, ECFIssuerConfig, ECFSequence
from facturacion.permissions import HasRequiredPermissions


MANAGER_ROLES = {CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN}
CERTIFICATION_XML_MAX_BYTES = 2 * 1024 * 1024


class ECFIssuerConfigViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ECFIssuerConfig.objects.all()
    serializer_class = ECFIssuerConfigSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('ecfissuerconfig')
    action_required_permissions = {'upload_certificate': [], 'certificates': [], 'sign_certification_xml': []}
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['business_name', 'trade_name', 'rnc']
    ordering_fields = ['business_name', 'rnc', 'created_at']
    ordering = ['-is_active', 'business_name']

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._refresh_certificate_metadata_if_needed(serializer.instance, serializer.validated_data)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._refresh_certificate_metadata_if_needed(serializer.instance, serializer.validated_data)

    def _refresh_certificate_metadata_if_needed(self, issuer, validated_data):
        if {'certificate_path', 'certificate_password'} & set(validated_data.keys()):
            ECFCertificateMetadataService().refresh(issuer)
            issuer.refresh_from_db()

    @action(
        detail=True,
        methods=['post'],
        url_path='certificate',
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_certificate(self, request, pk=None):
        """Carga transitoria de certificado DGII.

        Implementacion temporal: el password permanece en ECFIssuerConfig.
        Una fase futura debe migrar esto a ECFCertificate + secret manager/KMS.
        """
        issuer = self.get_object()
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None or issuer.company_id != company.id:
            return Response(
                {'detail': 'El emisor fiscal no pertenece a la empresa activa.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede cargar certificados DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get('certificate')
        password = request.data.get('password', '')
        if not uploaded_file:
            return Response({'certificate': ['Debe cargar un archivo .p12.']}, status=status.HTTP_400_BAD_REQUEST)
        if Path(uploaded_file.name).suffix.lower() != '.p12':
            return Response({'certificate': ['El certificado debe ser un archivo .p12.']}, status=status.HTTP_400_BAD_REQUEST)

        filename = f"{uuid4().hex}.p12"
        relative_path = f"ecf_certificates/company_{company.id}/issuer_{issuer.id}/{filename}"
        saved_path = default_storage.save(relative_path, uploaded_file)
        certificate_path = str(Path(settings.MEDIA_ROOT) / saved_path)

        try:
            with transaction.atomic():
                issuer.certificate_path = certificate_path
                issuer.certificate_password = password
                issuer.save(update_fields=['certificate_path', 'certificate_password', 'updated_at'])
                ECFCertificateMetadataService().refresh(issuer)
                issuer.refresh_from_db()

                now = timezone.now()
                previous_certificate = (
                    ECFCertificate.objects
                    .select_for_update()
                    .filter(
                        company=company,
                        issuer=issuer,
                        environment=issuer.environment,
                        is_active=True,
                    )
                    .order_by('-activated_at', '-uploaded_at')
                    .first()
                )
                ECFCertificate.objects.filter(
                    company=company,
                    issuer=issuer,
                    environment=issuer.environment,
                    is_active=True,
                ).update(is_active=False, deactivated_at=now, updated_at=now)
                ECFCertificate.objects.create(
                    company=company,
                    issuer=issuer,
                    environment=issuer.environment,
                    status=issuer.certificate_status,
                    storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
                    certificate_reference=certificate_path,
                    password_secret_reference=password,
                    subject=issuer.certificate_subject,
                    issuer_name=issuer.certificate_issuer,
                    serial_number=issuer.certificate_serial_number,
                    fingerprint=issuer.certificate_fingerprint,
                    not_valid_before=issuer.certificate_not_valid_before,
                    not_valid_after=issuer.certificate_not_valid_after,
                    rnc_detected=issuer.certificate_rnc_detected,
                    rnc_match_status=issuer.certificate_rnc_match_status,
                    uploaded_by=request.user,
                    uploaded_at=now,
                    activated_at=now,
                    is_active=True,
                    previous_certificate=previous_certificate,
                    notes='Carga operativa desde /company. Referencias legacy temporales.',
                )
        except (DjangoValidationError, IntegrityError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(issuer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='certificates')
    def certificates(self, request, pk=None):
        issuer = self.get_object()
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None or issuer.company_id != company.id:
            return Response(
                {'detail': 'El emisor fiscal no pertenece a la empresa activa.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede ver certificados DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = (
            ECFCertificate.objects
            .filter(company=company, issuer=issuer)
            .select_related('uploaded_by', 'issuer')
            .order_by('-is_active', '-uploaded_at')
        )
        serializer = ECFCertificateSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        url_path='sign-certification-xml',
        parser_classes=[MultiPartParser, FormParser],
    )
    def sign_certification_xml(self, request, pk=None):
        """Firma XML de postulacion DGII sin crear documentos e-CF.

        Este endpoint es operativo para certificacion/postulacion y no toca
        ElectronicFiscalDocument, secuencias ni colas del runtime fiscal.
        """
        issuer = self.get_object()
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None or issuer.company_id != company.id:
            return Response(
                {'detail': 'El emisor fiscal no pertenece a la empresa activa.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede firmar XML de postulacion DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get('xml')
        if not uploaded_file:
            return Response({'xml': ['Debe cargar un archivo XML de postulacion.']}, status=status.HTTP_400_BAD_REQUEST)
        if Path(uploaded_file.name).suffix.lower() != '.xml':
            return Response({'xml': ['El archivo de postulacion debe tener extension .xml.']}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded_file.size > CERTIFICATION_XML_MAX_BYTES:
            return Response({'xml': ['El XML de postulacion no puede exceder 2 MB.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            xml_content = uploaded_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'xml': ['El XML debe estar codificado en UTF-8.']}, status=status.HTTP_400_BAD_REQUEST)

        policy_result = ECFCertificateSigningPolicy().evaluate(issuer)
        issuer.refresh_from_db()
        if policy_result.blocked:
            return Response(
                {
                    'detail': policy_result.reason,
                    'code': policy_result.code,
                    'warnings': policy_result.warnings,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        if not certificate_path:
            return Response(
                {'detail': 'El emisor fiscal no tiene certificado DGII disponible para firmar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            certificate = PKCS12CertificateLoader().load(certificate_path, certificate_password)
            signed_xml = ECFXMLSigner().sign(xml_content, certificate)
        except ECFError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        original_stem = Path(uploaded_file.name).stem or 'postulacion-dgii'
        return Response(
            {
                'issuer_id': issuer.id,
                'filename': f'{original_stem}-firmado.xml',
                'signed_xml': signed_xml,
                'warnings': policy_result.warnings,
                'policy_code': policy_result.code,
                'certificate_status': issuer.certificate_status,
                'certificate_rnc_match_status': issuer.certificate_rnc_match_status,
            },
            status=status.HTTP_200_OK,
        )


class ECFSequenceViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ECFSequence.objects.select_related('issuer').all()
    serializer_class = ECFSequenceSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('ecfsequence')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['issuer', 'ecf_type', 'is_active']
    ordering_fields = ['ecf_type', 'next_number', 'expiration_date']
    ordering = ['ecf_type', 'next_number']


class ECFEventLogViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ECFEventLog.objects.select_related('electronic_document', 'created_by').all()
    serializer_class = ECFEventLogSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_ecfeventlog']}
    company_field = 'electronic_document__company'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['electronic_document', 'event_type']
    ordering = ['-created_at']
