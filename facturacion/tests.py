"""Tests for the facturacion app."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, force_authenticate

from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.certificates.metadata import ECFCertificateMetadataService, extract_rnc_candidates_from_certificate
from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.services.dgii_status import DGIIStatusService
from facturacion.ecf.services.dgii_submission import DGIISubmissionService
from facturacion.ecf.services.document_factory import ECFDocumentFactoryService
from facturacion.ecf.services.job_reconciliation import ECFJobStatusReconciliationService
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.services.signing import ECFSigningService
from facturacion.ecf.services.xml_generation import ECFXMLGenerationService
from facturacion.ecf.queues.ecf import enqueue_generate_xml, enqueue_submission_pipeline
from facturacion.ecf.rest.auth import DGIIRESTAuthClient
from facturacion.ecf.rest.clients import DGIIRESTClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironment, DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.responses import DGIIRESTToken
from facturacion.ecf.signer.xml_signer import ECFXMLSigner
from facturacion.ecf.soap.auth import DGIIBearerToken
from facturacion.ecf.soap.clients.base import SOAPCallResult
from facturacion.ecf.soap.environments import DGIISOAPEnvironment
from facturacion.ecf.soap.parsers.dgii import DGIISOAPResponseParser
from facturacion.ecf.validators.signature import ECFSignatureValidator
from facturacion.ecf.validators.xsd import ECFXSDValidator
from facturacion.models import (
    AbonoServicio,
    Asset,
    AssetCategory,
    Category,
    Client,
    Company,
    CompanyMembership,
    CreditNote,
    ECFCertificate,
    ECFIssuerConfig,
    ECFEventLog,
    ECFStatusEvent,
    ECFSequence,
    ElectronicFiscalDocument,
    Invoice,
    InvoiceDetail,
    NumberSequence,
    Product,
    Quotation,
    Sale,
    SaleDetail,
    ServicioManoObra,
)
from facturacion.api.serializers.ecf_runtime import ElectronicFiscalDocumentSerializer
from facturacion.api.serializers.clients import ClientSerializer
from facturacion.api.serializers.sales_legacy import SaleListSerializer, SaleSerializer
from facturacion.api.views.assets import AssetViewSet
from facturacion.api.views.clients import ClientViewSet
from facturacion.api.views.credit_notes import CreditNoteViewSet
from facturacion.api.views.companies import CompanyViewSet
from facturacion.api.views.ecf_runtime import ElectronicFiscalDocumentViewSet
from facturacion.api.views.ecf_config import ECFEventLogViewSet, ECFIssuerConfigViewSet, ECFSequenceViewSet
from facturacion.api.views.inventory import CategoryListCreateView, ProductListCreateView
from facturacion.api.views.inventory_utils import (
    GenerateBarcodeImageView,
    GenerateZPLLabelView,
    PrintLabelDirectView,
    SearchByBarcodeView,
    generate_low_stock_pdf,
)
from facturacion.api.views.invoices import InvoiceViewSet
from facturacion.api.views.operations import AbonoServicioViewSet, ServicioManoObraViewSet
from facturacion.api.views.quotations import QuotationViewSet
from facturacion.api.views.reports import DashboardView
from facturacion.api.views.sales_legacy import SaleCreateView, SaleListView, SalesUpdateDeleteView
from facturacion.api.views.auth import GroupViewSet, PermissionListView, RegisterView, UserViewSet
from facturacion.ecf.tasks.dgii import check_status, submit_dgii
from facturacion.ecf.tasks.signing import sign_xml as sign_xml_task
from facturacion.ecf.tasks.xml import generate_xml as generate_xml_task
from facturacion.api.company_context import (
    get_current_company,
    get_current_membership,
    require_current_company,
    user_has_company_access,
)
from facturacion.api.middleware import CompanyContextMiddleware
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.services.credit_note_reconciliation import CreditNoteReconciliationService
from facturacion.services.credit_notes import CreditNoteService
from facturacion.services.invoicing import InvoiceCreationService
from facturacion.services.onboarding import DEFAULT_OWNER_GROUP_NAME, DEFAULT_OWNER_PERMISSION_CODENAMES
from facturacion.services.quotations import QuotationService


class ECFSigningTests(SimpleTestCase):
    """Validate certificate loading and XMLDSig signing behavior."""

    password = "secret-pass"

    def test_load_valid_pkcs12_certificate(self):
        with TemporaryDirectory() as temp_dir:
            p12_path = self._write_pkcs12(Path(temp_dir) / "cert.p12")

            loaded = PKCS12CertificateLoader().load(p12_path, self.password)

            self.assertIn("CN=DGII Test Certificate", loaded.subject)
            self.assertTrue(loaded.private_key_pem.startswith(b"-----BEGIN PRIVATE KEY-----"))
            self.assertTrue(loaded.certificate_pem.startswith(b"-----BEGIN CERTIFICATE-----"))

    def test_sign_xml_replaces_placeholder_and_validates_signature(self):
        with TemporaryDirectory() as temp_dir:
            p12_path = self._write_pkcs12(Path(temp_dir) / "cert.p12")
            loaded = PKCS12CertificateLoader().load(p12_path, self.password)
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<ECF><FechaHoraFirma>27-05-2026 10:00:00</FechaHoraFirma>'
                '<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
                '<!-- Placeholder --></ds:Signature></ECF>'
            )

            signed_xml = ECFXMLSigner().sign(xml, loaded)

            self.assertIn("<ds:Signature", signed_xml)
            self.assertNotIn("Placeholder", signed_xml)
            ECFSignatureValidator().validate(signed_xml, loaded)

    def test_expired_certificate_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            p12_path = self._write_pkcs12(Path(temp_dir) / "expired.p12", expired=True)

            with self.assertRaises(ECFValidationError):
                PKCS12CertificateLoader().load(p12_path, self.password)

    def _write_pkcs12(self, path: Path, expired: bool = False) -> Path:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "DO"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DGII Test"),
                x509.NameAttribute(NameOID.COMMON_NAME, "DGII Test Certificate"),
            ]
        )

        now = datetime.now(timezone.utc)
        not_before = now - timedelta(days=30)
        not_after = now - timedelta(days=1) if expired else now + timedelta(days=365)

        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .sign(key, hashes.SHA256())
        )

        p12 = pkcs12.serialize_key_and_certificates(
            name=b"dgii-test",
            key=key,
            cert=certificate,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(self.password.encode("utf-8")),
        )
        path.write_bytes(p12)
        return path


class DGIISOAPParserTests(SimpleTestCase):
    """Validate DGII SOAP response normalization."""

    def test_parse_submission_response_extracts_track_id(self):
        response = {"trackId": "abc123", "estado": "Recibido", "codigo": 1}

        parsed = DGIISOAPResponseParser().parse_submission(response)

        self.assertEqual(parsed.track_id, "abc123")
        self.assertEqual(parsed.status, "Recibido")
        self.assertEqual(parsed.code, 1)

    def test_parse_status_response_normalizes_processing(self):
        response = {"trackId": "abc123", "estado": "En Proceso", "codigo": 3}

        parsed = DGIISOAPResponseParser().parse_status(response)

        self.assertEqual(parsed.normalized_status, "processing")

    def test_parse_xml_status_response_normalizes_rejected(self):
        response = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<RespuestaConsultaTrackId><trackId>abc123</trackId>"
            "<codigo>2</codigo><estado>Rechazado</estado>"
            "<mensajes><valor>Firma invalida</valor><codigo>99</codigo></mensajes>"
            "</RespuestaConsultaTrackId>"
        )

        parsed = DGIISOAPResponseParser().parse_status(response)

        self.assertEqual(parsed.normalized_status, "rejected")
        self.assertEqual(parsed.messages[0]["valor"], "Firma invalida")


class DGIIRESTClientTests(TestCase):
    """Validate DGII REST client scaffolding without network calls."""

    @override_settings(
        ECF_DGII_ENVIRONMENT="testing",
        ECF_DGII_REST_BASE_URLS={
            "testing": {
                "auth": "https://dgii.test/auth/",
                "reception": "https://dgii.test/recepcion/",
                "status": "https://dgii.test/estado/",
                "trackids": "https://dgii.test/trackids/",
            }
        },
        ECF_DGII_TIMEOUT=45,
        ECF_DGII_RETRIES=2,
        ECF_DGII_RETRY_BACKOFF=1,
        ECF_DGII_VERIFY_TLS=True,
    )
    def test_rest_environment_resolver_reads_configured_urls(self):
        environment = DGIIRESTEnvironmentResolver().resolve()

        self.assertEqual(environment.name, "testing")
        self.assertEqual(environment.auth_base_url, "https://dgii.test/auth")
        self.assertEqual(environment.reception_base_url, "https://dgii.test/recepcion")
        self.assertEqual(environment.status_base_url, "https://dgii.test/estado")
        self.assertEqual(environment.trackids_base_url, "https://dgii.test/trackids")
        self.assertEqual(environment.timeout, 45)
        self.assertEqual(environment.retries, 2)

    def test_auth_client_signs_seed_and_caches_token(self):
        from django.core.cache import cache

        cache.clear()
        session = FakeRESTSession([
            FakeRESTResponse({"semilla": "<Semilla><Valor>abc</Valor></Semilla>"}),
            FakeRESTResponse({"token": "token-001", "expiraEn": 600}),
        ])
        auth_client = DGIIRESTAuthClient(
            environment=self._environment(),
            certificate_loader=FakeCertificateLoader(),
            signer=FakeSeedSigner(),
            session=session,
        )

        first = auth_client.get_token("cert.p12", "secret", issuer_rnc="101010101")
        second = auth_client.get_token("cert.p12", "secret", issuer_rnc="101010101")

        self.assertEqual(first.value, "token-001")
        self.assertEqual(second.value, "token-001")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(session.calls[1]["method"], "POST")
        self.assertIn("semilla_firmada.xml", session.calls[1]["files"]["xml"])

    def test_rest_client_submits_signed_xml_with_bearer_token(self):
        session = FakeRESTSession([FakeRESTResponse({"trackId": "track-rest", "estado": "Recibido"})])
        client = DGIIRESTClient(
            environment=self._environment(),
            auth_client=FakeRESTAuthClient(),
            session=session,
        )

        result = client.submit_ecf(
            signed_xml_content="<ECF>firmado</ECF>",
            encf="E310000000001",
            issuer_rnc="101010101",
            certificate_path="cert.p12",
            certificate_password="secret",
        )

        self.assertEqual(result.result["trackId"], "track-rest")
        self.assertEqual(result.request_xml, "<ECF>firmado</ECF>")
        self.assertEqual(session.calls[0]["method"], "POST")
        self.assertEqual(session.calls[0]["headers"]["Authorization"], "Bearer token-rest")
        self.assertIn("/api/Recepcion/ECF", session.calls[0]["url"])

    def test_rest_client_queries_status_by_track_id(self):
        session = FakeRESTSession([FakeRESTResponse({"trackId": "track-rest", "estado": "Aceptado"})])
        client = DGIIRESTClient(
            environment=self._environment(),
            auth_client=FakeRESTAuthClient(),
            session=session,
        )

        result = client.query_status(
            track_id="track-rest",
            certificate_path="cert.p12",
            certificate_password="secret",
            issuer_rnc="101010101",
        )

        self.assertEqual(result.result["estado"], "Aceptado")
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(session.calls[0]["params"]["trackId"], "track-rest")

    @override_settings(
        DEBUG=False,
        ECF_DGII_ENVIRONMENT="production",
        ECF_CERTIFICATE_PATH="global-cert.p12",
        ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK=True,
        ECF_ALLOW_DEV_SELF_SIGNED_CERT=False,
    )
    def test_certificate_resolver_blocks_global_fallback_in_production(self):
        issuer = self._manual_issuer()

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)

        self.assertIsNone(certificate_path)
        self.assertIsNone(certificate_password)

    @override_settings(
        DEBUG=True,
        ECF_DGII_ENVIRONMENT="testing",
        ECF_CERTIFICATE_PATH="global-cert.p12",
        ECF_CERTIFICATE_PASSWORD="global-pass",
        ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK=True,
        ECF_ALLOW_DEV_SELF_SIGNED_CERT=False,
    )
    def test_certificate_resolver_allows_explicit_global_fallback_in_debug_testing(self):
        issuer = self._manual_issuer()

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)

        self.assertEqual(certificate_path, "global-cert.p12")
        self.assertEqual(certificate_password, "global-pass")

    def test_certificate_resolver_prefers_active_ecf_certificate(self):
        issuer = self._manual_issuer(certificate_path="legacy-cert.p12")
        issuer.certificate_password = "legacy-pass"
        issuer.save(update_fields=["certificate_password", "updated_at"])
        ECFCertificate.objects.create(
            company=issuer.company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="active-cert.p12",
            password_secret_reference="active-pass",
            fingerprint="resolver-active-fingerprint",
            is_active=True,
        )

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)

        self.assertEqual(certificate_path, "active-cert.p12")
        self.assertEqual(certificate_password, "active-pass")

    def test_certificate_resolver_falls_back_to_legacy_when_no_active_certificate(self):
        issuer = self._manual_issuer(certificate_path="legacy-only.p12")
        issuer.certificate_password = "legacy-only-pass"
        issuer.save(update_fields=["certificate_password", "updated_at"])

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)

        self.assertEqual(certificate_path, "legacy-only.p12")
        self.assertEqual(certificate_password, "legacy-only-pass")

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production", ECF_ALLOW_LEGACY_CERTIFICATE_FALLBACK=False)
    def test_certificate_resolver_can_block_legacy_fallback_in_production(self):
        issuer = self._manual_issuer(certificate_path="legacy-prod.p12")

        certificate_path, certificate_password = resolve_certificate_credentials(issuer)

        self.assertIsNone(certificate_path)
        self.assertIsNone(certificate_password)

    @override_settings(
        ECF_DGII_ENVIRONMENT="testing",
        ECF_DGII_REST_BASE_URLS={
            "testing": {
                "auth": "https://dgii.test/auth",
                "reception": "https://dgii.test/recepcion",
                "status": "https://dgii.test/estado",
                "trackids": "https://dgii.test/trackids",
            }
        },
    )
    @patch("facturacion.management.commands.dgii_rest_check_trackid.DGIIRESTClient")
    def test_check_trackid_command_uses_rest_client_without_state_changes(self, client_class):
        client_class.return_value = FakeManualRESTClient()
        issuer = self._manual_issuer(certificate_path="cert.p12")
        output = StringIO()

        call_command(
            "dgii_rest_check_trackid",
            track_id="track-manual",
            company_id=issuer.company_id,
            issuer_id=issuer.id,
            stdout=output,
        )

        self.assertIn("Consulta DGII REST completada", output.getvalue())
        client_class.return_value.query_status.assert_called_once()

    @override_settings(
        ECF_DGII_ENVIRONMENT="testing",
        ECF_DGII_REST_BASE_URLS={
            "testing": {
                "auth": "https://dgii.test/auth",
                "reception": "https://dgii.test/recepcion",
                "status": "https://dgii.test/estado",
                "trackids": "https://dgii.test/trackids",
            }
        },
    )
    @patch("facturacion.management.commands.dgii_rest_send_signed_xml.DGIIRESTClient")
    def test_send_signed_xml_command_sends_file_without_state_changes(self, client_class):
        client_class.return_value = FakeManualRESTClient()
        issuer = self._manual_issuer(rnc="101010112", certificate_path="cert.p12")
        with TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "signed.xml"
            xml_path.write_text("<ECF>firmado</ECF>", encoding="utf-8")
            output = StringIO()

            call_command(
                "dgii_rest_send_signed_xml",
                file=str(xml_path),
                encf="E310000000001",
                company_id=issuer.company_id,
                issuer_id=issuer.id,
                save_artifact=False,
                stdout=output,
            )

        self.assertIn("Envio DGII REST manual completado", output.getvalue())
        client_class.return_value.submit_ecf.assert_called_once()

    @override_settings(
        ECF_DGII_ENVIRONMENT="testing",
        ECF_DGII_REST_BASE_URLS={
            "testing": {
                "auth": "https://dgii.test/auth",
                "reception": "https://dgii.test/recepcion",
                "status": "https://dgii.test/estado",
                "trackids": "https://dgii.test/trackids",
            }
        },
    )
    @patch("facturacion.management.commands.dgii_rest_send_signed_xml.DGIIRESTClient")
    def test_send_signed_xml_command_blocks_cross_company_issuer(self, client_class):
        client_class.return_value = FakeManualRESTClient()
        allowed_company = Company.objects.create(name="Empresa Manual A", rnc="401010101")
        issuer = self._manual_issuer(company=Company.objects.create(name="Empresa Manual B", rnc="401010102"), certificate_path="cert.p12")
        with TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "signed.xml"
            xml_path.write_text("<ECF>firmado</ECF>", encoding="utf-8")

            with self.assertRaises(CommandError):
                call_command(
                    "dgii_rest_send_signed_xml",
                    file=str(xml_path),
                    encf="E310000000001",
                    company_id=allowed_company.id,
                    issuer_id=issuer.id,
                    save_artifact=False,
                )

        client_class.return_value.submit_ecf.assert_not_called()

    def test_ecf_sequence_rejects_overlapping_ranges_for_same_issuer_and_type(self):
        issuer = self._manual_issuer(rnc="101010113")
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )

        with self.assertRaises(ValidationError):
            ECFSequence.objects.create(
                company=issuer.company,
                issuer=issuer,
                ecf_type="32",
                start_number=5,
                end_number=15,
                next_number=5,
            )

        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="34",
            start_number=5,
            end_number=15,
            next_number=5,
        )

    def test_certificate_metadata_service_marks_missing_certificate(self):
        issuer = self._manual_issuer(rnc="101010114")

        result = ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(result.status, ECFIssuerConfig.CERTIFICATE_STATUS_MISSING)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_MISSING)
        self.assertIsNotNone(issuer.certificate_status_updated_at)
        self.assertIsNone(issuer.certificate_subject)

    def test_certificate_metadata_service_extracts_active_certificate(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(Path(temp_dir) / "active.p12")
            issuer = self._manual_issuer(rnc="101010115", certificate_path=str(certificate_path))

            result = ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(result.status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertIn("CN=DGII Metadata Certificate", issuer.certificate_subject)
        self.assertTrue(issuer.certificate_fingerprint)
        self.assertIsNotNone(issuer.certificate_not_valid_before)
        self.assertIsNotNone(issuer.certificate_not_valid_after)
        self.assertIsNotNone(issuer.certificate_status_updated_at)

    def test_certificate_metadata_service_marks_rnc_match(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(
                Path(temp_dir) / "matched-rnc.p12",
                subject_rnc="101-010-120",
            )
            issuer = self._manual_issuer(rnc="101010120", certificate_path=str(certificate_path))

            result = ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(result.status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertEqual(issuer.certificate_rnc_detected, "101010120")
        self.assertEqual(issuer.certificate_rnc_match_status, ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED)

    def test_certificate_metadata_service_marks_rnc_mismatch_without_invalidating_certificate(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(
                Path(temp_dir) / "mismatch-rnc.p12",
                subject_rnc="101010121",
            )
            issuer = self._manual_issuer(rnc="101010122", certificate_path=str(certificate_path))

            ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertEqual(issuer.certificate_rnc_detected, "101010121")
        self.assertEqual(issuer.certificate_rnc_match_status, ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MISMATCH)

    def test_certificate_metadata_service_marks_rnc_not_found(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(Path(temp_dir) / "no-rnc.p12")
            issuer = self._manual_issuer(rnc="101010123", certificate_path=str(certificate_path))

            ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertIsNone(issuer.certificate_rnc_detected)
        self.assertEqual(issuer.certificate_rnc_match_status, ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND)

    def test_extract_rnc_candidates_reads_subject_and_subject_alt_name(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(
                Path(temp_dir) / "candidate-rnc.p12",
                subject_rnc="101010124",
                san_values=["RNC-101-010-125.dgii.test"],
            )
            _private_key, certificate, _additional = pkcs12.load_key_and_certificates(
                certificate_path.read_bytes(),
                b"secret",
            )

        candidates = extract_rnc_candidates_from_certificate(certificate)

        self.assertIn("101010124", candidates)
        self.assertIn("101010125", candidates)

    def test_certificate_metadata_service_classifies_expired_certificate(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(Path(temp_dir) / "expired.p12", expires_in_days=-1)
            issuer = self._manual_issuer(rnc="101010116", certificate_path=str(certificate_path))

            result = ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(result.status, ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED)
        self.assertIsNotNone(issuer.certificate_not_valid_after)

    def test_certificate_metadata_service_marks_invalid_certificate(self):
        with TemporaryDirectory() as temp_dir:
            certificate_path = Path(temp_dir) / "invalid.p12"
            certificate_path.write_text("not a certificate", encoding="utf-8")
            issuer = self._manual_issuer(rnc="101010117", certificate_path=str(certificate_path))

            result = ECFCertificateMetadataService().refresh(issuer)

        issuer.refresh_from_db()
        self.assertEqual(result.status, ECFIssuerConfig.CERTIFICATE_STATUS_INVALID)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_INVALID)
        self.assertIsNone(issuer.certificate_fingerprint)

    def test_refresh_certificate_metadata_command_updates_one_issuer(self):
        issuer = self._manual_issuer(rnc="101010118")
        output = StringIO()

        call_command("refresh_certificate_metadata", issuer_id=issuer.id, stdout=output)

        issuer.refresh_from_db()
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_MISSING)
        self.assertIn("Metadata de certificados actualizada: 1", output.getvalue())

    def test_ecf_issuer_api_create_refreshes_certificate_metadata(self):
        user = get_user_model().objects.create_superuser(username="issuer-cert-api", password="pass")
        company = Company.objects.create(name="Empresa Cert API", rnc="401010118")
        CompanyMembership.objects.create(user=user, company=company, role="owner")
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(Path(temp_dir) / "api.p12")
            request = APIRequestFactory().post(
                "/ecf-issuers/",
                {
                    "business_name": "Empresa Cert API SRL",
                    "rnc": "101010119",
                    "address": "Calle Cert",
                    "environment": "testing",
                    "default_ecf_type": "32",
                    "certificate_path": str(certificate_path),
                    "certificate_password": "secret",
                    "is_active": True,
                },
                format="json",
            )
            request.session = {"active_company_id": company.id}
            force_authenticate(request, user=user)

            response = ECFIssuerConfigViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        issuer = ECFIssuerConfig.objects.get(pk=response.data["id"])
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertIsNotNone(issuer.certificate_status_updated_at)
        self.assertEqual(response.data["certificate_status"], ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertIn("certificate_rnc_detected", response.data)
        self.assertIn("certificate_rnc_match_status", response.data)

    def test_owner_can_upload_issuer_certificate_and_receives_metadata(self):
        user = get_user_model().objects.create_user(username="issuer-upload-owner", password="pass")
        company = Company.objects.create(name="Empresa Upload Cert", rnc="401010120")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(
                Path(temp_dir) / "upload.p12",
                subject_rnc="101010120",
            )
            issuer = self._manual_issuer(company=company, rnc="101010120")
            request = APIRequestFactory().post(
                f"/ecf/issuers/{issuer.id}/certificate/",
                {
                    "certificate": SimpleUploadedFile(
                        "dgii.p12",
                        certificate_path.read_bytes(),
                        content_type="application/x-pkcs12",
                    ),
                    "password": "secret",
                },
                format="multipart",
            )
            request.session = {"active_company_id": company.id}
            force_authenticate(request, user=user)

            response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(request, pk=issuer.id)

        issuer.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["certificate_status"], ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE)
        self.assertEqual(response.data["certificate_rnc_detected"], "101010120")
        self.assertEqual(response.data["certificate_rnc_match_status"], ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED)
        self.assertTrue(issuer.certificate_path.endswith(".p12"))
        self.assertEqual(issuer.certificate_password, "secret")
        certificate = ECFCertificate.objects.get(issuer=issuer)
        self.assertTrue(certificate.is_active)
        self.assertEqual(certificate.certificate_reference, issuer.certificate_path)
        self.assertEqual(certificate.password_secret_reference, "secret")
        self.assertEqual(certificate.fingerprint, issuer.certificate_fingerprint)
        self.assertEqual(certificate.uploaded_by, user)

    def test_uploading_second_certificate_deactivates_previous_certificate(self):
        user = get_user_model().objects.create_user(username="issuer-upload-rotate", password="pass")
        company = Company.objects.create(name="Empresa Cert Rotate", rnc="401010130")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)
        issuer = self._manual_issuer(company=company, rnc="101010130")

        with TemporaryDirectory() as temp_dir:
            first_path = self._write_manual_pkcs12(Path(temp_dir) / "first.p12", subject_rnc="101010130")
            second_path = self._write_manual_pkcs12(Path(temp_dir) / "second.p12", subject_rnc="101010130")

            first_request = APIRequestFactory().post(
                f"/ecf/issuers/{issuer.id}/certificate/",
                {
                    "certificate": SimpleUploadedFile("first.p12", first_path.read_bytes(), content_type="application/x-pkcs12"),
                    "password": "secret",
                },
                format="multipart",
            )
            first_request.session = {"active_company_id": company.id}
            force_authenticate(first_request, user=user)
            first_response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(first_request, pk=issuer.id)

            second_request = APIRequestFactory().post(
                f"/ecf/issuers/{issuer.id}/certificate/",
                {
                    "certificate": SimpleUploadedFile("second.p12", second_path.read_bytes(), content_type="application/x-pkcs12"),
                    "password": "secret",
                },
                format="multipart",
            )
            second_request.session = {"active_company_id": company.id}
            force_authenticate(second_request, user=user)
            second_response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(second_request, pk=issuer.id)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        certificates = list(ECFCertificate.objects.filter(issuer=issuer).order_by("uploaded_at"))
        self.assertEqual(len(certificates), 2)
        self.assertFalse(certificates[0].is_active)
        self.assertIsNotNone(certificates[0].deactivated_at)
        self.assertTrue(certificates[1].is_active)
        self.assertEqual(certificates[1].previous_certificate_id, certificates[0].id)

    def test_user_from_other_company_cannot_upload_issuer_certificate(self):
        owner = get_user_model().objects.create_user(username="issuer-upload-foreign", password="pass")
        issuer_company = Company.objects.create(name="Empresa Cert Tenant A", rnc="401010121")
        other_company = Company.objects.create(name="Empresa Cert Tenant B", rnc="401010122")
        CompanyMembership.objects.create(user=owner, company=other_company, role=CompanyMembership.ROLE_OWNER)
        issuer = self._manual_issuer(company=issuer_company, rnc="101010121")
        request = APIRequestFactory().post(
            f"/ecf/issuers/{issuer.id}/certificate/",
            {
                "certificate": SimpleUploadedFile("dgii.p12", b"not-real", content_type="application/x-pkcs12"),
                "password": "secret",
            },
            format="multipart",
        )
        request.session = {"active_company_id": other_company.id}
        force_authenticate(request, user=owner)

        response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(request, pk=issuer.id)

        self.assertEqual(response.status_code, 404)

    def test_certificate_upload_rejects_non_p12_file(self):
        user = get_user_model().objects.create_user(username="issuer-upload-extension", password="pass")
        company = Company.objects.create(name="Empresa Cert Extension", rnc="401010123")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_ADMIN)
        issuer = self._manual_issuer(company=company, rnc="101010123")
        request = APIRequestFactory().post(
            f"/ecf/issuers/{issuer.id}/certificate/",
            {
                "certificate": SimpleUploadedFile("dgii.txt", b"not-real", content_type="text/plain"),
                "password": "secret",
            },
            format="multipart",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(request, pk=issuer.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn("certificate", response.data)

    def test_certificate_upload_wrong_password_marks_metadata_invalid(self):
        user = get_user_model().objects.create_user(username="issuer-upload-wrong-password", password="pass")
        company = Company.objects.create(name="Empresa Cert Password", rnc="401010124")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)
        with TemporaryDirectory() as temp_dir:
            certificate_path = self._write_manual_pkcs12(Path(temp_dir) / "wrong-password.p12")
            issuer = self._manual_issuer(company=company, rnc="101010124")
            request = APIRequestFactory().post(
                f"/ecf/issuers/{issuer.id}/certificate/",
                {
                    "certificate": SimpleUploadedFile(
                        "dgii.p12",
                        certificate_path.read_bytes(),
                        content_type="application/x-pkcs12",
                    ),
                    "password": "wrong-secret",
                },
                format="multipart",
            )
            request.session = {"active_company_id": company.id}
            force_authenticate(request, user=user)

            response = ECFIssuerConfigViewSet.as_view({"post": "upload_certificate"})(request, pk=issuer.id)

        issuer.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["certificate_status"], ECFIssuerConfig.CERTIFICATE_STATUS_INVALID)
        self.assertEqual(issuer.certificate_status, ECFIssuerConfig.CERTIFICATE_STATUS_INVALID)
        self.assertIsNotNone(issuer.certificate_status_updated_at)

    def test_ecf_certificate_allows_only_one_active_per_issuer_environment(self):
        issuer = self._manual_issuer(rnc="101010125")
        ECFCertificate.objects.create(
            company=issuer.company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-a.p12",
            fingerprint="fingerprint-a",
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            ECFCertificate.objects.create(
                company=issuer.company,
                issuer=issuer,
                environment=issuer.environment,
                status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
                storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
                certificate_reference="cert-b.p12",
                fingerprint="fingerprint-b",
                is_active=True,
            )

    def test_ecf_certificate_rejects_cross_company_issuer(self):
        issuer = self._manual_issuer(rnc="101010126")
        other_company = Company.objects.create(name="Empresa Cert Cruzada", rnc="401010126")

        with self.assertRaises(ValidationError):
            ECFCertificate.objects.create(
                company=other_company,
                issuer=issuer,
                environment=issuer.environment,
                status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
                storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
                certificate_reference="cert-cross.p12",
                fingerprint="fingerprint-cross",
                is_active=True,
            )

    def test_ecf_certificate_rejects_duplicate_fingerprint_for_same_issuer(self):
        issuer = self._manual_issuer(rnc="101010127")
        ECFCertificate.objects.create(
            company=issuer.company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-fingerprint-a.p12",
            fingerprint="same-fingerprint",
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            ECFCertificate.objects.create(
                company=issuer.company,
                issuer=issuer,
                environment=issuer.environment,
                status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
                storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
                certificate_reference="cert-fingerprint-b.p12",
                fingerprint="same-fingerprint",
                is_active=False,
            )

    def test_issuer_certificates_api_lists_company_certificates_without_password(self):
        user = get_user_model().objects.create_user(username="issuer-cert-list", password="pass")
        company = Company.objects.create(name="Empresa Cert Lista", rnc="401010127")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)
        issuer = self._manual_issuer(company=company, rnc="101010128")
        ECFCertificate.objects.create(
            company=company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-list.p12",
            password_secret_reference="secret-value",
            fingerprint="fingerprint-list",
            is_active=True,
        )
        request = APIRequestFactory().get(f"/ecf/issuers/{issuer.id}/certificates/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = ECFIssuerConfigViewSet.as_view({"get": "certificates"})(request, pk=issuer.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["fingerprint"], "fingerprint-list")
        self.assertNotIn("password_secret_reference", response.data[0])

    def test_issuer_certificates_api_shows_active_and_inactive_history(self):
        user = get_user_model().objects.create_user(username="issuer-cert-history", password="pass")
        company = Company.objects.create(name="Empresa Cert Historia", rnc="401010131")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)
        issuer = self._manual_issuer(company=company, rnc="101010131")
        previous = ECFCertificate.objects.create(
            company=company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-history-old.p12",
            fingerprint="fingerprint-history-old",
            is_active=False,
            deactivated_at=datetime.now(timezone.utc),
        )
        active = ECFCertificate.objects.create(
            company=company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-history-active.p12",
            fingerprint="fingerprint-history-active",
            is_active=True,
            previous_certificate=previous,
        )
        request = APIRequestFactory().get(f"/ecf/issuers/{issuer.id}/certificates/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = ECFIssuerConfigViewSet.as_view({"get": "certificates"})(request, pk=issuer.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [active.id, previous.id])
        self.assertTrue(response.data[0]["is_active"])
        self.assertFalse(response.data[1]["is_active"])

    def test_issuer_certificates_api_hides_other_company_issuer(self):
        user = get_user_model().objects.create_user(username="issuer-cert-list-other", password="pass")
        issuer_company = Company.objects.create(name="Empresa Cert Lista A", rnc="401010128")
        other_company = Company.objects.create(name="Empresa Cert Lista B", rnc="401010129")
        CompanyMembership.objects.create(user=user, company=other_company, role=CompanyMembership.ROLE_OWNER)
        issuer = self._manual_issuer(company=issuer_company, rnc="101010129")
        ECFCertificate.objects.create(
            company=issuer_company,
            issuer=issuer,
            environment=issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="cert-hidden.p12",
            fingerprint="fingerprint-hidden",
            is_active=True,
        )
        request = APIRequestFactory().get(f"/ecf/issuers/{issuer.id}/certificates/")
        request.session = {"active_company_id": other_company.id}
        force_authenticate(request, user=user)

        response = ECFIssuerConfigViewSet.as_view({"get": "certificates"})(request, pk=issuer.id)

        self.assertEqual(response.status_code, 404)

    def _environment(self):
        return DGIIRESTEnvironment(
            name="testing",
            auth_base_url="https://dgii.test/auth",
            reception_base_url="https://dgii.test/recepcion",
            status_base_url="https://dgii.test/estado",
            trackids_base_url="https://dgii.test/trackids",
            timeout=30,
            retries=1,
            retry_backoff=0.1,
            verify_tls=True,
        )

    def _manual_issuer(self, *, company=None, rnc="101010111", certificate_path=""):
        company = company or Company.objects.create(name=f"Empresa Manual {rnc}", rnc=f"4{rnc[-8:]}")
        return ECFIssuerConfig.objects.create(
            company=company,
            business_name=f"Empresa Manual {rnc}",
            rnc=rnc,
            address="Calle Manual",
            certificate_path=certificate_path,
            certificate_password="secret",
        )

    def _write_manual_pkcs12(
        self,
        path: Path,
        expires_in_days: int = 365,
        *,
        subject_rnc: str | None = None,
        san_values: list[str] | None = None,
    ) -> Path:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject_attributes = [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DO"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DGII Metadata Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, "DGII Metadata Certificate"),
        ]
        if subject_rnc:
            subject_attributes.append(x509.NameAttribute(NameOID.SERIAL_NUMBER, subject_rnc))
        subject = issuer = x509.Name(subject_attributes)

        now = datetime.now(timezone.utc)
        not_after = now + timedelta(days=expires_in_days)
        not_before = now - timedelta(days=30)
        if expires_in_days < 0:
            not_before = now + timedelta(days=expires_in_days - 30)

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
        )
        if san_values:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(value) for value in san_values]),
                critical=False,
            )
        certificate = builder.sign(key, hashes.SHA256())

        p12 = pkcs12.serialize_key_and_certificates(
            name=b"dgii-metadata-test",
            key=key,
            cert=certificate,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b"secret"),
        )
        path.write_bytes(p12)
        return path


class FakeRESTResponse:
    def __init__(self, data, status_code=200, text=None):
        self.data = data
        self.status_code = status_code
        self.text = text if text is not None else (data if isinstance(data, str) else "{}")

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class FakeRESTSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.verify = True

    def get(self, url, **kwargs):
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self.responses.pop(0)


class FakeCertificateLoader:
    def load(self, certificate_path, password):
        return object()


class FakeSeedSigner:
    def sign(self, xml_content, certificate):
        return f"<Signed>{xml_content}</Signed>"


class FakeRESTAuthClient:
    def get_token(self, certificate_path, certificate_password, issuer_rnc=None):
        return DGIIRESTToken(value="token-rest", expires_in=600)


class FakeManualRESTClient:
    def __init__(self):
        self.query_status = Mock(
            return_value=SimpleNamespace(
                status_code=200,
                result={"trackId": "track-manual", "estado": "Aceptado"},
                response_xml='{"estado":"Aceptado"}',
            )
        )
        self.submit_ecf = Mock(
            return_value=SimpleNamespace(
                status_code=200,
                result={"trackId": "track-send", "estado": "Recibido"},
                response_xml='{"estado":"Recibido"}',
            )
        )
        self.query_trackids = Mock(
            return_value=SimpleNamespace(
                status_code=200,
                result={"trackIds": ["track-send"]},
                response_xml='{"trackIds":["track-send"]}',
            )
        )


class CompanyFoundationAPITests(TestCase):
    """Validate minimal multi-company foundation without tenant scoping."""

    def test_public_registration_creates_active_standard_user_and_token(self):
        request = APIRequestFactory().post(
            "/auth/register/",
            {
                "first_name": "Nuevo",
                "email": "nuevo@example.com",
                "username": "nuevo-saas",
                "password": "strong-pass-123",
                "confirm_password": "strong-pass-123",
            },
            format="json",
        )

        response = RegisterView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username="nuevo-saas")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.email, "nuevo@example.com")
        self.assertTrue(Token.objects.filter(user=user, key=response.data["token"]).exists())
        self.assertEqual(response.data["user"]["permissions"], [])

    def test_companies_list_returns_only_active_memberships(self):
        user = get_user_model().objects.create_user(username="company-user", password="pass")
        active_company = Company.objects.create(name="Empresa Activa", legal_name="Empresa Activa SRL", rnc="101010101")
        inactive_membership_company = Company.objects.create(name="Empresa No Miembro", rnc="202020202")
        inactive_company = Company.objects.create(name="Empresa Inactiva", rnc="303030303", is_active=False)
        CompanyMembership.objects.create(user=user, company=active_company, role="admin", is_active=True)
        CompanyMembership.objects.create(user=user, company=inactive_membership_company, role="cashier", is_active=False)
        CompanyMembership.objects.create(user=user, company=inactive_company, role="owner", is_active=True)

        request = APIRequestFactory().get("/companies/")
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], active_company.id)
        self.assertEqual(response.data[0]["role"], "admin")

    def test_active_company_uses_single_membership_automatically(self):
        user = get_user_model().objects.create_user(username="single-company", password="pass")
        company = Company.objects.create(name="Empresa Unica", rnc="101010102")
        CompanyMembership.objects.create(user=user, company=company, role="cashier")

        request = APIRequestFactory().get("/companies/active/")
        request.session = {}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"get": "active"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["requires_selection"])
        self.assertEqual(response.data["active_company"]["id"], company.id)
        self.assertEqual(request.session["active_company_id"], company.id)

    def test_active_company_autoselects_first_active_membership_when_multiple_and_no_valid_context(self):
        user = get_user_model().objects.create_user(username="multi-company", password="pass")
        first = Company.objects.create(name="Empresa Uno", rnc="101010103")
        second = Company.objects.create(name="Empresa Dos", rnc="101010104")
        CompanyMembership.objects.create(user=user, company=first, role="owner")
        CompanyMembership.objects.create(user=user, company=second, role="accountant")

        request = APIRequestFactory().get("/companies/active/")
        request.session = {}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"get": "active"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["requires_selection"])
        self.assertEqual(response.data["active_company"]["id"], second.id)
        self.assertEqual(request.session["active_company_id"], second.id)
        self.assertEqual(len(response.data["companies"]), 2)

    def test_active_company_replaces_invalid_session_with_first_active_membership(self):
        user = get_user_model().objects.create_user(username="multi-company-invalid-session", password="pass")
        first = Company.objects.create(name="Empresa Zeta", rnc="101010107")
        second = Company.objects.create(name="Empresa Alfa", rnc="101010108")
        blocked = Company.objects.create(name="Empresa Bloqueada", rnc="101010109")
        CompanyMembership.objects.create(user=user, company=first, role="owner")
        CompanyMembership.objects.create(user=user, company=second, role="accountant")

        request = APIRequestFactory().get("/companies/active/")
        request.session = {"active_company_id": blocked.id}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"get": "active"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["requires_selection"])
        self.assertEqual(response.data["active_company"]["id"], second.id)
        self.assertEqual(request.session["active_company_id"], second.id)

    def test_switch_validates_active_membership(self):
        user = get_user_model().objects.create_user(username="switch-company", password="pass")
        allowed = Company.objects.create(name="Empresa Permitida", rnc="101010105")
        blocked = Company.objects.create(name="Empresa Bloqueada", rnc="101010106")
        CompanyMembership.objects.create(user=user, company=allowed, role="owner")

        request = APIRequestFactory().post("/companies/switch/", {"company_id": blocked.id}, format="json")
        request.session = {}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"post": "switch"})(request)

        self.assertEqual(response.status_code, 403)

        request = APIRequestFactory().post("/companies/switch/", {"company_id": allowed.id}, format="json")
        request.session = {}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"post": "switch"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["active_company"]["id"], allowed.id)
        self.assertEqual(request.session["active_company_id"], allowed.id)

    def test_owner_can_create_company_and_receives_owner_membership(self):
        user = get_user_model().objects.create_user(username="company-owner", password="pass")
        existing = Company.objects.create(name="Empresa Base", rnc="101010155")
        CompanyMembership.objects.create(user=user, company=existing, role="owner")

        request = APIRequestFactory().post(
            "/companies/",
            {
                "name": "Nueva Empresa",
                "legal_name": "Nueva Empresa SRL",
                "rnc": "131313131",
                "email": "empresa@example.com",
                "phone": "8090000000",
                "address": "Santo Domingo",
            },
            format="json",
        )
        request.session = {"active_company_id": existing.id}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        created = Company.objects.get(pk=response.data["id"])
        self.assertEqual(created.name, "Nueva Empresa")
        self.assertTrue(
            CompanyMembership.objects.filter(
                user=user,
                company=created,
                role="owner",
                is_active=True,
            ).exists()
        )

    def test_user_without_company_can_setup_first_company_and_becomes_owner(self):
        user = get_user_model().objects.create_user(username="first-company-user", password="pass")

        request = APIRequestFactory().post(
            "/companies/setup-first/",
            {
                "name": "Primera Empresa",
                "legal_name": "Primera Empresa SRL",
                "rnc": "151515199",
                "email": "primera@example.com",
                "phone": "8091234567",
                "address": "Santo Domingo",
            },
            format="json",
        )
        request.session = {}
        force_authenticate(request, user=user)

        response = CompanyViewSet.as_view({"post": "setup_first"})(request)

        self.assertEqual(response.status_code, 201)
        company = Company.objects.get(pk=response.data["active_company"]["id"])
        self.assertEqual(company.name, "Primera Empresa")
        self.assertEqual(request.session["active_company_id"], company.id)
        self.assertFalse(response.data["requires_selection"])
        self.assertTrue(
            CompanyMembership.objects.filter(
                user=user,
                company=company,
                role=CompanyMembership.ROLE_OWNER,
                is_active=True,
            ).exists()
        )
        user = get_user_model().objects.get(pk=user.pk)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.has_perm("facturacion.view_invoice"))
        self.assertTrue(user.has_perm("facturacion.add_invoice"))
        self.assertTrue(user.has_perm("facturacion.view_product"))
        self.assertTrue(user.has_perm("facturacion.add_product"))
        self.assertTrue(user.has_perm("facturacion.view_client"))
        self.assertTrue(user.has_perm("facturacion.add_client"))
        self.assertTrue(user.has_perm("facturacion.view_quotation"))
        self.assertTrue(user.has_perm("facturacion.view_almacen"))
        self.assertTrue(user.has_perm("facturacion.view_financial_totals"))
        self.assertTrue(user.has_perm("facturacion.view_ecfissuerconfig"))
        self.assertFalse(user.has_perm("auth.view_user"))
        self.assertFalse(user.has_perm("auth.add_user"))
        self.assertFalse(user.has_perm("auth.change_user"))
        self.assertFalse(user.has_perm("auth.delete_user"))
        self.assertFalse(user.has_perm("auth.view_group"))
        self.assertFalse(user.has_perm("auth.add_group"))
        self.assertFalse(user.has_perm("auth.change_group"))
        self.assertFalse(user.has_perm("auth.delete_group"))
        self.assertFalse(user.has_perm("auth.view_permission"))

        active_request = APIRequestFactory().get("/companies/active/")
        active_request.session = {"active_company_id": company.id}
        force_authenticate(active_request, user=user)
        active_response = CompanyViewSet.as_view({"get": "active"})(active_request)
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.data["active_company"]["id"], company.id)

        members_request = APIRequestFactory().get("/companies/members/")
        members_request.session = {"active_company_id": company.id}
        force_authenticate(members_request, user=user)
        members_response = CompanyViewSet.as_view({"get": "members"})(members_request)
        self.assertEqual(members_response.status_code, 200)
        self.assertEqual(len(members_response.data), 1)
        self.assertEqual(members_response.data[0]["role"], CompanyMembership.ROLE_OWNER)

    def test_saas_owner_cannot_access_global_auth_console_but_can_access_company_members(self):
        user = get_user_model().objects.create_user(username="saas-owner-auth-blocked", password="pass")
        company = Company.objects.create(name="Empresa Auth Scope", rnc="303030303")
        CompanyMembership.objects.create(user=user, company=company, role=CompanyMembership.ROLE_OWNER)

        for codename in ["view_user", "view_group", "view_permission"]:
            user.user_permissions.add(Permission.objects.get(content_type__app_label="auth", codename=codename))

        users_request = APIRequestFactory().get("/users/")
        users_request.session = {"active_company_id": company.id}
        force_authenticate(users_request, user=user)
        users_response = UserViewSet.as_view({"get": "list"})(users_request)
        self.assertEqual(users_response.status_code, 403)

        groups_request = APIRequestFactory().get("/groups/")
        groups_request.session = {"active_company_id": company.id}
        force_authenticate(groups_request, user=user)
        groups_response = GroupViewSet.as_view({"get": "list"})(groups_request)
        self.assertEqual(groups_response.status_code, 403)

        permissions_request = APIRequestFactory().get("/permissions/")
        permissions_request.session = {"active_company_id": company.id}
        force_authenticate(permissions_request, user=user)
        permissions_response = PermissionListView.as_view()(permissions_request)
        self.assertEqual(permissions_response.status_code, 403)

        members_request = APIRequestFactory().get("/companies/members/")
        members_request.session = {"active_company_id": company.id}
        force_authenticate(members_request, user=user)
        members_response = CompanyViewSet.as_view({"get": "members"})(members_request)
        self.assertEqual(members_response.status_code, 200)
        self.assertEqual(len(members_response.data), 1)

    def test_superuser_keeps_global_auth_console_access(self):
        superuser = get_user_model().objects.create_superuser(
            username="global-auth-admin",
            email="global-auth-admin@example.com",
            password="pass",
        )

        users_request = APIRequestFactory().get("/users/")
        force_authenticate(users_request, user=superuser)
        users_response = UserViewSet.as_view({"get": "list"})(users_request)
        self.assertEqual(users_response.status_code, 200)

        groups_request = APIRequestFactory().get("/groups/")
        force_authenticate(groups_request, user=superuser)
        groups_response = GroupViewSet.as_view({"get": "list"})(groups_request)
        self.assertEqual(groups_response.status_code, 200)

        permissions_request = APIRequestFactory().get("/permissions/")
        force_authenticate(permissions_request, user=superuser)
        permissions_response = PermissionListView.as_view()(permissions_request)
        self.assertEqual(permissions_response.status_code, 200)

    def test_staff_with_auth_permissions_keeps_global_read_access(self):
        staff = get_user_model().objects.create_user(username="staff-auth-reader", password="pass", is_staff=True)
        for codename in ["view_user", "view_group", "view_permission"]:
            staff.user_permissions.add(Permission.objects.get(content_type__app_label="auth", codename=codename))

        users_request = APIRequestFactory().get("/users/")
        force_authenticate(users_request, user=staff)
        users_response = UserViewSet.as_view({"get": "list"})(users_request)
        self.assertEqual(users_response.status_code, 200)

        groups_request = APIRequestFactory().get("/groups/")
        force_authenticate(groups_request, user=staff)
        groups_response = GroupViewSet.as_view({"get": "list"})(groups_request)
        self.assertEqual(groups_response.status_code, 200)

        permissions_request = APIRequestFactory().get("/permissions/")
        force_authenticate(permissions_request, user=staff)
        permissions_response = PermissionListView.as_view()(permissions_request)
        self.assertEqual(permissions_response.status_code, 200)

    def test_non_superuser_cannot_write_admin_flags_or_global_groups(self):
        staff = get_user_model().objects.create_user(username="staff-auth-writer", password="pass", is_staff=True)
        target = get_user_model().objects.create_user(username="target-auth-user", password="pass")
        for codename in ["change_user", "view_user"]:
            staff.user_permissions.add(Permission.objects.get(content_type__app_label="auth", codename=codename))

        flag_request = APIRequestFactory().patch(
            f"/users/{target.id}/",
            {"is_superuser": True},
            format="json",
        )
        force_authenticate(flag_request, user=staff)
        flag_response = UserViewSet.as_view({"patch": "partial_update"})(flag_request, pk=target.id)
        self.assertEqual(flag_response.status_code, 400)

        group_request = APIRequestFactory().patch(
            f"/users/{target.id}/",
            {"groups": []},
            format="json",
        )
        force_authenticate(group_request, user=staff)
        group_response = UserViewSet.as_view({"patch": "partial_update"})(group_request, pk=target.id)
        self.assertEqual(group_response.status_code, 400)

    def test_sync_saas_owner_permissions_removes_historical_auth_permissions(self):
        group = Group.objects.create(name=DEFAULT_OWNER_GROUP_NAME)
        auth_permissions = Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=["view_user", "add_user", "change_group", "view_permission"],
        )
        operational_permission = Permission.objects.get(
            content_type__app_label="facturacion",
            codename="view_invoice",
        )
        group.permissions.add(*auth_permissions, operational_permission)

        output = StringIO()
        call_command("sync_saas_owner_permissions", stdout=output)

        group.refresh_from_db()
        self.assertFalse(group.permissions.filter(content_type__app_label="auth").exists())
        self.assertTrue(group.permissions.filter(content_type__app_label="facturacion", codename="view_invoice").exists())
        self.assertIn("Permisos auth.* removidos", output.getvalue())
        self.assertIn("auth.view_user", output.getvalue())

    def test_sync_saas_owner_permissions_keeps_expected_operational_permissions(self):
        output = StringIO()

        call_command("sync_saas_owner_permissions", stdout=output)

        group = Group.objects.get(name=DEFAULT_OWNER_GROUP_NAME)
        expected = set(DEFAULT_OWNER_PERMISSION_CODENAMES)
        current = set(
            group.permissions.filter(content_type__app_label="facturacion").values_list("codename", flat=True)
        )
        self.assertTrue(expected.issubset(current))
        self.assertFalse(group.permissions.filter(content_type__app_label="auth").exists())
        self.assertIn("Grupo sincronizado", output.getvalue())

    def test_sync_saas_owner_permissions_is_idempotent(self):
        call_command("sync_saas_owner_permissions", stdout=StringIO())
        first = set(
            Group.objects.get(name=DEFAULT_OWNER_GROUP_NAME).permissions.values_list("id", flat=True)
        )

        output = StringIO()
        call_command("sync_saas_owner_permissions", stdout=output)
        second = set(
            Group.objects.get(name=DEFAULT_OWNER_GROUP_NAME).permissions.values_list("id", flat=True)
        )

        self.assertEqual(first, second)
        self.assertIn("Permisos agregados en esta ejecucion: 0", output.getvalue())
        self.assertIn("Permisos removidos en esta ejecucion: 0", output.getvalue())

    def test_sync_saas_owner_permissions_creates_missing_group(self):
        self.assertFalse(Group.objects.filter(name=DEFAULT_OWNER_GROUP_NAME).exists())

        output = StringIO()
        call_command("sync_saas_owner_permissions", stdout=output)

        self.assertTrue(Group.objects.filter(name=DEFAULT_OWNER_GROUP_NAME).exists())
        self.assertIn("no existia", output.getvalue())

    def test_clean_direct_auth_permissions_removes_from_normal_saas_user(self):
        user = get_user_model().objects.create_user(username="normal-direct-auth", password="pass")
        permission = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        user.user_permissions.add(permission)

        output = StringIO()
        call_command("clean_direct_auth_permissions", stdout=output)

        user = get_user_model().objects.get(pk=user.pk)
        self.assertFalse(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertIn("Usuario normal-direct-auth", output.getvalue())
        self.assertIn("Permisos directos removidos: 1", output.getvalue())

    def test_clean_direct_auth_permissions_preserves_superuser_permissions(self):
        user = get_user_model().objects.create_superuser(
            username="super-direct-auth",
            email="super-direct-auth@example.com",
            password="pass",
        )
        permission = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        user.user_permissions.add(permission)

        output = StringIO()
        call_command("clean_direct_auth_permissions", stdout=output)

        user = get_user_model().objects.get(pk=user.pk)
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertIn("superuser esperado", output.getvalue())
        self.assertIn("Permisos directos conservados: 1", output.getvalue())

    def test_clean_direct_auth_permissions_removes_redundant_staff_direct_permission(self):
        user = get_user_model().objects.create_user(username="staff-redundant-auth", password="pass", is_staff=True)
        group = Group.objects.create(name="Staff Auth Readers")
        redundant = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        preserved = Permission.objects.get(content_type__app_label="auth", codename="view_group")
        group.permissions.add(redundant)
        user.groups.add(group)
        user.user_permissions.add(redundant, preserved)

        output = StringIO()
        call_command("clean_direct_auth_permissions", stdout=output)

        user = get_user_model().objects.get(pk=user.pk)
        self.assertFalse(user.user_permissions.filter(pk=redundant.pk).exists())
        self.assertTrue(user.user_permissions.filter(pk=preserved.pk).exists())
        self.assertIn("auth.view_user", output.getvalue())
        self.assertIn("auth.view_group", output.getvalue())
        self.assertIn("Permisos directos removidos: 1", output.getvalue())
        self.assertIn("Permisos directos conservados: 1", output.getvalue())

    def test_clean_direct_auth_permissions_is_idempotent(self):
        user = get_user_model().objects.create_user(username="idempotent-direct-auth", password="pass")
        permission = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        user.user_permissions.add(permission)

        call_command("clean_direct_auth_permissions", stdout=StringIO())
        output = StringIO()
        call_command("clean_direct_auth_permissions", stdout=output)

        user = get_user_model().objects.get(pk=user.pk)
        self.assertFalse(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertIn("No se encontraron permisos directos auth.* sensibles", output.getvalue())
        self.assertIn("Permisos directos removidos: 0", output.getvalue())

    def test_setup_first_company_validates_rnc_and_phone(self):
        user = get_user_model().objects.create_user(username="first-company-validation", password="pass")

        invalid_rnc_request = APIRequestFactory().post(
            "/companies/setup-first/",
            {
                "name": "Empresa RNC Invalido",
                "rnc": "ABC123",
                "phone": "+1 (809) 123-4567",
            },
            format="json",
        )
        invalid_rnc_request.session = {}
        force_authenticate(invalid_rnc_request, user=user)
        invalid_rnc_response = CompanyViewSet.as_view({"post": "setup_first"})(invalid_rnc_request)
        self.assertEqual(invalid_rnc_response.status_code, 400)
        self.assertIn("rnc", invalid_rnc_response.data["fields"])

        invalid_phone_request = APIRequestFactory().post(
            "/companies/setup-first/",
            {
                "name": "Empresa Telefono Invalido",
                "rnc": "151515188",
                "phone": "809-ABC-0000",
            },
            format="json",
        )
        invalid_phone_request.session = {}
        force_authenticate(invalid_phone_request, user=user)
        invalid_phone_response = CompanyViewSet.as_view({"post": "setup_first"})(invalid_phone_request)
        self.assertEqual(invalid_phone_response.status_code, 400)
        self.assertIn("phone", invalid_phone_response.data["fields"])

    def test_client_serializer_validates_rnc_and_phone(self):
        company = Company.objects.create(name="Empresa Cliente Validacion", rnc="151515187")

        invalid_rnc = ClientSerializer(
            data={
                "company": company.id,
                "name": "Cliente RNC Invalido",
                "ruc_ci": "ABC123",
                "phone": "+1 (809) 000-0000",
            }
        )
        self.assertFalse(invalid_rnc.is_valid())
        self.assertIn("ruc_ci", invalid_rnc.errors)

        invalid_phone = ClientSerializer(
            data={
                "company": company.id,
                "name": "Cliente Telefono Invalido",
                "ruc_ci": "131444444",
                "phone": "809-ABC-0000",
            }
        )
        self.assertFalse(invalid_phone.is_valid())
        self.assertIn("phone", invalid_phone.errors)

        too_long_phone = ClientSerializer(
            data={
                "company": company.id,
                "name": "Cliente Telefono Largo",
                "ruc_ci": "131444445",
                "phone": "+1 (809) 123-45678901",
            }
        )
        self.assertFalse(too_long_phone.is_valid())
        self.assertIn("phone", too_long_phone.errors)

    def test_setup_first_company_is_blocked_when_user_already_has_active_company(self):
        user = get_user_model().objects.create_user(username="existing-company-user", password="pass")
        existing = Company.objects.create(name="Empresa Existente", rnc="151515198")
        CompanyMembership.objects.create(user=user, company=existing, role=CompanyMembership.ROLE_OWNER)

        request = APIRequestFactory().post(
            "/companies/setup-first/",
            {"name": "No Permitida", "rnc": "151515197"},
            format="json",
        )
        request.session = {"active_company_id": existing.id}
        force_authenticate(request, user=user)

        response = CompanyViewSet.as_view({"post": "setup_first"})(request)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Company.objects.filter(name="No Permitida").exists())

    def test_onboarded_owner_can_create_ecf_issuer_and_sequences(self):
        user = get_user_model().objects.create_user(username="fiscal-onboarding-owner", password="pass")

        request = APIRequestFactory().post(
            "/companies/setup-first/",
            {
                "name": "Empresa Fiscal Onboarding",
                "legal_name": "Empresa Fiscal Onboarding SRL",
                "rnc": "252525252",
                "email": "fiscal-onboarding@example.com",
                "phone": "8092525252",
                "address": "Santo Domingo",
            },
            format="json",
        )
        request.session = {}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"post": "setup_first"})(request)
        self.assertEqual(response.status_code, 201)
        company_id = response.data["active_company"]["id"]
        user = get_user_model().objects.get(pk=user.pk)

        issuer_request = APIRequestFactory().post(
            "/ecf/issuers/",
            {
                "business_name": "Empresa Fiscal Onboarding SRL",
                "trade_name": "Empresa Fiscal Onboarding",
                "rnc": "252525252",
                "address": "Santo Domingo",
                "environment": "testing",
                "is_active": True,
            },
            format="json",
        )
        issuer_request.session = {"active_company_id": company_id}
        force_authenticate(issuer_request, user=user)
        issuer_response = ECFIssuerConfigViewSet.as_view({"post": "create"})(issuer_request)
        self.assertEqual(issuer_response.status_code, 201)
        issuer_id = issuer_response.data["id"]

        for offset, ecf_type in enumerate(["31", "32", "34"], start=1):
            sequence_request = APIRequestFactory().post(
                "/ecf/sequences/",
                {
                    "issuer": issuer_id,
                    "ecf_type": ecf_type,
                    "start_number": offset * 100,
                    "end_number": offset * 100 + 99,
                    "next_number": offset * 100,
                    "is_active": True,
                },
                format="json",
            )
            sequence_request.session = {"active_company_id": company_id}
            force_authenticate(sequence_request, user=user)
            sequence_response = ECFSequenceViewSet.as_view({"post": "create"})(sequence_request)
            self.assertEqual(sequence_response.status_code, 201)
            self.assertEqual(sequence_response.data["ecf_type"], ecf_type)

        self.assertEqual(ECFSequence.objects.filter(company_id=company_id).count(), 3)

    def test_admin_can_update_active_company_but_cashier_cannot(self):
        admin = get_user_model().objects.create_user(username="company-admin", password="pass")
        cashier = get_user_model().objects.create_user(username="company-cashier", password="pass")
        company = Company.objects.create(name="Empresa Editable", rnc="141414141")
        CompanyMembership.objects.create(user=admin, company=company, role="admin")
        CompanyMembership.objects.create(user=cashier, company=company, role="cashier")

        request = APIRequestFactory().patch("/companies/%s/" % company.id, {"name": "Empresa Editada"}, format="json")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=admin)
        response = CompanyViewSet.as_view({"patch": "partial_update"})(request, pk=company.id)
        self.assertEqual(response.status_code, 200)
        company.refresh_from_db()
        self.assertEqual(company.name, "Empresa Editada")

        request = APIRequestFactory().patch("/companies/%s/" % company.id, {"name": "No Permitido"}, format="json")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=cashier)
        response = CompanyViewSet.as_view({"patch": "partial_update"})(request, pk=company.id)
        self.assertEqual(response.status_code, 403)

    def test_company_members_endpoint_returns_active_company_memberships(self):
        user = get_user_model().objects.create_user(username="members-admin", password="pass", email="admin@example.com")
        other_user = get_user_model().objects.create_user(username="members-cashier", password="pass", email="cashier@example.com")
        company = Company.objects.create(name="Empresa Miembros", rnc="151515151")
        other_company = Company.objects.create(name="Empresa Otra", rnc="161616161")
        CompanyMembership.objects.create(user=user, company=company, role="admin")
        CompanyMembership.objects.create(user=other_user, company=company, role="cashier", is_active=False)
        CompanyMembership.objects.create(user=other_user, company=other_company, role="owner")

        request = APIRequestFactory().get("/companies/members/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = CompanyViewSet.as_view({"get": "members"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({row["username"] for row in response.data}, {"members-admin", "members-cashier"})

    def test_owner_can_add_existing_user_as_company_member(self):
        owner = get_user_model().objects.create_user(username="member-owner", password="pass", email="owner@example.com")
        new_user = get_user_model().objects.create_user(username="new-member", password="pass", email="new@example.com")
        company = Company.objects.create(name="Empresa Add Member", rnc="171717171")
        CompanyMembership.objects.create(user=owner, company=company, role="owner")

        request = APIRequestFactory().post(
            "/companies/members/",
            {"email": "new@example.com", "role": "cashier"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=owner)
        response = CompanyViewSet.as_view({"post": "members"})(request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            CompanyMembership.objects.filter(
                user=new_user,
                company=company,
                role="cashier",
                is_active=True,
            ).exists()
        )

    def test_add_member_requires_existing_user(self):
        owner = get_user_model().objects.create_user(username="missing-owner", password="pass", email="missing-owner@example.com")
        company = Company.objects.create(name="Empresa Missing Member", rnc="181818181")
        CompanyMembership.objects.create(user=owner, company=company, role="owner")

        request = APIRequestFactory().post(
            "/companies/members/",
            {"email": "missing@example.com", "role": "cashier"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=owner)
        response = CompanyViewSet.as_view({"post": "members"})(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("El usuario debe existir", response.data["detail"])

    def test_admin_cannot_modify_owner_or_assign_owner_role(self):
        owner = get_user_model().objects.create_user(username="role-owner", password="pass", email="role-owner@example.com")
        admin = get_user_model().objects.create_user(username="role-admin", password="pass", email="role-admin@example.com")
        cashier = get_user_model().objects.create_user(username="role-cashier", password="pass", email="role-cashier@example.com")
        company = Company.objects.create(name="Empresa Roles", rnc="191919191")
        owner_membership = CompanyMembership.objects.create(user=owner, company=company, role="owner")
        CompanyMembership.objects.create(user=admin, company=company, role="admin")

        request = APIRequestFactory().patch(
            f"/companies/members/{owner_membership.id}/",
            {"role": "cashier"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=admin)
        response = CompanyViewSet.as_view({"patch": "update_member"})(request, membership_id=owner_membership.id)
        self.assertEqual(response.status_code, 400)

        request = APIRequestFactory().post(
            "/companies/members/",
            {"email": cashier.email, "role": "owner"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=admin)
        response = CompanyViewSet.as_view({"post": "members"})(request)
        self.assertEqual(response.status_code, 400)

    def test_cannot_deactivate_or_degrade_last_active_owner(self):
        owner = get_user_model().objects.create_user(username="last-owner", password="pass", email="last-owner@example.com")
        company = Company.objects.create(name="Empresa Last Owner", rnc="202020299")
        membership = CompanyMembership.objects.create(user=owner, company=company, role="owner")

        request = APIRequestFactory().patch(
            f"/companies/members/{membership.id}/",
            {"is_active": False},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=owner)
        response = CompanyViewSet.as_view({"patch": "update_member"})(request, membership_id=membership.id)
        self.assertEqual(response.status_code, 400)

        request = APIRequestFactory().patch(
            f"/companies/members/{membership.id}/",
            {"role": "admin"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=owner)
        response = CompanyViewSet.as_view({"patch": "update_member"})(request, membership_id=membership.id)
        self.assertEqual(response.status_code, 400)

    def test_get_current_company_accepts_valid_header_context(self):
        user = get_user_model().objects.create_user(username="header-company", password="pass")
        first = Company.objects.create(name="Empresa Header Uno", rnc="101010107")
        second = Company.objects.create(name="Empresa Header Dos", rnc="101010108")
        CompanyMembership.objects.create(user=user, company=first, role="admin")
        CompanyMembership.objects.create(user=user, company=second, role="cashier")

        request = APIRequestFactory().get("/dashboard/", HTTP_X_COMPANY_ID=str(second.id))
        request.session = {}
        request.user = user
        force_authenticate(request, user=user)

        self.assertEqual(get_current_company(request), second)
        self.assertEqual(request.session["active_company_id"], second.id)

    def test_session_company_has_priority_over_header(self):
        user = get_user_model().objects.create_user(username="session-priority", password="pass")
        session_company = Company.objects.create(name="Empresa Sesion", rnc="101010109")
        header_company = Company.objects.create(name="Empresa Header", rnc="101010110")
        session_membership = CompanyMembership.objects.create(user=user, company=session_company, role="admin")
        CompanyMembership.objects.create(user=user, company=header_company, role="cashier")

        request = APIRequestFactory().get("/dashboard/", HTTP_X_COMPANY_ID=str(header_company.id))
        request.session = {"active_company_id": session_company.id}
        request.user = user

        self.assertEqual(get_current_company(request), session_company)
        self.assertEqual(get_current_membership(request), session_membership)
        self.assertEqual(request.session["active_company_id"], session_company.id)

    def test_company_context_middleware_assigns_request_context(self):
        user = get_user_model().objects.create_user(username="middleware-company", password="pass")
        company = Company.objects.create(name="Empresa Middleware", rnc="101010111")
        membership = CompanyMembership.objects.create(user=user, company=company, role="owner")
        captured = {}

        def get_response(request):
            captured["company"] = request.company
            captured["membership"] = request.company_membership
            return None

        request = APIRequestFactory().get("/home/")
        request.session = {}
        request.user = user

        CompanyContextMiddleware(get_response)(request)

        self.assertEqual(captured["company"], company)
        self.assertEqual(captured["membership"], membership)
        self.assertEqual(request.session["active_company_id"], company.id)

    def test_company_context_middleware_resolves_token_user(self):
        user = get_user_model().objects.create_user(username="middleware-token", password="pass")
        company = Company.objects.create(name="Empresa Token", rnc="101010116")
        membership = CompanyMembership.objects.create(user=user, company=company, role="admin")
        token = Token.objects.create(user=user)
        captured = {}

        def get_response(request):
            captured["user"] = request.user
            captured["company"] = request.company
            captured["membership"] = request.company_membership
            return None

        request = APIRequestFactory().get("/home/", HTTP_AUTHORIZATION=f"Token {token.key}")
        request.session = {}

        CompanyContextMiddleware(get_response)(request)

        self.assertEqual(captured["user"], user)
        self.assertEqual(captured["company"], company)
        self.assertEqual(captured["membership"], membership)

    def test_require_current_company_fails_when_user_has_no_active_company(self):
        user = get_user_model().objects.create_user(username="requires-company", password="pass")

        request = APIRequestFactory().get("/dashboard/")
        request.session = {}
        request.user = user

        with self.assertRaises(PermissionDenied):
            require_current_company(request)

        self.assertIsNone(request.company)
        self.assertIsNone(request.company_membership)

    def test_company_scoped_queryset_mixin_filters_and_fails_closed_without_active_membership(self):
        user = get_user_model().objects.create_user(username="scoped-company", password="pass")
        first = Company.objects.create(name="Empresa Scope Uno", rnc="101010114")
        second = Company.objects.create(name="Empresa Scope Dos", rnc="101010115")
        first_membership = CompanyMembership.objects.create(user=user, company=first, role="admin")
        CompanyMembership.objects.create(user=user, company=second, role="cashier")

        class DummyScopedView(CompanyScopedQuerysetMixin):
            pass

        request = APIRequestFactory().get("/scoped/")
        request.session = {"active_company_id": first.id}
        request.user = user

        view = DummyScopedView()
        view.request = request

        scoped = view.get_company_scoped_queryset(CompanyMembership.objects.order_by("id"))
        self.assertEqual(list(scoped), [first_membership])
        self.assertTrue(user_has_company_access(user, first))

        no_company_user = get_user_model().objects.create_user(username="scoped-company-empty", password="pass")
        request = APIRequestFactory().get("/scoped/")
        request.session = {}
        request.user = no_company_user
        view.request = request

        with self.assertRaises(PermissionDenied):
            view.get_company_scoped_queryset(CompanyMembership.objects.all())

    def test_client_viewset_is_scoped_by_active_company(self):
        user = get_user_model().objects.create_superuser(username="client-scope", password="pass")
        first, second = self._member_companies(user)
        visible = Client.objects.create(company=first, name="Cliente Visible")
        Client.objects.create(company=second, name="Cliente Oculto")

        request = APIRequestFactory().get("/clients/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)

        response = ClientViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([client["id"] for client in response.data], [visible.id])

    def test_inventory_create_assigns_active_company_and_filters_products(self):
        user = get_user_model().objects.create_superuser(username="inventory-scope", password="pass")
        first, second = self._member_companies(user)
        other_category = Category.objects.create(company=second, name="Categoria Oculta")
        Product.objects.create(
            company=second,
            category=other_category,
            name="Producto Oculto",
            description="No visible",
            price=Decimal("10.00"),
            stock=5,
        )

        request = APIRequestFactory().post("/categories/", {"name": "Categoria Visible"}, format="json")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        category_response = CategoryListCreateView.as_view()(request)
        category = Category.objects.get(id=category_response.data["id"])

        request = APIRequestFactory().post(
            "/products/",
            {
                "name": "Producto Visible",
                "description": "Visible",
                "price": "12.00",
                "stock": 8,
                "category": category.id,
            },
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        product_response = ProductListCreateView.as_view()(request)

        self.assertEqual(category_response.status_code, 201)
        self.assertEqual(product_response.status_code, 201)
        category.refresh_from_db()
        product = Product.objects.get(id=product_response.data["id"])
        self.assertEqual(category.company, first)
        self.assertEqual(product.company, first)

        request = APIRequestFactory().get("/products/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        list_response = ProductListCreateView.as_view()(request)

        self.assertEqual([product["id"] for product in list_response.data], [product.id])

    def test_inventory_utils_are_scoped_by_product_id(self):
        user = get_user_model().objects.create_superuser(username="inventory-utils-id", password="pass")
        first, second = self._member_companies(user)
        first_category = Category.objects.create(company=first, name="Util ID Visible")
        second_category = Category.objects.create(company=second, name="Util ID Oculto")
        visible = Product.objects.create(
            company=first,
            category=first_category,
            name="Producto Util Visible",
            description="Visible",
            price=Decimal("10.00"),
            stock=5,
            barcode="UTIL-ID-001",
        )
        hidden = Product.objects.create(
            company=second,
            category=second_category,
            name="Producto Util Oculto",
            description="Oculto",
            price=Decimal("10.00"),
            stock=5,
            barcode="UTIL-ID-002",
        )

        request = APIRequestFactory().get(f"/products/{visible.id}/barcode-image/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = GenerateBarcodeImageView.as_view()(request, pk=visible.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["barcode"], visible.barcode)

        request = APIRequestFactory().get(f"/products/{hidden.id}/barcode-image/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = GenerateBarcodeImageView.as_view()(request, pk=hidden.id)
        self.assertEqual(response.status_code, 404)

    def test_inventory_utils_are_scoped_by_barcode(self):
        user = get_user_model().objects.create_superuser(username="inventory-utils-barcode", password="pass")
        first, second = self._member_companies(user)
        first_category = Category.objects.create(company=first, name="Util Barcode Visible")
        second_category = Category.objects.create(company=second, name="Util Barcode Oculto")
        visible = Product.objects.create(
            company=first,
            category=first_category,
            name="Producto Barcode Visible",
            description="Visible",
            price=Decimal("10.00"),
            stock=5,
            barcode="SHARED-BC-001",
        )
        hidden = Product.objects.create(
            company=second,
            category=second_category,
            name="Producto Barcode Oculto",
            description="Oculto",
            price=Decimal("10.00"),
            stock=5,
            barcode="SHARED-BC-001",
        )

        request = APIRequestFactory().get("/products/search-barcode/", {"barcode": visible.barcode})
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = SearchByBarcodeView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], visible.id)

        hidden.barcode = "HIDDEN-BC-001"
        hidden.save(update_fields=["barcode"])
        request = APIRequestFactory().get("/products/search-barcode/", {"barcode": hidden.barcode})
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = SearchByBarcodeView.as_view()(request)
        self.assertEqual(response.status_code, 404)

    def test_inventory_label_utilities_return_404_for_cross_company_product(self):
        user = get_user_model().objects.create_superuser(username="inventory-utils-labels", password="pass")
        first, second = self._member_companies(user)
        category = Category.objects.create(company=second, name="Util Label Oculto")
        hidden = Product.objects.create(
            company=second,
            category=category,
            name="Producto Label Oculto",
            description="Oculto",
            price=Decimal("10.00"),
            stock=5,
            barcode="UTIL-LABEL-001",
        )

        request = APIRequestFactory().post("/products/print-label/", {"product_id": hidden.id, "quantity": 1}, format="json")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = GenerateZPLLabelView.as_view()(request)
        self.assertEqual(response.status_code, 404)

        request = APIRequestFactory().post("/products/print-direct/", {"product_id": hidden.id, "quantity": 1}, format="json")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = PrintLabelDirectView.as_view()(request)
        self.assertEqual(response.status_code, 404)

    def test_low_stock_pdf_rejects_cross_company_products(self):
        user = get_user_model().objects.create_superuser(username="inventory-utils-pdf", password="pass")
        first, second = self._member_companies(user)
        first_category = Category.objects.create(company=first, name="PDF Visible")
        second_category = Category.objects.create(company=second, name="PDF Oculto")
        visible = Product.objects.create(
            company=first,
            category=first_category,
            name="Producto PDF Visible",
            description="Visible",
            price=Decimal("10.00"),
            stock=2,
            min_stock=5,
            barcode="PDF-001",
        )
        hidden = Product.objects.create(
            company=second,
            category=second_category,
            name="Producto PDF Oculto",
            description="Oculto",
            price=Decimal("10.00"),
            stock=1,
            min_stock=5,
            barcode="PDF-002",
        )

        request = APIRequestFactory().post(
            "/reports/low-stock-pdf/",
            {"products": [{"id": visible.id, "name": "Manipulado", "stock": 999}]},
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = generate_low_stock_pdf(request)
        self.assertEqual(response.status_code, 200)

        request = APIRequestFactory().post(
            "/reports/low-stock-pdf/",
            {"products": [{"id": hidden.id, "name": hidden.name, "stock": hidden.stock}]},
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = generate_low_stock_pdf(request)
        self.assertEqual(response.status_code, 404)

    def test_asset_statistics_are_scoped_by_active_company(self):
        user = get_user_model().objects.create_superuser(username="asset-scope", password="pass")
        first, second = self._member_companies(user)
        first_category = AssetCategory.objects.create(company=first, name="Herramientas")
        second_category = AssetCategory.objects.create(company=second, name="Equipos")
        Asset.objects.create(company=first, category=first_category, code="AST-001", name="Activo Visible")
        Asset.objects.create(company=second, category=second_category, code="AST-002", name="Activo Oculto")

        request = APIRequestFactory().get("/assets/statistics/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)

        response = AssetViewSet.as_view({"get": "statistics"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["by_category"][0]["category__name"], "Herramientas")

    def test_operations_scope_services_and_abonos(self):
        user = get_user_model().objects.create_superuser(username="operations-scope", password="pass")
        first, second = self._member_companies(user)
        other_service = ServicioManoObra.objects.create(
            company=second,
            nombre_persona="Servicio Oculto",
            descripcion="Otro tenant",
            precio_total=Decimal("100.00"),
        )

        request = APIRequestFactory().post(
            "/servicios-mano-obra/",
            {
                "nombre_persona": "Servicio Visible",
                "descripcion": "Tenant activo",
                "precio_total": "150.00",
                "modalidad_pago": "credito",
            },
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        service_response = ServicioManoObraViewSet.as_view({"post": "create"})(request)
        service = ServicioManoObra.objects.get(id=service_response.data["id"])

        request = APIRequestFactory().post(
            "/abonos-servicio/",
            {"servicio": service.id, "monto": "50.00"},
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        abono_response = AbonoServicioViewSet.as_view({"post": "create"})(request)

        request = APIRequestFactory().post(
            "/abonos-servicio/",
            {"servicio": other_service.id, "monto": "10.00"},
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        blocked_response = AbonoServicioViewSet.as_view({"post": "create"})(request)

        self.assertEqual(service_response.status_code, 201)
        self.assertEqual(abono_response.status_code, 201)
        self.assertEqual(blocked_response.status_code, 400)
        service.refresh_from_db()
        abono = AbonoServicio.objects.get(id=abono_response.data["id"])
        self.assertEqual(service.company, first)
        self.assertEqual(abono.company, first)

    def test_dashboard_inventory_status_is_scoped_but_sales_remain_global(self):
        user = get_user_model().objects.create_superuser(username="dashboard-low-risk-scope", password="pass")
        first, second = self._member_companies(user)
        first_category = Category.objects.create(company=first, name="Inventario Visible")
        second_category = Category.objects.create(company=second, name="Inventario Oculto")
        Product.objects.create(
            company=first,
            category=first_category,
            name="Producto Visible Bajo",
            description="Visible",
            price=Decimal("10.00"),
            stock=2,
        )
        Product.objects.create(
            company=second,
            category=second_category,
            name="Producto Oculto Bajo",
            description="Oculto",
            price=Decimal("10.00"),
            stock=0,
        )

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)

        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["inventoryStatus"]["low_stock_count"], 1)
        self.assertEqual(
            [category["name"] for category in response.data["inventoryStatus"]["categories"]],
            ["Inventario Visible"],
        )

    def test_invoice_viewset_pos_assigns_active_company(self):
        user = get_user_model().objects.create_superuser(username="invoice-company-scope", password="pass")
        first, second = self._member_companies(user)
        category = Category.objects.create(company=first, name="POS Scoped")
        product = Product.objects.create(
            company=first,
            category=category,
            name="Producto POS Scoped",
            description="Visible",
            price=Decimal("100.00"),
            stock=5,
        )
        other_category = Category.objects.create(company=second, name="POS Other")
        other_product = Product.objects.create(
            company=second,
            category=other_category,
            name="Producto POS Other",
            description="Oculto",
            price=Decimal("100.00"),
            stock=5,
        )

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "auto_ecf": False,
                "details": [{"product": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        blocked_request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "auto_ecf": False,
                "details": [{"product": other_product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        blocked_request.session = {"active_company_id": first.id}
        force_authenticate(blocked_request, user=user)
        blocked_response = InvoiceViewSet.as_view({"post": "create"})(blocked_request)

        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.data["id"])
        self.assertEqual(invoice.company, first)
        self.assertEqual(blocked_response.status_code, 400)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_quotation_conversion_keeps_company_on_invoice(self):
        user = get_user_model().objects.create_superuser(username="quotation-company-scope", password="pass")
        first, _second = self._member_companies(user)
        category = Category.objects.create(company=first, name="Quote Scoped")
        product = Product.objects.create(
            company=first,
            category=category,
            name="Producto Quote Scoped",
            description="Visible",
            price=Decimal("100.00"),
            stock=5,
        )
        issuer = ECFIssuerConfig.objects.create(
            company=first,
            business_name="Empresa Quote Company SRL",
            rnc="131313131",
            address="Calle Quote Company",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )

        request = APIRequestFactory().post(
            "/quotations/",
            {
                "customer_name": "Cliente Cotizacion",
                "details": [{"product": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        create_response = QuotationViewSet.as_view({"post": "create"})(request)
        quotation = Quotation.objects.get(id=create_response.data["id"])
        QuotationService().approve(quotation.id)

        request = APIRequestFactory().post(
            f"/quotations/{quotation.id}/convert-to-invoice/",
            {"status": "pending", "issuer": issuer.id, "ecf_type": "32"},
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        convert_response = QuotationViewSet.as_view({"post": "convert_to_invoice"})(request, pk=quotation.id)

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(convert_response.status_code, 201)
        quotation.refresh_from_db()
        invoice = Invoice.objects.get(id=convert_response.data["invoice_id"])
        self.assertEqual(quotation.company, first)
        self.assertEqual(invoice.company, first)

    def test_dashboard_sales_are_scoped_by_invoice_company(self):
        user = get_user_model().objects.create_superuser(username="dashboard-sales-scope", password="pass")
        first, second = self._member_companies(user)
        first_category = Category.objects.create(company=first, name="Ventas Visible")
        second_category = Category.objects.create(company=second, name="Ventas Oculta")
        first_product = Product.objects.create(
            company=first,
            category=first_category,
            name="Producto Venta Visible",
            description="Visible",
            price=Decimal("100.00"),
            stock=5,
        )
        second_product = Product.objects.create(
            company=second,
            category=second_category,
            name="Producto Venta Oculta",
            description="Oculto",
            price=Decimal("250.00"),
            stock=5,
        )
        visible_invoice = Invoice.objects.create(
            company=first,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        hidden_invoice = Invoice.objects.create(
            company=second,
            subtotal=Decimal("250.00"),
            tax=Decimal("45.00"),
            discount=Decimal("0.00"),
            total=Decimal("295.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=visible_invoice,
            product=first_product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )
        InvoiceDetail.objects.create(
            invoice=hidden_invoice,
            product=second_product,
            quantity=1,
            price=Decimal("250.00"),
            subtotal=Decimal("250.00"),
        )

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["salesSummary"]["sales_count"], 1)
        self.assertEqual(response.data["salesSummary"]["total_sales"], 118.0)
        self.assertEqual(response.data["topProducts"][0]["name"], "Producto Venta Visible")
        self.assertEqual(response.data["recentSales"][0]["id"], visible_invoice.id)

    def test_low_risk_constraints_are_company_scoped(self):
        user = get_user_model().objects.create_superuser(username="constraints-scope", password="pass")
        first, second = self._member_companies(user)

        Category.objects.create(company=first, name="Repetible")
        Category.objects.create(company=second, name="Repetible")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(company=first, name="Repetible")

        Client.objects.create(company=first, name="Cliente Uno", ruc_ci="001001001")
        Client.objects.create(company=second, name="Cliente Dos", ruc_ci="001001001")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Client.objects.create(company=first, name="Cliente Tres", ruc_ci="001001001")

        first_asset_category = AssetCategory.objects.create(company=first, name="Activos")
        second_asset_category = AssetCategory.objects.create(company=second, name="Activos")
        Asset.objects.create(company=first, category=first_asset_category, code="FIX-001", name="Activo Uno")
        Asset.objects.create(company=second, category=second_asset_category, code="FIX-001", name="Activo Dos")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Asset.objects.create(company=first, category=first_asset_category, code="FIX-001", name="Activo Tres")

    def test_ecf_config_viewsets_are_scoped_by_active_company(self):
        user = get_user_model().objects.create_superuser(username="ecf-config-scope", password="pass")
        first, second = self._member_companies(user)
        visible_issuer = ECFIssuerConfig.objects.create(
            company=first,
            business_name="Emisor Visible",
            rnc="501000001",
            address="Calle Visible",
        )
        hidden_issuer = ECFIssuerConfig.objects.create(
            company=second,
            business_name="Emisor Oculto",
            rnc="501000002",
            address="Calle Oculta",
        )
        visible_sequence = ECFSequence.objects.create(
            company=first,
            issuer=visible_issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )
        ECFSequence.objects.create(
            company=second,
            issuer=hidden_issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )

        request = APIRequestFactory().get("/ecf-issuers/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        issuer_response = ECFIssuerConfigViewSet.as_view({"get": "list"})(request)

        request = APIRequestFactory().get("/ecf-sequences/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        sequence_response = ECFSequenceViewSet.as_view({"get": "list"})(request)

        self.assertEqual(issuer_response.status_code, 200)
        self.assertEqual([issuer["id"] for issuer in issuer_response.data], [visible_issuer.id])
        self.assertEqual(sequence_response.status_code, 200)
        self.assertEqual([sequence["id"] for sequence in sequence_response.data], [visible_sequence.id])

    def test_ecf_sequence_rejects_cross_company_issuer(self):
        user = get_user_model().objects.create_superuser(username="ecf-sequence-cross", password="pass")
        first, second = self._member_companies(user)
        issuer = ECFIssuerConfig.objects.create(
            company=second,
            business_name="Emisor Ajeno",
            rnc="501000003",
            address="Calle Ajena",
        )

        request = APIRequestFactory().post(
            "/ecf-sequences/",
            {
                "issuer": issuer.id,
                "ecf_type": "32",
                "start_number": 1,
                "end_number": 10,
                "next_number": 1,
            },
            format="json",
        )
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = ECFSequenceViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("issuer", response.data["fields"])

    def test_document_factory_resolves_issuer_by_company_and_rejects_ambiguous_active_issuers(self):
        user = get_user_model().objects.create_superuser(username="ecf-factory-company", password="pass")
        first, second = self._member_companies(user)
        first_issuer = ECFIssuerConfig.objects.create(
            company=first,
            business_name="Emisor Empresa Uno",
            rnc="501000004",
            address="Calle Uno",
        )
        second_issuer = ECFIssuerConfig.objects.create(
            company=second,
            business_name="Emisor Empresa Dos",
            rnc="501000005",
            address="Calle Dos",
        )
        ECFSequence.objects.create(company=first, issuer=first_issuer, ecf_type="32", start_number=1, end_number=10, next_number=1)
        ECFSequence.objects.create(company=second, issuer=second_issuer, ecf_type="32", start_number=1, end_number=10, next_number=1)
        invoice = Invoice.objects.create(
            company=first,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )

        result = ECFDocumentFactoryService().create_for_invoice(invoice, user=user, ecf_type="32")
        self.assertIsNone(result.error)
        self.assertEqual(result.document.issuer_id, first_issuer.id)

        invoice_two = Invoice.objects.create(
            company=first,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        ECFIssuerConfig.objects.create(
            company=first,
            business_name="Emisor Empresa Uno Alterno",
            rnc="501000006",
            address="Calle Uno B",
        )

        ambiguous = ECFDocumentFactoryService().create_for_invoice(invoice_two, user=user, ecf_type="32")
        self.assertIn("varios emisores", ambiguous.error)

    def test_ecf_runtime_viewset_is_scoped_by_active_company(self):
        user = get_user_model().objects.create_superuser(username="ecf-runtime-scope", password="pass")
        first, second = self._member_companies(user)
        visible = self._ecf_document(first, encf="E320000001001", fiscal_status="accepted")
        hidden = self._ecf_document(second, encf="E320000001002", fiscal_status="rejected")

        request = APIRequestFactory().get("/ecf/documents/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = ElectronicFiscalDocumentViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        payload = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([item["id"] for item in payload], [visible.id])
        self.assertNotIn(hidden.id, [item["id"] for item in payload])

    def test_same_encf_is_allowed_for_different_issuers_and_companies(self):
        user = get_user_model().objects.create_superuser(username="ecf-duplicate-cross-company", password="pass")
        first, second = self._member_companies(user)

        first_document = self._ecf_document(first, encf="E310000000001", ecf_type="31")
        second_document = self._ecf_document(second, encf="E310000000001", ecf_type="31")

        self.assertNotEqual(first_document.issuer_id, second_document.issuer_id)
        self.assertEqual(first_document.encf, second_document.encf)

        request = APIRequestFactory().get("/ecf/documents/", {"search": "E310000000001"})
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = ElectronicFiscalDocumentViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        payload = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([item["id"] for item in payload], [first_document.id])

    def test_same_issuer_cannot_duplicate_encf(self):
        company = Company.objects.create(name="Empresa Emisor Unico", rnc="101019999")
        document = self._ecf_document(company, encf="E310000000001", ecf_type="31")
        invoice = Invoice.objects.create(
            company=company,
            invoice_number="FAC-DUP-001",
            subtotal=Decimal("50.00"),
            tax=Decimal("9.00"),
            discount=Decimal("0.00"),
            total=Decimal("59.00"),
            status="paid",
        )

        with self.assertRaises(ValidationError):
            ElectronicFiscalDocument.objects.create(
                company=company,
                invoice=invoice,
                issuer=document.issuer,
                sequence=document.sequence,
                ecf_type="31",
                encf="E310000000001",
            )

    def test_ecf_async_monitor_is_scoped_by_active_company(self):
        user = get_user_model().objects.create_superuser(username="ecf-monitor-scope", password="pass")
        first, second = self._member_companies(user)
        self._ecf_document(first, encf="E320000001003", fiscal_status="accepted", job_status="idle")
        self._ecf_document(first, encf="E320000001004", fiscal_status="submitted", job_status="queued")
        self._ecf_document(second, encf="E320000001005", fiscal_status="rejected", job_status="failed")

        request = APIRequestFactory().get("/ecf/documents/async-monitor/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = ElectronicFiscalDocumentViewSet.as_view({"get": "async_monitor"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["accepted"], 1)
        self.assertEqual(response.data["submitted"], 1)
        self.assertEqual(response.data["rejected"], 0)
        self.assertEqual(response.data["technical_failed"], 0)
        self.assertEqual(response.data["queued"], 1)

    def test_ecf_event_logs_are_scoped_by_document_company(self):
        user = get_user_model().objects.create_superuser(username="ecf-log-scope", password="pass")
        first, second = self._member_companies(user)
        visible_document = self._ecf_document(first, encf="E320000001006")
        hidden_document = self._ecf_document(second, encf="E320000001007")
        visible_log = ECFEventLog.objects.create(
            electronic_document=visible_document,
            event_type="created",
            message="Visible",
        )
        ECFEventLog.objects.create(
            electronic_document=hidden_document,
            event_type="created",
            message="Hidden",
        )

        request = APIRequestFactory().get("/ecf/events/")
        request.session = {"active_company_id": first.id}
        force_authenticate(request, user=user)
        response = ECFEventLogViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        payload = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([item["id"] for item in payload], [visible_log.id])

    def test_electronic_document_rejects_cross_company_relations(self):
        user = get_user_model().objects.create_superuser(username="ecf-cross-company", password="pass")
        first, second = self._member_companies(user)
        invoice = Invoice.objects.create(
            company=first,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        issuer = ECFIssuerConfig.objects.create(company=second, business_name="Emisor Cruzado", rnc="501000010", address="Calle")
        sequence = ECFSequence.objects.create(company=second, issuer=issuer, ecf_type="32", start_number=1, end_number=10, next_number=1)

        document = ElectronicFiscalDocument(
            company=first,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="32",
            encf="E320000001008",
        )

        with self.assertRaises(ValidationError):
            document.full_clean()

    def _member_companies(self, user):
        first = Company.objects.create(name=f"Empresa A {user.username}", rnc="101010201")
        second = Company.objects.create(name=f"Empresa B {user.username}", rnc="101010202")
        CompanyMembership.objects.create(user=user, company=first, role="admin")
        CompanyMembership.objects.create(user=user, company=second, role="cashier")
        return first, second

    def _ecf_document(self, company, *, encf, fiscal_status="draft", job_status="idle", ecf_type="32"):
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name=f"Emisor {encf}",
            rnc=str(600000000 + ECFIssuerConfig.objects.count()),
            address="Calle Fiscal",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type=ecf_type,
            start_number=1,
            end_number=20,
            next_number=1,
        )
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        return ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type=ecf_type,
            encf=encf,
            status=fiscal_status,
            fiscal_status=fiscal_status,
            job_status=job_status,
        )


class DGIIServicesTests(TestCase):
    """Validate DGII submission/status services without network calls."""

    @override_settings(ECF_DGII_MOCK_ENABLED=False)
    def test_submit_persists_track_id_and_soap_envelopes(self):
        document = self._document(signed_xml_content="<ECF />")

        result = DGIISubmissionService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeDGIISOAPClient,
        ).submit(document)

        document.refresh_from_db()
        self.assertEqual(result.track_id, "track-001")
        self.assertEqual(document.track_id, "track-001")
        self.assertEqual(document.status, "submitted")
        self.assertEqual(document.fiscal_status, "submitted")
        self.assertEqual(document.job_status, "idle")
        self.assertIn("SubmitRequest", document.dgii_request_xml)
        self.assertIn("SubmitResponse", document.dgii_response_xml)

    def test_status_check_persists_accepted_state(self):
        document = self._document(signed_xml_content="<ECF />", track_id="track-001", status="pending")

        result = DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeDGIISOAPClient,
        ).check(document)

        document.refresh_from_db()
        self.assertEqual(result.status, "accepted")
        self.assertEqual(document.status, "accepted")
        self.assertIsNotNone(document.accepted_at)

    @override_settings(ECF_DGII_MOCK_ENABLED=True)
    def test_mock_status_check_reconciles_queued_document_with_track_id(self):
        document = self._document(signed_xml_content="<ECF />", track_id="track-queued", status="queued")

        result = DGIIStatusService().check(document)

        document.refresh_from_db()
        self.assertEqual(result.status, "accepted")
        self.assertEqual(document.status, "accepted")
        self.assertTrue(
            ECFStatusEvent.objects.filter(
                document=document,
                source="dgii_status_reconciliation",
                new_fiscal_status="submitted",
            ).exists()
        )

    def _document(self, signed_xml_content: str, track_id: str | None = None, status: str = "signed"):
        company = Company.objects.create(name="Empresa SOAP", rnc="101010101")
        category = Category.objects.create(company=company, name="SOAP")
        product = Product.objects.create(
            company=company,
            name="Producto SOAP",
            description="Prueba",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente SOAP", ruc_ci="131111111")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa SOAP SRL",
            rnc="101010101",
            address="Calle SOAP",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=10,
            next_number=2,
        )
        return ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="31",
            encf="E310000000001",
            signed_xml_content=signed_xml_content,
            track_id=track_id,
            status=status,
        )


class FakeEnvironmentResolver:
    def resolve(self, environment=None):
        return DGIISOAPEnvironment(
            name=environment or "testing",
            reception_wsdl="https://example.test/reception?wsdl",
            status_wsdl="https://example.test/status?wsdl",
            trackids_wsdl=None,
            submit_operation="Submit",
            status_operation="Status",
            trackids_operation="TrackIds",
            timeout=1,
            retries=0,
            retry_backoff=0,
            verify_tls=True,
        )


class FakeTokenProvider:
    def get_token(self):
        return DGIIBearerToken("token")


class FakeDGIISOAPClient:
    def __init__(self, environment, token):
        self.environment = environment
        self.token = token

    def submit_ecf(self, signed_xml_content, encf, issuer_rnc):
        return SOAPCallResult(
            result={"trackId": "track-001", "estado": "Recibido", "codigo": 1},
            request_xml="<SubmitRequest />",
            response_xml="<SubmitResponse />",
        )

    def query_status(self, track_id):
        return SOAPCallResult(
            result={"trackId": track_id, "estado": "Aceptado", "codigo": 1},
            request_xml="<StatusRequest />",
            response_xml="<StatusResponse />",
        )


class ECFAsyncTaskTests(TestCase):
    """Validate async task idempotency and DGII retry-safe behavior."""

    def test_submit_task_skips_duplicate_when_track_id_exists(self):
        document = self._document(signed_xml_content="<ECF />", track_id="track-existing", status="pending")

        result = submit_dgii.apply(args=[document.id]).get()

        document.refresh_from_db()
        self.assertTrue(result["skipped"])
        self.assertEqual(document.submission_attempts, 0)
        self.assertEqual(document.track_id, "track-existing")
        self.assertTrue(ECFEventLog.objects.filter(electronic_document=document, event_type="skipped").exists())

    @patch("facturacion.ecf.tasks.dgii.check_status.apply_async")
    @patch("facturacion.ecf.tasks.dgii.DGIISubmissionService")
    def test_submit_task_records_attempt_and_schedules_status_check(self, service_class, status_task):
        document = self._document(signed_xml_content="<ECF />")

        class FakeSubmissionService:
            def submit(self, document, user=None, environment=None):
                document.track_id = "track-async"
                document.status = "submitted"
                document.fiscal_status = "submitted"
                document.save(update_fields=["track_id", "status", "fiscal_status", "updated_at"])
                return SimpleNamespace(track_id="track-async", status="submitted", document=document)

        service_class.return_value = FakeSubmissionService()

        result = submit_dgii.apply(args=[document.id]).get()

        document.refresh_from_db()
        self.assertEqual(result["track_id"], "track-async")
        self.assertEqual(document.submission_attempts, 1)
        status_task.assert_called_once()

    @override_settings(ECF_DGII_MOCK_ENABLED=True)
    def test_check_status_task_recovers_document_marked_error_after_track_id(self):
        document = self._document(
            signed_xml_content="<ECF />",
            track_id="track-error",
            status="error",
        )

        result = check_status.apply(args=[document.id]).get()

        document.refresh_from_db()
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(document.status, "accepted")
        self.assertIsNone(document.last_error)

    def test_electronic_document_company_cannot_be_cleared_before_generate_task(self):
        document = self._document(signed_xml_content="", status="draft")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ElectronicFiscalDocument.objects.filter(pk=document.pk).update(company=None)

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "draft")
        self.assertEqual(document.status, "draft")
        self.assertEqual(document.job_status, "idle")
        self.assertIsNone(document.last_error)

    def test_submit_task_records_cross_company_issuer_as_technical_failure(self):
        document = self._document(signed_xml_content="<ECF />", status="signed")
        other_company = Company.objects.create(name="Empresa Async Externa", rnc="309999999")
        ECFIssuerConfig.objects.filter(pk=document.issuer_id).update(company=other_company)

        with self.assertRaises(Exception):
            submit_dgii.apply(args=[document.id]).get()

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "signed")
        self.assertEqual(document.status, "signed")
        self.assertEqual(document.job_status, "failed")
        self.assertIn("otra empresa", document.last_error)
        self.assertEqual(document.submission_attempts, 0)
        self.assertTrue(
            ECFStatusEvent.objects.filter(
                document=document,
                source="task_submit_dgii_failed",
                previous_fiscal_status="signed",
                new_fiscal_status="signed",
                new_job_status="failed",
            ).exists()
        )

    def _document(self, signed_xml_content: str, track_id: str | None = None, status: str = "signed"):
        company = Company.objects.create(name="Empresa Async", rnc="101010102")
        category = Category.objects.create(company=company, name="ASYNC")
        product = Product.objects.create(
            company=company,
            name="Producto Async",
            description="Prueba",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente Async", ruc_ci="131111111")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Async SRL",
            rnc="101010102",
            address="Calle Async",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=10,
            next_number=2,
        )
        return ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="31",
            encf="E310000000002",
            signed_xml_content=signed_xml_content,
            track_id=track_id,
            status=status,
        )


class ECFStatusSplitCompatibilityTests(TestCase):
    """Validate 1B.1 serializer compatibility without changing operations."""

    def test_serializer_exposes_status_as_effective_fiscal_status(self):
        document = self._document(status="queued", track_id="track-queued", signed_xml_content="<ECF />")

        data = ElectronicFiscalDocumentSerializer(document).data

        self.assertEqual(document.status, "queued")
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["fiscal_status"], "submitted")
        self.assertEqual(data["job_status"], "queued")
        self.assertEqual(data["job_status_label"], "En cola")
        self.assertTrue(data["can_check_status"])
        self.assertFalse(data["can_submit"])

    def test_serializer_preserves_accepted_and_rejected_fiscal_statuses(self):
        accepted = self._document(status="accepted", encf="E310000000101")
        rejected = self._document(status="rejected", encf="E310000000102")

        self.assertEqual(ElectronicFiscalDocumentSerializer(accepted).data["status"], "accepted")
        self.assertEqual(ElectronicFiscalDocumentSerializer(rejected).data["status"], "rejected")
        self.assertTrue(ElectronicFiscalDocumentSerializer(accepted).data["is_terminal_fiscal"])

    def test_serializer_maps_legacy_error_to_failed_job_without_losing_fiscal_stage(self):
        document = self._document(status="error", signed_xml_content="<ECF />", encf="E310000000103")

        data = ElectronicFiscalDocumentSerializer(document).data

        self.assertEqual(document.status, "error")
        self.assertEqual(data["status"], "signed")
        self.assertEqual(data["fiscal_status"], "signed")
        self.assertEqual(data["job_status"], "failed")
        self.assertTrue(data["can_retry"])

    def test_async_monitor_separates_fiscal_and_technical_statuses(self):
        user = get_user_model().objects.create_superuser(
            username="monitor-admin",
            email="monitor-admin@example.test",
            password="test-pass",
        )
        rejected = self._document(status="rejected", encf="E310000000104")
        failed = self._document(status="submitted", encf="E310000000105", track_id="track-failed", company=rejected.company)
        failed.job_status = "failed"
        failed.last_error = "SOAP timeout"
        failed.save(update_fields=["job_status", "last_error", "updated_at"])
        CompanyMembership.objects.create(user=user, company=rejected.company, role="admin")

        request = APIRequestFactory().get("/ecf/documents/async-monitor/")
        request.session = {"active_company_id": rejected.company_id}
        force_authenticate(request, user=user)
        response = ElectronicFiscalDocumentViewSet.as_view({"get": "async_monitor"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rejected"], 1)
        self.assertEqual(response.data["technical_failed"], 1)
        self.assertEqual(response.data["pending_dgii"], 1)
        self.assertIn("by_fiscal_status", response.data)
        self.assertIn("by_job_status", response.data)
        self.assertIn("by_status", response.data)

    def _document(
        self,
        *,
        status: str,
        encf: str = "E310000000100",
        track_id: str | None = None,
        signed_xml_content: str = "",
        company: Company | None = None,
    ):
        company = company or Company.objects.create(name=f"Empresa Status {encf}", rnc=encf[-9:])
        category = Category.objects.create(company=company, name=f"STATUS-{encf}")
        product = Product.objects.create(
            company=company,
            name=f"Producto {encf}",
            description="Prueba status split",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name=f"Empresa {encf}",
            rnc=encf[-9:],
            address="Calle Status",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=200,
            next_number=2,
        )
        return ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="31",
            encf=encf,
            status=status,
            fiscal_status="draft",
            job_status="idle",
            track_id=track_id,
            xml_content="<ECF />" if signed_xml_content else "",
            signed_xml_content=signed_xml_content,
        )


class ECFStatusSplitMigrationTests(TransactionTestCase):
    """Validate legacy status inference performed by migration 0016."""

    migrate_from = [("facturacion", "0015_number_sequence")]
    migrate_to = [("facturacion", "0016_ecf_status_split_compat")]

    def test_legacy_statuses_are_inferred_and_audited(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        self._create_legacy_document(old_apps, encf="E310000001001", status="queued", track_id="track-queued", signed=True)
        self._create_legacy_document(old_apps, encf="E310000001002", status="error", signed=True)
        self._create_legacy_document(old_apps, encf="E310000001003", status="processing", track_id="track-processing", signed=True)
        self._create_legacy_document(old_apps, encf="E310000001004", status="accepted", track_id="track-accepted", signed=True)
        self._create_legacy_document(old_apps, encf="E310000001005", status="rejected", track_id="track-rejected", signed=True)
        self._create_legacy_document(old_apps, encf="E310000001006", status="cancelled", xml=True)

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        ElectronicFiscalDocumentNew = new_apps.get_model("facturacion", "ElectronicFiscalDocument")
        ECFStatusEventNew = new_apps.get_model("facturacion", "ECFStatusEvent")

        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001001", "submitted", "queued")
        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001002", "signed", "failed")
        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001003", "submitted", "idle")
        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001004", "accepted", "idle")
        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001005", "rejected", "idle")
        self._assert_migrated(ElectronicFiscalDocumentNew, "E310000001006", "xml_generated", "failed")

        self.assertEqual(ECFStatusEventNew.objects.count(), 6)
        cancelled_event = ECFStatusEventNew.objects.get(document__encf="E310000001006")
        self.assertIn("legacy_status=cancelled", cancelled_event.reason)
        self.assertIn("requires_manual_review=true", cancelled_event.reason)

        executor.migrate(self.migrate_from)
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _create_legacy_document(
        self,
        apps,
        *,
        encf: str,
        status: str,
        track_id: str | None = None,
        xml: bool = False,
        signed: bool = False,
    ):
        Invoice = apps.get_model("facturacion", "Invoice")
        ECFIssuerConfig = apps.get_model("facturacion", "ECFIssuerConfig")
        ECFSequence = apps.get_model("facturacion", "ECFSequence")
        ElectronicFiscalDocument = apps.get_model("facturacion", "ElectronicFiscalDocument")

        invoice = Invoice.objects.create(
            invoice_number=f"FAC-{encf[-8:]}",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        issuer = ECFIssuerConfig.objects.create(
            business_name=f"Empresa Legacy {encf}",
            rnc=encf[-9:],
            address="Calle Legacy",
        )
        sequence = ECFSequence.objects.create(
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=9999,
            next_number=2,
        )
        return ElectronicFiscalDocument.objects.create(
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="31",
            encf=encf,
            status=status,
            track_id=track_id,
            xml_content="<ECF />" if xml or signed else "",
            signed_xml_content="<ECF />" if signed else "",
        )

    def _assert_migrated(self, model, encf: str, fiscal_status: str, job_status: str):
        document = model.objects.get(encf=encf)
        self.assertEqual(document.fiscal_status, fiscal_status)
        self.assertEqual(document.job_status, job_status)


class ECFCertificateBackfillMigrationTests(TransactionTestCase):
    """Validate ECFCertificate backfill from legacy issuer certificate fields."""

    migrate_from = [("facturacion", "0040_ecfissuerconfig_certificate_rnc_detected_and_more")]
    migrate_to = [("facturacion", "0041_ecfcertificate")]

    def test_backfill_creates_active_certificate_from_legacy_issuer_fields(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        CompanyOld = old_apps.get_model("facturacion", "Company")
        ECFIssuerConfigOld = old_apps.get_model("facturacion", "ECFIssuerConfig")

        company = CompanyOld.objects.create(name="Empresa Legacy Cert", rnc="409999177")
        issuer = ECFIssuerConfigOld.objects.create(
            company=company,
            business_name="Empresa Legacy Cert SRL",
            rnc="101010177",
            address="Calle Legacy Cert",
            environment="testing",
            certificate_path="legacy/cert.p12",
            certificate_password="legacy-secret",
            certificate_subject="CN=Legacy",
            certificate_issuer="CN=Legacy CA",
            certificate_serial_number="123456",
            certificate_fingerprint="legacy-fingerprint",
            certificate_not_valid_before=datetime.now(timezone.utc) - timedelta(days=1),
            certificate_not_valid_after=datetime.now(timezone.utc) + timedelta(days=365),
            certificate_status="active",
            certificate_status_updated_at=datetime.now(timezone.utc),
            certificate_rnc_detected="101010177",
            certificate_rnc_match_status="matched",
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps
        ECFCertificateNew = new_apps.get_model("facturacion", "ECFCertificate")

        certificate = ECFCertificateNew.objects.get(issuer_id=issuer.id)
        self.assertEqual(certificate.company_id, company.id)
        self.assertEqual(certificate.environment, "testing")
        self.assertEqual(certificate.status, "active")
        self.assertEqual(certificate.storage_backend, "legacy_local")
        self.assertEqual(certificate.certificate_reference, "legacy/cert.p12")
        self.assertEqual(certificate.password_secret_reference, "legacy-secret")
        self.assertEqual(certificate.subject, "CN=Legacy")
        self.assertEqual(certificate.issuer_name, "CN=Legacy CA")
        self.assertEqual(certificate.serial_number, "123456")
        self.assertEqual(certificate.fingerprint, "legacy-fingerprint")
        self.assertEqual(certificate.rnc_detected, "101010177")
        self.assertEqual(certificate.rnc_match_status, "matched")
        self.assertTrue(certificate.is_active)
        self.assertIn("Backfill", certificate.notes)

        executor.migrate(self.migrate_from)
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


class ECFStatusRuntimeTransitionTests(TestCase):
    """Validate runtime writes fiscal_status/job_status without hybrid status values."""

    def test_xml_generation_changes_only_fiscal_status_and_audits(self):
        document = self._document(status="draft", fiscal_status="draft")

        ECFXMLGenerationService().generate(document, validate_xsd=False)

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "xml_generated")
        self.assertEqual(document.status, "xml_generated")
        self.assertEqual(document.job_status, "idle")
        self.assertTrue(ECFStatusEvent.objects.filter(document=document, source="xml_generation").exists())

    def test_signing_changes_only_fiscal_status_and_audits(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")

        ECFSigningService(
            certificate_loader=FakeCertificateLoader(),
            signer=FakeXMLSigner(),
            signature_validator=FakeValidator(),
            xsd_validator=FakeValidator(),
        ).sign(document, certificate_path="fake.p12", certificate_password="secret", validate_xsd=True)

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "signed")
        self.assertEqual(document.status, "signed")
        self.assertEqual(document.job_status, "idle")
        self.assertTrue(ECFStatusEvent.objects.filter(document=document, source="xml_signing").exists())

    @patch("facturacion.ecf.queues.ecf.generate_xml.apply_async")
    def test_enqueue_changes_only_job_status(self, apply_async):
        apply_async.return_value = SimpleNamespace(id="task-generate")
        document = self._document(status="draft", fiscal_status="draft")

        result = enqueue_generate_xml(document.id)

        document.refresh_from_db()
        self.assertTrue(result["enqueued"])
        self.assertEqual(document.fiscal_status, "draft")
        self.assertEqual(document.status, "draft")
        self.assertEqual(document.job_status, "queued")
        self.assertTrue(ECFStatusEvent.objects.filter(document=document, source="queue_generate_xml").exists())

    @patch("facturacion.ecf.queues.ecf.generate_xml.apply_async")
    def test_enqueue_preflight_cannot_receive_document_without_company(self, apply_async):
        document = self._document(status="draft", fiscal_status="draft")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ElectronicFiscalDocument.objects.filter(pk=document.pk).update(company=None)

        document.refresh_from_db()
        apply_async.assert_not_called()
        self.assertEqual(document.fiscal_status, "draft")
        self.assertEqual(document.status, "draft")
        self.assertEqual(document.job_status, "idle")
        self.assertIsNone(document.last_error)

    @patch("facturacion.ecf.queues.ecf.chain")
    def test_submission_pipeline_preflight_blocks_cross_company_sequence_before_enqueue(self, chain_mock):
        document = self._document(status="draft", fiscal_status="draft")
        other_company = Company.objects.create(name="Empresa Pipeline Externa", rnc="409999999")
        ECFSequence.objects.filter(pk=document.sequence_id).update(company=other_company)

        result = enqueue_submission_pipeline(document.id)

        document.refresh_from_db()
        chain_mock.assert_not_called()
        self.assertFalse(result["enqueued"])
        self.assertIn("otra empresa", result["error"])
        self.assertEqual(document.fiscal_status, "draft")
        self.assertEqual(document.status, "draft")
        self.assertEqual(document.job_status, "failed")
        self.assertIsNone(document.async_task_id)
        self.assertTrue(
            ECFStatusEvent.objects.filter(
                document=document,
                source="queue_pipeline_failed",
                previous_fiscal_status="draft",
                new_fiscal_status="draft",
                new_job_status="failed",
            ).exists()
        )

    def test_technical_failure_does_not_change_fiscal_status(self):
        document = self._document(status="signed", fiscal_status="signed", signed_xml_content="<ECF />")

        with self.assertRaises(Exception):
            check_status.apply(args=[document.id]).get()

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "signed")
        self.assertEqual(document.status, "signed")
        self.assertEqual(document.job_status, "failed")
        self.assertTrue(ECFStatusEvent.objects.filter(document=document, new_job_status="failed").exists())

    @override_settings(ECF_DGII_MOCK_ENABLED=False)
    def test_dgii_processing_keeps_fiscal_status_submitted(self):
        document = self._document(
            status="submitted",
            fiscal_status="submitted",
            signed_xml_content="<ECF />",
            track_id="track-processing",
        )

        result = DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeProcessingDGIISOAPClient,
        ).check(document)

        document.refresh_from_db()
        self.assertEqual(result.status, "submitted")
        self.assertEqual(document.fiscal_status, "submitted")
        self.assertEqual(document.status, "submitted")
        self.assertNotIn(document.status, {"queued", "pending", "processing", "error", "running", "retrying"})

    def test_terminal_reconciliation_sets_stale_job_status_to_idle(self):
        document = self._document(status="accepted", fiscal_status="accepted", track_id="track-terminal")
        document.job_status = "queued"
        document.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        document.save(update_fields=["job_status", "next_retry_at", "updated_at"])

        result = ECFJobStatusReconciliationService().reconcile_terminal_document(document)

        document.refresh_from_db()
        self.assertTrue(result.reconciled)
        self.assertEqual(result.previous_job_status, "queued")
        self.assertEqual(document.job_status, "idle")
        self.assertIsNone(document.next_retry_at)
        self.assertTrue(ECFStatusEvent.objects.filter(document=document, new_job_status="idle").exists())
        self.assertTrue(ECFEventLog.objects.filter(electronic_document=document, event_type="job_reconciled").exists())

    def test_dgii_accepted_reconciles_stale_job_status(self):
        document = self._document(
            status="submitted",
            fiscal_status="submitted",
            signed_xml_content="<ECF />",
            track_id="track-accepted-job",
        )
        document.job_status = "queued"
        document.save(update_fields=["job_status", "updated_at"])

        DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeDGIISOAPClient,
        ).check(document)

        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "accepted")
        self.assertEqual(document.job_status, "idle")

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_certificate_policy_production_blocks_missing_certificate(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_MISSING,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
        )

        result = ECFCertificateSigningPolicy().evaluate(document.issuer)

        self.assertTrue(result.blocked)
        self.assertFalse(result.allowed)
        self.assertEqual(result.code, "certificate_missing")

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_certificate_policy_production_blocks_expired_and_invalid_certificate(self):
        cases = [
            (ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED, "certificate_expired"),
            (ECFIssuerConfig.CERTIFICATE_STATUS_INVALID, "certificate_invalid"),
        ]
        for certificate_status, code in cases:
            with self.subTest(certificate_status=certificate_status):
                document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
                self._set_certificate_state(
                    document,
                    certificate_status,
                    ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
                )

                result = ECFCertificateSigningPolicy().evaluate(document.issuer)

                self.assertTrue(result.blocked)
                self.assertEqual(result.code, code)

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_certificate_policy_production_blocks_rnc_mismatch(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MISMATCH,
        )

        result = ECFCertificateSigningPolicy().evaluate(document.issuer)

        self.assertTrue(result.blocked)
        self.assertEqual(result.code, "certificate_rnc_mismatch")

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_certificate_policy_uses_active_ecf_certificate_metadata(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
        )
        ECFCertificate.objects.create(
            company=document.company,
            issuer=document.issuer,
            environment=document.issuer.environment,
            status=ECFIssuerConfig.CERTIFICATE_STATUS_INVALID,
            storage_backend=ECFCertificate.STORAGE_BACKEND_LEGACY_LOCAL,
            certificate_reference="active-invalid.p12",
            password_secret_reference="secret",
            fingerprint="active-invalid-fingerprint",
            rnc_match_status=ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
            is_active=True,
        )

        result = ECFCertificateSigningPolicy().evaluate(document.issuer)

        self.assertTrue(result.blocked)
        self.assertEqual(result.code, "certificate_invalid")

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_certificate_policy_production_allows_rnc_not_found_with_warning(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND,
        )

        result = ECFCertificateSigningPolicy().evaluate(document.issuer)

        self.assertTrue(result.allowed)
        self.assertFalse(result.blocked)
        self.assertEqual(result.code, "certificate_rnc_not_found_warning")
        self.assertTrue(result.warnings)

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=True, ECF_DGII_ENVIRONMENT="testing")
    def test_certificate_policy_testing_allows_missing_only_with_global_fallback(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_MISSING,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN,
        )

        with override_settings(ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK=False):
            blocked = ECFCertificateSigningPolicy().evaluate(document.issuer)
        with override_settings(ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK=True):
            allowed = ECFCertificateSigningPolicy().evaluate(document.issuer)

        self.assertTrue(blocked.blocked)
        self.assertEqual(blocked.code, "certificate_missing")
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.code, "certificate_missing_with_fallback")
        self.assertTrue(allowed.warnings)

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_sign_xml_policy_block_keeps_fiscal_status_and_marks_job_failed(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_MISSING,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
        )
        user = get_user_model().objects.create_superuser(username="policy-block", password="pass")
        CompanyMembership.objects.create(user=user, company=document.company, role="owner")
        request = APIRequestFactory().post(
            f"/ecf-documents/{document.id}/sign-xml/",
            {"validate_xsd": False},
            format="json",
        )
        request.session = {"active_company_id": document.company_id}
        force_authenticate(request, user=user)

        response = ElectronicFiscalDocumentViewSet.as_view({"post": "sign_xml"})(request, pk=document.id)

        document.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "certificate_missing")
        self.assertEqual(document.fiscal_status, "xml_generated")
        self.assertEqual(document.status, "xml_generated")
        self.assertEqual(document.job_status, "failed")
        self.assertIn("certificado", document.last_error.lower())
        self.assertTrue(
            ECFStatusEvent.objects.filter(
                document=document,
                source="certificate_policy_blocked",
                previous_fiscal_status="xml_generated",
                new_fiscal_status="xml_generated",
                new_job_status="failed",
            ).exists()
        )
        self.assertTrue(
            ECFEventLog.objects.filter(
                electronic_document=document,
                event_type="error",
                payload__stage="certificate_policy",
            ).exists()
        )

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    def test_sign_xml_task_policy_block_marks_job_failed_without_fiscal_change(self):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
        )

        result = sign_xml_task.apply(args=[document.id], kwargs={"validate_xsd": False}).get()

        document.refresh_from_db()
        self.assertEqual(result["job_status"], "failed")
        self.assertEqual(result["error"], "El certificado DGII está vencido. Renueve el certificado antes de firmar e-CF.")
        self.assertEqual(document.fiscal_status, "xml_generated")
        self.assertEqual(document.status, "xml_generated")
        self.assertEqual(document.job_status, "failed")
        self.assertTrue(
            ECFStatusEvent.objects.filter(
                document=document,
                source="task_sign_xml_certificate_policy_failed",
                previous_fiscal_status="xml_generated",
                new_fiscal_status="xml_generated",
                new_job_status="failed",
            ).exists()
        )
        self.assertTrue(
            ECFEventLog.objects.filter(
                electronic_document=document,
                event_type="error",
                payload__stage="certificate_policy",
                payload__code="certificate_expired",
            ).exists()
        )

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    @patch("facturacion.api.views.ecf_runtime.resolve_certificate_credentials", return_value=("cert.p12", "secret"))
    @patch("facturacion.api.views.ecf_runtime.ECFSigningService")
    def test_sign_xml_policy_warning_logs_and_continues(self, signing_service_class, _resolver):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND,
        )
        signing_service_class.return_value.sign.return_value = SimpleNamespace(
            document=document,
            signature_validated=True,
            xsd_validated=True,
        )
        user = get_user_model().objects.create_superuser(username="policy-warning", password="pass")
        CompanyMembership.objects.create(user=user, company=document.company, role="owner")
        request = APIRequestFactory().post(
            f"/ecf-documents/{document.id}/sign-xml/",
            {"validate_xsd": False},
            format="json",
        )
        request.session = {"active_company_id": document.company_id}
        force_authenticate(request, user=user)

        response = ElectronicFiscalDocumentViewSet.as_view({"post": "sign_xml"})(request, pk=document.id)

        self.assertEqual(response.status_code, 200)
        signing_service_class.return_value.sign.assert_called_once()
        self.assertTrue(
            ECFEventLog.objects.filter(
                electronic_document=document,
                event_type="warning",
                payload__stage="certificate_policy",
                payload__code="certificate_rnc_not_found_warning",
            ).exists()
        )

    @override_settings(DEBUG=False, ECF_DGII_MOCK_ENABLED=False, ECF_DGII_ENVIRONMENT="production")
    @patch("facturacion.api.views.ecf_runtime.ECFSigningService")
    def test_sign_xml_still_uses_legacy_certificate_when_no_active_ecf_certificate(self, signing_service_class):
        document = self._document(status="xml_generated", fiscal_status="xml_generated", xml_content="<ECF />")
        issuer = self._set_certificate_state(
            document,
            ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE,
            ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED,
        )
        issuer.certificate_path = "legacy-sign.p12"
        issuer.certificate_password = "legacy-sign-pass"
        issuer.certificate_fingerprint = "legacy-sign-fingerprint"
        issuer.save(update_fields=["certificate_path", "certificate_password", "certificate_fingerprint", "updated_at"])
        signing_service_class.return_value.sign.return_value = SimpleNamespace(
            document=document,
            signature_validated=True,
            xsd_validated=True,
        )
        user = get_user_model().objects.create_superuser(username="policy-legacy-sign", password="pass")
        CompanyMembership.objects.create(user=user, company=document.company, role="owner")
        request = APIRequestFactory().post(
            f"/ecf-documents/{document.id}/sign-xml/",
            {"validate_xsd": False},
            format="json",
        )
        request.session = {"active_company_id": document.company_id}
        force_authenticate(request, user=user)

        response = ElectronicFiscalDocumentViewSet.as_view({"post": "sign_xml"})(request, pk=document.id)

        self.assertEqual(response.status_code, 200)
        signing_service_class.return_value.sign.assert_called_once()
        kwargs = signing_service_class.return_value.sign.call_args.kwargs
        self.assertEqual(kwargs["certificate_path"], "legacy-sign.p12")
        self.assertEqual(kwargs["certificate_password"], "legacy-sign-pass")

    def _document(
        self,
        *,
        status: str,
        fiscal_status: str,
        xml_content: str = "",
        signed_xml_content: str = "",
        track_id: str | None = None,
    ):
        suffix = ElectronicFiscalDocument.objects.count()
        company = Company.objects.create(name=f"Empresa Runtime {suffix}", rnc=f"20202{suffix:04d}")
        category = Category.objects.create(company=company, name=f"RUNTIME-{suffix}")
        product = Product.objects.create(
            company=company,
            name=f"Producto Runtime {suffix}",
            description="Runtime",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name=f"Empresa Runtime {invoice.id}",
            rnc=f"20202{invoice.id:04d}",
            address="Calle Runtime",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=9999,
            next_number=2,
        )
        return ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="32",
            encf=f"E3200000{invoice.id:05d}",
            status=status,
            fiscal_status=fiscal_status,
            job_status="idle",
            track_id=track_id,
            xml_content=xml_content,
            signed_xml_content=signed_xml_content,
        )

    def _set_certificate_state(self, document, certificate_status: str, rnc_match_status: str):
        issuer = document.issuer
        issuer.certificate_status = certificate_status
        issuer.certificate_rnc_match_status = rnc_match_status
        issuer.certificate_status_updated_at = datetime.now(timezone.utc)
        issuer.save(
            update_fields=[
                "certificate_status",
                "certificate_rnc_match_status",
                "certificate_status_updated_at",
                "updated_at",
            ]
        )
        document.issuer = issuer
        return issuer


class FakeCertificate:
    subject = "CN=Fake"
    issuer = "CN=Fake CA"
    serial_number = "123"
    not_valid_after = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    sha256_fingerprint = "fake"


class FakeCertificateLoader:
    def load(self, certificate_path, certificate_password):
        return FakeCertificate()


class FakeXMLSigner:
    def sign(self, xml_content, certificate):
        return xml_content


class FakeValidator:
    def validate(self, *args, **kwargs):
        return None


class FakeProcessingDGIISOAPClient(FakeDGIISOAPClient):
    def query_status(self, track_id):
        return SOAPCallResult(
            result={"trackId": track_id, "estado": "En Proceso", "codigo": 3},
            request_xml="<StatusRequest />",
            response_xml="<StatusResponse />",
        )


class FakeRejectedDGIISOAPClient(FakeDGIISOAPClient):
    def query_status(self, track_id):
        return SOAPCallResult(
            result={"trackId": track_id, "estado": "Rechazado", "codigo": 2, "mensajes": [{"valor": "Firma invalida"}]},
            request_xml="<StatusRequest />",
            response_xml="<StatusResponse />",
        )


class InvoiceE2EIntegrationTests(TestCase):
    """Validate ERP invoice/sale flows create e-CF documents automatically."""

    def test_invoice_creation_service_creates_ecf_and_decrements_stock(self):
        company = Company.objects.create(name="Empresa Integrada", rnc="501010103")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(company=company)
        self._sequence(issuer)
        client = Client.objects.create(company=company, name="Cliente Final", ruc_ci="")

        result = InvoiceCreationService().create_invoice(
            client_id=client.id,
            details=[{"product": product.id, "quantity": 2, "price": Decimal("100.00")}],
            payment_method="cash",
            receipt_type="invoice",
            status="paid",
            subtotal=Decimal("200.00"),
            tax=Decimal("36.00"),
            discount=Decimal("0.00"),
            total=Decimal("236.00"),
            cash_received=Decimal("236.00"),
            change=Decimal("0.00"),
            company=company,
        )

        product.refresh_from_db()
        self.assertEqual(product.stock, 3)
        self.assertIsNotNone(result.electronic_document)
        self.assertEqual(result.electronic_document.ecf_type, "32")
        self.assertEqual(result.electronic_document.status, "draft")
        self.assertTrue(result.ecf_enqueued)

    def test_sale_flow_creates_invoice_and_ecf(self):
        company = Company.objects.create(name="Empresa Integrada Sale", rnc="501010104")
        product = self._product(stock=4, company=company)
        issuer = self._issuer(company=company, rnc="101010104")
        self._sequence(issuer)

        result = InvoiceCreationService().create_sale_with_invoice(
            customer="Consumidor Final",
            details=[{"product": product.id, "quantity": 1, "price": Decimal("50.00")}],
            company=company,
        )

        product.refresh_from_db()
        self.assertEqual(product.stock, 3)
        self.assertEqual(result.invoice.status, "paid")
        self.assertEqual(result.sale.details.count(), 1)
        self.assertIsNotNone(result.electronic_document)

    def _product(self, stock=10, company=None):
        category = Category.objects.create(company=company, name=f"CAT-{stock}")
        return Product.objects.create(
            company=company,
            name=f"Producto {stock}",
            description="Producto prueba",
            price=Decimal("100.00"),
            stock=stock,
            category=category,
        )

    def _issuer(self, company=None, rnc="101010103"):
        company = company or Company.objects.first() or Company.objects.create(name="Empresa Integrada", rnc="501010103")
        return ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Integrada SRL",
            rnc=rnc,
            address="Calle Integracion",
        )

    def _sequence(self, issuer):
        return ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=20,
            next_number=1,
        )


class InvoiceAPIContractTests(TestCase):
    """Validate the official Invoice API contract used by commercial screens."""

    def _company_for_user(self, user, name="Empresa Invoice Contract"):
        company = Company.objects.create(name=name, rnc=f"20{Company.objects.count():07d}")
        CompanyMembership.objects.create(user=user, company=company, role="admin")
        return company

    def test_invoice_list_supports_minimum_commercial_filters(self):
        user = get_user_model().objects.create_superuser(
            username="invoice-contract-admin",
            email="invoice-contract-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user)
        client = Client.objects.create(company=company, name="Cliente Contrato", ruc_ci="131333333")
        matching = Invoice.objects.create(
            company=company,
            client=client,
            invoice_number="FAC-CONTRACT-001",
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        other = Invoice.objects.create(
            company=company,
            invoice_number="FAC-OTHER-001",
            subtotal=Decimal("50.00"),
            tax=Decimal("9.00"),
            discount=Decimal("0.00"),
            total=Decimal("59.00"),
            status="pending",
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Contrato SRL",
            rnc="101010196",
            address="Calle Contrato",
        )
        sequence = ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=2,
        )
        ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=matching,
            issuer=issuer,
            sequence=sequence,
            ecf_type="32",
            encf="E320000000196",
            status="accepted",
            fiscal_status="accepted",
        )
        ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=other,
            issuer=issuer,
            sequence=sequence,
            ecf_type="32",
            encf="E320000000197",
            status="draft",
            fiscal_status="draft",
        )

        self.assertEqual(Invoice.objects.filter(client_id=client.id).count(), 1)
        self.assertEqual(Invoice.objects.filter(invoice_number__icontains="CONTRACT").count(), 1)
        self.assertEqual(Invoice.objects.filter(electronic_document__fiscal_status="accepted").count(), 1)
        request = APIRequestFactory().get(
            "/invoices/",
            {
                "client": client.id,
                "invoice_number": "CONTRACT",
                "fiscal_status": "accepted",
            },
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], matching.id)

    def test_invoice_list_paginates_when_requested(self):
        user = get_user_model().objects.create_superuser(
            username="invoice-pagination-admin",
            email="invoice-pagination-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Invoice Pagination")
        Invoice.objects.create(
            company=company,
            invoice_number="FAC-PAGE-001",
            subtotal=Decimal("10.00"),
            tax=Decimal("1.80"),
            discount=Decimal("0.00"),
            total=Decimal("11.80"),
            status="paid",
        )
        Invoice.objects.create(
            company=company,
            invoice_number="FAC-PAGE-002",
            subtotal=Decimal("20.00"),
            tax=Decimal("3.60"),
            discount=Decimal("0.00"),
            total=Decimal("23.60"),
            status="paid",
        )

        request = APIRequestFactory().get("/invoices/", {"page": 1, "page_size": 1})
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_pos_invoice_without_client_name_or_rnc_uses_final_consumer_e32(self):
        user = get_user_model().objects.create_superuser(
            username="pos-invoice-final-consumer-admin",
            email="pos-invoice-final-consumer-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa POS Consumidor Final")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010196", company=company)
        self._sequence(issuer, ecf_type="32")

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "client_id": None,
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "cash_received": "120.00",
                "change": "2.00",
                "details": [{"product_id": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        invoice = Invoice.objects.get(pk=response.data["id"])
        document = invoice.electronic_document
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "paid")
        self.assertEqual(response.data["ecf_type"], "32")
        self.assertEqual(invoice.status, "paid")
        self.assertIsNone(invoice.client_id)
        self.assertEqual(document.ecf_type, "32")
        self.assertIn(document.fiscal_status, {"draft", "submitted", "accepted"})
        self.assertEqual(product.stock, 4)
        self.assertEqual(Sale.objects.count(), 0)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_pos_invoice_payload_with_pending_status_is_forced_to_paid(self):
        user = get_user_model().objects.create_superuser(
            username="pos-invoice-force-paid-admin",
            email="pos-invoice-force-paid-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa POS Force Paid")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010183", company=company)
        self._sequence(issuer, ecf_type="32")

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "status": "pending",
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "cash_received": "120.00",
                "change": "2.00",
                "details": [{"product_id": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        invoice = Invoice.objects.get(pk=response.data["id"])
        document = invoice.electronic_document
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "paid")
        self.assertEqual(invoice.status, "paid")
        self.assertEqual(document.ecf_type, "32")
        self.assertEqual(document.fiscal_status, "draft")
        self.assertEqual(product.stock, 4)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_pos_invoice_payload_without_rnc_creates_paid_e32_without_sale(self):
        user = get_user_model().objects.create_superuser(
            username="pos-invoice-e32-admin",
            email="pos-invoice-e32-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa POS E32")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010195", company=company)
        self._sequence(issuer, ecf_type="32")

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "customer_name": "Nombre libre",
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "cash_received": "120.00",
                "change": "2.00",
                "details": [{"product_id": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        invoice = Invoice.objects.get(pk=response.data["id"])
        document = invoice.electronic_document
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ecf_type"], "32")
        self.assertEqual(invoice.status, "paid")
        self.assertIsNone(invoice.client_id)
        self.assertIn("Nombre libre", invoice.notes)
        self.assertEqual(document.ecf_type, "32")
        self.assertEqual(product.stock, 4)
        self.assertEqual(Sale.objects.count(), 0)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_pos_invoice_payload_with_direct_rnc_creates_e31_without_sale(self):
        user = get_user_model().objects.create_superuser(
            username="pos-invoice-e31-admin",
            email="pos-invoice-e31-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa POS E31")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010194", company=company)
        self._sequence(issuer, ecf_type="31")

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "customer_name": "Cliente Fiscal Directo",
                "customer_rnc": "131222222",
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "cash_received": "120.00",
                "change": "2.00",
                "details": [{"product_id": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        invoice = Invoice.objects.get(pk=response.data["id"])
        document = invoice.electronic_document
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "paid")
        self.assertEqual(response.data["ecf_type"], "31")
        self.assertEqual(invoice.status, "paid")
        self.assertEqual(invoice.client.ruc_ci, "131222222")
        self.assertEqual(invoice.client.client_type, "occasional")
        self.assertEqual(document.ecf_type, "31")
        self.assertEqual(product.stock, 4)
        self.assertEqual(Sale.objects.count(), 0)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_pos_invoice_payload_with_invalid_direct_rnc_is_rejected(self):
        user = get_user_model().objects.create_superuser(
            username="pos-invoice-invalid-rnc-admin",
            email="pos-invoice-invalid-rnc-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa POS RNC Invalido")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010184", company=company)
        self._sequence(issuer, ecf_type="31")

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "source": "pos",
                "customer_name": "Cliente Fiscal Invalido",
                "customer_rnc": "ABC123",
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "cash_received": "120.00",
                "change": "2.00",
                "details": [{"product_id": product.id, "quantity": 1, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(product.stock, 5)
        self.assertEqual(Invoice.objects.filter(company=company).count(), 0)
        self.assertEqual(Sale.objects.count(), 0)

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_manual_invoice_does_not_auto_emit_or_decrement_stock(self):
        user = get_user_model().objects.create_superuser(
            username="manual-invoice-draft-admin",
            email="manual-invoice-draft-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Manual Factura")
        product = self._product(stock=5, company=company)

        request = APIRequestFactory().post(
            "/invoices/",
            {
                "status": "paid",
                "payment_method": "cash",
                "receipt_type": "invoice",
                "subtotal": "100.00",
                "tax": "18.00",
                "discount": "0.00",
                "total": "118.00",
                "details": [{"product_id": product.id, "quantity": 2, "price": "100.00"}],
            },
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = InvoiceViewSet.as_view({"post": "create"})(request)

        product.refresh_from_db()
        invoice = Invoice.objects.get(pk=response.data["id"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(invoice.status, "pending")
        self.assertIsNone(invoice.inventory_committed_at)
        self.assertEqual(product.stock, 5)
        self.assertFalse(ElectronicFiscalDocument.objects.filter(invoice=invoice).exists())
        self.assertTrue(response.data["can_collect"])

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_manual_invoice_can_be_edited_before_collecting(self):
        user = get_user_model().objects.create_superuser(
            username="manual-invoice-edit-admin",
            email="manual-invoice-edit-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Manual Editable")
        product = self._product(stock=5, company=company)
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )

        request = APIRequestFactory().patch(
            f"/invoices/{invoice.id}/",
            {"notes": "Nota antes de emitir"},
            format="json",
        )
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = InvoiceViewSet.as_view({"patch": "partial_update"})(request, pk=invoice.id)

        invoice.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice.notes, "Nota antes de emitir")

    @override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
    def test_collect_manual_invoice_decrements_stock_and_creates_ecf_once(self):
        user = get_user_model().objects.create_superuser(
            username="manual-invoice-collect-admin",
            email="manual-invoice-collect-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Manual Cobro")
        product = self._product(stock=5, company=company)
        issuer = self._issuer(rnc="101010185", company=company)
        self._sequence(issuer, ecf_type="32")
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("200.00"),
            tax=Decimal("36.00"),
            discount=Decimal("0.00"),
            total=Decimal("236.00"),
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=2,
            price=Decimal("100.00"),
            subtotal=Decimal("200.00"),
        )

        request = APIRequestFactory().post(f"/invoices/{invoice.id}/collect/", {}, format="json")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)

        response = InvoiceViewSet.as_view({"post": "collect"})(request, pk=invoice.id)
        product.refresh_from_db()
        invoice.refresh_from_db()
        document = invoice.electronic_document

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invoice.status, "paid")
        self.assertIsNotNone(invoice.inventory_committed_at)
        self.assertEqual(product.stock, 3)
        self.assertEqual(document.ecf_type, "32")

        second_request = APIRequestFactory().post(f"/invoices/{invoice.id}/collect/", {}, format="json")
        second_request.session = {"active_company_id": company.id}
        force_authenticate(second_request, user=user)
        second_response = InvoiceViewSet.as_view({"post": "collect"})(second_request, pk=invoice.id)

        product.refresh_from_db()
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(product.stock, 3)
        self.assertEqual(ElectronicFiscalDocument.objects.filter(invoice=invoice).count(), 1)

    def _product(self, stock=10, company=None):
        category = Category.objects.create(company=company, name=f"INVOICE-API-{stock}-{Product.objects.count()}")
        return Product.objects.create(
            company=company,
            name=f"Producto Invoice API {stock}",
            description="Producto invoice api",
            price=Decimal("100.00"),
            stock=stock,
            category=category,
        )

    def _issuer(self, rnc="101010193", company=None):
        company = company or Company.objects.first() or Company.objects.create(name="Empresa Invoice API", rnc="501010193")
        return ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Invoice API SRL",
            rnc=rnc,
            address="Calle Invoice API",
        )

    def _sequence(self, issuer, ecf_type="32"):
        return ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type=ecf_type,
            start_number=1,
            end_number=10,
            next_number=1,
        )


@override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
class SaleLegacyAdapterTests(TestCase):
    """Validate Sale legacy paths delegate commercial creation to invoices."""

    def assert_legacy_sale_deprecation(self, response):
        self.assertEqual(response["Deprecation"], "true")
        self.assertEqual(response["Sunset-Phase"], "2A-legacy-sale-removal")
        self.assertTrue(response.data["deprecated"])
        self.assertEqual(response.data["replacement"], "/api/v1/invoices/")
        self.assertEqual(response.data["removal_phase"], "2A-final-cleanup")

    def test_sale_serializer_create_uses_invoice_service_and_decrements_stock_once(self):
        product = self._product(stock=5)
        self._sequence(self._issuer())
        user = get_user_model().objects.create_superuser(
            username="legacy-serializer-admin",
            email="legacy-serializer-admin@example.test",
            password="test-pass",
        )
        CompanyMembership.objects.create(user=user, company=product.company, role="admin")
        request = APIRequestFactory().post("/sales/")
        request.session = {"active_company_id": product.company_id}
        request.user = user
        force_authenticate(request, user=user)

        serializer = SaleSerializer(
            data={
                "customer": "Cliente Legacy",
                "details": [
                    {"product_id": product.id, "quantity": 2, "price": "75.00"},
                ],
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        sale = serializer.save()

        product.refresh_from_db()
        self.assertEqual(product.stock, 3)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(sale.details.count(), 1)

    def test_sale_create_view_delegates_to_invoice_service_without_double_stock_mutation(self):
        product = self._product(stock=5)
        self._sequence(self._issuer())
        user = get_user_model().objects.create_superuser(
            username="legacy-pos-admin",
            email="legacy-pos-admin@example.test",
            password="test-pass",
        )
        CompanyMembership.objects.create(user=user, company=product.company, role="admin")

        request = APIRequestFactory().post(
            "/sales/",
            {
                "customer": "Mostrador",
                "details": [
                    {"product_id": product.id, "quantity": 2, "price": "50.00"},
                ],
            },
            format="json",
        )
        request.session = {"active_company_id": product.company_id}
        force_authenticate(request, user=user)
        response = SaleCreateView.as_view()(request)

        product.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(product.stock, 3)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertIn("invoice_id", response.data)
        self.assert_legacy_sale_deprecation(response)

    def test_sales_list_legacy_response_has_deprecation_contract(self):
        product = self._product(stock=5)
        self._sequence(self._issuer())
        user = get_user_model().objects.create_superuser(
            username="legacy-list-admin",
            email="legacy-list-admin@example.test",
            password="test-pass",
        )
        InvoiceCreationService().create_sale_with_invoice(
            customer="Consumidor Final",
            details=[{"product": product.id, "quantity": 1, "price": Decimal("50.00")}],
            company=product.company,
        )

        request = APIRequestFactory().get("/sales/list/")
        force_authenticate(request, user=user)
        response = SaleListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assert_legacy_sale_deprecation(response)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_sale_pos_without_client_uses_e32_consumidor_final(self):
        product = self._product(stock=5)
        issuer = self._issuer(rnc="101010198")
        self._sequence(issuer, ecf_type="32")

        result = InvoiceCreationService().create_sale_with_invoice(
            customer="Nombre libre",
            details=[{"product": product.id, "quantity": 1, "price": Decimal("50.00")}],
            company=product.company,
        )

        self.assertIsNone(result.invoice.client_id)
        self.assertEqual(result.electronic_document.ecf_type, "32")
        self.assertEqual(result.sale.customer, "Nombre libre")

    def test_sale_pos_with_rnc_client_uses_e31_and_links_invoice_client(self):
        product = self._product(stock=5)
        issuer = self._issuer(rnc="101010197")
        self._sequence(issuer, ecf_type="31")
        client = Client.objects.create(company=product.company, name="Cliente Fiscal", ruc_ci="131222222")

        result = InvoiceCreationService().create_sale_with_invoice(
            customer=client.name,
            client_id=client.id,
            details=[{"product": product.id, "quantity": 1, "price": Decimal("50.00")}],
            company=product.company,
        )

        self.assertEqual(result.invoice.client_id, client.id)
        self.assertEqual(result.electronic_document.ecf_type, "31")
        self.assertEqual(result.sale.customer, "Cliente Fiscal")

    def test_sales_update_delete_legacy_delete_is_blocked_and_does_not_mutate_stock(self):
        product = self._product(stock=5)
        self._sequence(self._issuer())
        user = get_user_model().objects.create_superuser(
            username="legacy-delete-admin",
            email="legacy-delete-admin@example.test",
            password="test-pass",
        )
        sale = InvoiceCreationService().create_sale_with_invoice(
            customer="Consumidor Final",
            details=[{"product": product.id, "quantity": 2, "price": Decimal("50.00")}],
            company=product.company,
        ).sale
        product.refresh_from_db()
        self.assertEqual(product.stock, 3)

        request = APIRequestFactory().delete(f"/salesUpdate/{sale.id}/")
        force_authenticate(request, user=user)
        response = SalesUpdateDeleteView.as_view()(request, pk=sale.id)

        product.refresh_from_db()
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["code"], "sale_legacy_read_only")
        self.assert_legacy_sale_deprecation(response)
        self.assertEqual(product.stock, 3)
        self.assertTrue(Sale.objects.filter(pk=sale.id).exists())

    def test_sales_update_delete_legacy_update_is_blocked(self):
        product = self._product(stock=5)
        self._sequence(self._issuer())
        user = get_user_model().objects.create_superuser(
            username="legacy-update-admin",
            email="legacy-update-admin@example.test",
            password="test-pass",
        )
        sale = InvoiceCreationService().create_sale_with_invoice(
            customer="Consumidor Final",
            details=[{"product": product.id, "quantity": 1, "price": Decimal("50.00")}],
            company=product.company,
        ).sale

        request = APIRequestFactory().put(
            f"/salesUpdate/{sale.id}/",
            {"customer": "Editado", "details": []},
            format="json",
        )
        force_authenticate(request, user=user)
        response = SalesUpdateDeleteView.as_view()(request, pk=sale.id)

        sale.refresh_from_db()
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.data["code"], "sale_legacy_read_only")
        self.assert_legacy_sale_deprecation(response)
        self.assertEqual(sale.customer, "Consumidor Final")

    def _product(self, stock=10):
        company = self._company()
        category = Category.objects.create(company=company, name=f"SALE-LEGACY-{stock}")
        return Product.objects.create(
            company=company,
            name=f"Producto Legacy {stock}",
            description="Producto prueba legacy",
            price=Decimal("100.00"),
            stock=stock,
            category=category,
        )

    def _issuer(self, rnc="101010199"):
        return ECFIssuerConfig.objects.create(
            company=self._company(),
            business_name="Empresa Legacy Adapter SRL",
            rnc=rnc,
            address="Calle Legacy Adapter",
        )

    def _sequence(self, issuer, ecf_type="32"):
        return ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type=ecf_type,
            start_number=1,
            end_number=20,
            next_number=1,
        )

    def _company(self):
        if not hasattr(self, "_legacy_company"):
            self._legacy_company = Company.objects.create(name="Empresa Legacy Adapter", rnc="501010199")
        return self._legacy_company


class DashboardInvoiceReportingTests(TestCase):
    """Validate commercial dashboard metrics use Invoice as source of truth."""

    def _company_for_user(self, user, name="Empresa Dashboard"):
        company = Company.objects.create(name=name, rnc=f"30{Company.objects.count():07d}")
        CompanyMembership.objects.create(user=user, company=company, role="admin")
        return company

    def _grant(self, user, model, codename):
        content_type = ContentType.objects.get_for_model(model)
        permission = Permission.objects.get(content_type=content_type, codename=codename)
        user.user_permissions.add(permission)

    def _grant_dashboard_access(self, user):
        self._grant(user, Invoice, "view_invoice")
        self._grant(user, Product, "view_product")

    def _build_invoice_fixture(self, company):
        category = Category.objects.create(company=company, name="Dashboard")
        product = Product.objects.create(
            company=company,
            name="Producto Dashboard",
            description="Reporte",
            price=Decimal("50.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente Dashboard", ruc_ci="")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=2,
            price=Decimal("50.00"),
            subtotal=Decimal("100.00"),
        )
        return client, invoice, product

    def test_dashboard_uses_invoice_metrics_and_ignores_sale_legacy_totals(self):
        user = get_user_model().objects.create_superuser(
            username="dashboard-invoice-admin",
            email="dashboard-invoice-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Dashboard Principal")
        category = Category.objects.create(company=company, name="Dashboard")
        product = Product.objects.create(
            company=company,
            name="Producto Dashboard",
            description="Reporte",
            price=Decimal("50.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente Dashboard", ruc_ci="")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=2,
            price=Decimal("50.00"),
            subtotal=Decimal("100.00"),
        )
        legacy_sale = Sale.objects.create(customer="Legacy", total=Decimal("999.00"))
        SaleDetail.objects.create(
            sale=legacy_sale,
            product=product,
            quantity=9,
            price=Decimal("111.00"),
        )

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["salesSummary"]["total_sales"], 118.0)
        self.assertEqual(response.data["salesSummary"]["sales_count"], 1)
        self.assertEqual(response.data["salesSummary"]["products_sold"], 2)
        self.assertEqual(response.data["topProducts"][0]["name"], "Producto Dashboard")
        self.assertEqual(response.data["topProducts"][0]["quantity"], 2)
        self.assertEqual(response.data["recentSales"][0]["id"], invoice.id)
        self.assertEqual(response.data["recentSales"][0]["customer"], "Cliente Dashboard")

    def test_dashboard_separates_paid_pending_and_fiscal_accepted_metrics(self):
        user = get_user_model().objects.create_superuser(
            username="dashboard-separated-admin",
            email="dashboard-separated-admin@example.test",
            password="test-pass",
        )
        company = self._company_for_user(user, name="Empresa Dashboard Separada")
        category = Category.objects.create(company=company, name="Dashboard Separado")
        product = Product.objects.create(
            company=company,
            name="Producto Dashboard Separado",
            description="Reporte",
            price=Decimal("50.00"),
            stock=10,
            category=category,
        )
        paid_invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=paid_invoice,
            product=product,
            quantity=2,
            price=Decimal("50.00"),
            subtotal=Decimal("100.00"),
        )
        pending_invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("200.00"),
            tax=Decimal("36.00"),
            discount=Decimal("0.00"),
            total=Decimal("236.00"),
            status="pending",
        )
        InvoiceDetail.objects.create(
            invoice=pending_invoice,
            product=product,
            quantity=4,
            price=Decimal("50.00"),
            subtotal=Decimal("200.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Dashboard Separada SRL",
            rnc="101010186",
            address="Calle Dashboard",
        )
        sequence = ECFSequence.objects.create(
            company=company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=20,
            next_number=2,
        )
        ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=paid_invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="32",
            encf="E320000000001",
            status="accepted",
            fiscal_status="accepted",
        )

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["salesSummary"]["total_sales"], 118.0)
        self.assertEqual(response.data["salesSummary"]["sales_count"], 1)
        self.assertEqual(response.data["salesSummary"]["products_sold"], 2)
        self.assertEqual(response.data["salesSummary"]["accounts_receivable_total"], 236.0)
        self.assertEqual(response.data["salesSummary"]["accounts_receivable_count"], 1)
        self.assertEqual(response.data["salesSummary"]["accepted_fiscal_total"], 118.0)
        self.assertEqual(response.data["salesSummary"]["accepted_fiscal_count"], 1)
        self.assertEqual(response.data["salesSummary"]["total_invoices_count"], 2)
        self.assertEqual(response.data["topProducts"][0]["quantity"], 2)
        self.assertEqual([item["id"] for item in response.data["recentSales"]], [paid_invoice.id])

    def test_dashboard_accepts_financial_totals_permission(self):
        user = get_user_model().objects.create_user(username="financial-dashboard")
        company = self._company_for_user(user, name="Empresa Dashboard Financial")
        self._grant_dashboard_access(user)
        self._grant(user, Invoice, "view_financial_totals")
        self._build_invoice_fixture(company)

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["salesSummary"]["total_sales"], 118.0)

    def test_dashboard_accepts_legacy_sale_totals_permission(self):
        user = get_user_model().objects.create_user(username="legacy-dashboard")
        company = self._company_for_user(user, name="Empresa Dashboard Legacy")
        self._grant_dashboard_access(user)
        self._grant(user, Sale, "view_sale_totals")
        self._build_invoice_fixture(company)

        request = APIRequestFactory().get("/dashboard/")
        request.session = {"active_company_id": company.id}
        force_authenticate(request, user=user)
        response = DashboardView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["salesSummary"]["total_sales"], 118.0)

    def test_client_serializer_uses_financial_totals_permission(self):
        user = get_user_model().objects.create_user(username="client-financial")
        company = self._company_for_user(user, name="Empresa Client Financial")
        self._grant(user, Invoice, "view_financial_totals")
        client, _, _ = self._build_invoice_fixture(company)

        request = APIRequestFactory().get("/clients/")
        request.user = user
        data = ClientSerializer(client, context={"request": request}).data

        self.assertEqual(data["total_spent"], Decimal("118.00"))

    def test_client_serializer_hides_total_without_financial_permission(self):
        user = get_user_model().objects.create_user(username="client-no-financial")
        company = self._company_for_user(user, name="Empresa Client Hidden")
        client, _, _ = self._build_invoice_fixture(company)

        request = APIRequestFactory().get("/clients/")
        request.user = user
        data = ClientSerializer(client, context={"request": request}).data

        self.assertIsNone(data["total_spent"])

    def test_sales_legacy_serializer_accepts_financial_totals_permission(self):
        user = get_user_model().objects.create_user(username="sale-financial")
        company = self._company_for_user(user, name="Empresa Sale Financial")
        self._grant(user, Invoice, "view_financial_totals")
        _, _, product = self._build_invoice_fixture(company)
        sale = Sale.objects.create(customer="Legacy", total=Decimal("50.00"))
        SaleDetail.objects.create(
            sale=sale,
            product=product,
            quantity=1,
            price=Decimal("50.00"),
        )

        request = APIRequestFactory().get("/sales/list/")
        request.user = user
        data = SaleListSerializer(sale, context={"request": request}).data

        self.assertEqual(data["total"], "50.00")
        self.assertEqual(data["details"][0]["price"], "50.00")


@override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
class QuotationERPFlowTests(TestCase):
    """Validate quotations are commercial-only until converted to invoices."""

    def test_quotation_does_not_create_ecf_or_decrement_stock(self):
        product = self._product(stock=5)
        client = Client.objects.create(company=product.company, name="Cliente Cotizacion", ruc_ci="")

        result = QuotationService().create_quotation(
            client_id=client.id,
            customer_name=None,
            details=[{"product": product.id, "quantity": 2, "price": Decimal("100.00")}],
            discount=Decimal("0.00"),
            notes="Cotizacion no fiscal",
            company=product.company,
        )

        product.refresh_from_db()
        self.assertEqual(product.stock, 5)
        self.assertEqual(result.quotation.status, "draft")
        self.assertEqual(result.quotation.details.count(), 1)
        self.assertEqual(Quotation.objects.count(), 1)
        self.assertEqual(ElectronicFiscalDocument.objects.count(), 0)

    def test_approved_quotation_converts_to_pending_manual_invoice_then_collects(self):
        product = self._product(stock=5)
        client = Client.objects.create(company=product.company, name="Cliente Conversion", ruc_ci="")
        issuer = ECFIssuerConfig.objects.create(
            company=product.company,
            business_name="Empresa Cotizacion SRL",
            rnc="101010188",
            address="Calle Cotizacion",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=20,
            next_number=1,
        )
        service = QuotationService()
        quote = service.create_quotation(
            client_id=client.id,
            customer_name=None,
            details=[{"product": product.id, "quantity": 2, "price": Decimal("100.00")}],
            discount=Decimal("0.00"),
            company=product.company,
        ).quotation
        service.approve(quote.id)

        result = service.convert_to_invoice(
            quotation_id=quote.id,
            issuer_id=issuer.id,
            status="paid",
            cash_received=Decimal("236.00"),
            change=Decimal("0.00"),
        )

        product.refresh_from_db()
        quote.refresh_from_db()
        self.assertEqual(product.stock, 5)
        self.assertIsNotNone(quote.converted_at)
        self.assertEqual(result.invoice.origin_quotation_id, quote.id)
        self.assertEqual(result.invoice.status, "pending")
        self.assertIsNone(result.invoice.inventory_committed_at)
        self.assertEqual(result.invoice.details.count(), 1)
        self.assertIsNone(result.electronic_document)
        self.assertFalse(result.ecf_enqueued)
        self.assertEqual(ElectronicFiscalDocument.objects.count(), 0)

        collected = InvoiceCreationService().collect_and_issue_invoice(
            invoice_id=result.invoice.id,
            issuer_id=issuer.id,
            ecf_type="32",
        )
        product.refresh_from_db()
        collected.invoice.refresh_from_db()
        self.assertEqual(product.stock, 3)
        self.assertEqual(collected.invoice.status, "paid")
        self.assertIsNotNone(collected.invoice.inventory_committed_at)
        self.assertIsNotNone(collected.electronic_document)
        self.assertEqual(collected.electronic_document.ecf_type, "32")

    def _product(self, stock=10):
        company = Company.objects.create(name=f"Empresa Quote ERP {stock}", rnc=f"4010101{stock:02d}")
        category = Category.objects.create(company=company, name=f"QUOTE-CAT-{stock}")
        return Product.objects.create(
            company=company,
            name=f"Producto Cotizacion {stock}",
            description="Producto quote",
            price=Decimal("100.00"),
            stock=stock,
            category=category,
        )


class E34FiscalValidationTests(TestCase):
    """Validate E34 credit note creation, XML serialization and XSD coverage."""

    def test_e34_credit_note_generates_xsd_valid_reference_xml(self):
        user = get_user_model().objects.create_superuser(
            username="fiscal-admin",
            email="fiscal-admin@example.test",
            password="test-pass",
        )
        invoice, origin_document, detail = self._accepted_origin_invoice()
        ECFSequence.objects.create(
            company=origin_document.issuer.company,
            issuer=origin_document.issuer,
            ecf_type="34",
            start_number=1,
            end_number=20,
            next_number=1,
        )

        with patch("facturacion.services.credit_notes.enqueue_submission_pipeline") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                result = CreditNoteService().create_credit_note(
                    origin_invoice_id=invoice.id,
                    details=[{"origin_detail": detail.id, "quantity": 1}],
                    reason="Devolucion parcial por ajuste operativo",
                    user=user,
                )
        xml_result = ECFXMLGenerationService().generate(result.electronic_document, user=user, validate_xsd=True)

        self.assertEqual(result.electronic_document.ecf_type, "34")
        self.assertTrue(result.ecf_enqueued)
        enqueue.assert_called_once_with(result.electronic_document.id, user_id=user.id, validate_xsd=True)
        self.assertIn("<IndicadorNotaCredito>0</IndicadorNotaCredito>", xml_result.xml_content)
        self.assertIn("<InformacionReferencia>", xml_result.xml_content)
        self.assertIn(f"<NCFModificado>{origin_document.encf}</NCFModificado>", xml_result.xml_content)
        ECFXSDValidator().validate("34", xml_result.xml_content)

    def test_e34_requires_origin_invoice_accepted_by_dgii(self):
        user = get_user_model().objects.create_superuser(
            username="strict-admin",
            email="strict-admin@example.test",
            password="test-pass",
        )
        blocked_statuses = ["draft", "xml_generated", "signed", "submitted", "rejected"]

        for fiscal_status in blocked_statuses:
            invoice, origin_document, detail = self._accepted_origin_invoice(quantity=3)
            origin_document.fiscal_status = fiscal_status
            origin_document.status = fiscal_status
            origin_document.save(update_fields=["fiscal_status", "status", "updated_at"])
            ECFSequence.objects.create(
                company=origin_document.issuer.company,
                issuer=origin_document.issuer,
                ecf_type="34",
                start_number=10,
                end_number=20,
                next_number=10,
            )

            with self.assertRaisesMessage(ValueError, "aceptado por DGII"):
                CreditNoteService().create_credit_note(
                    origin_invoice_id=invoice.id,
                    details=[{"origin_detail": detail.id, "quantity": 1}],
                    reason="Intento no permitido",
                    user=user,
                )

    def test_e34_inventory_restore_is_idempotent_and_audited(self):
        user = get_user_model().objects.create_superuser(
            username="inventory-admin",
            email="inventory-admin@example.test",
            password="test-pass",
        )
        invoice, origin_document, detail = self._accepted_origin_invoice(quantity=3)
        product = detail.product
        ECFSequence.objects.create(
            company=origin_document.issuer.company,
            issuer=origin_document.issuer,
            ecf_type="34",
            start_number=30,
            end_number=40,
            next_number=30,
        )

        with patch("facturacion.services.credit_notes.enqueue_submission_pipeline"):
            result = CreditNoteService().create_credit_note(
                origin_invoice_id=invoice.id,
                details=[{"origin_detail": detail.id, "quantity": 1}],
                reason="Restauracion idempotente",
                user=user,
            )

        note = result.credit_note
        note.refresh_from_db()
        product.refresh_from_db()
        self.assertIsNotNone(note.inventory_restored_at)
        self.assertEqual(product.stock, 11)
        self.assertTrue(
            ECFEventLog.objects.filter(
                electronic_document=result.electronic_document,
                event_type="inventory_restored",
            ).exists()
        )

        restored_again = CreditNoteService()._restore_inventory_once(
            note,
            [
                {
                    "origin_detail": detail,
                    "product": product,
                    "quantity": 1,
                }
            ],
            result.electronic_document,
            user=user,
        )

        product.refresh_from_db()
        self.assertFalse(restored_again)
        self.assertEqual(product.stock, 11)

    def test_new_reversals_are_blocked_while_e34_is_pending(self):
        user = get_user_model().objects.create_superuser(
            username="reverse-admin",
            email="reverse-admin@example.test",
            password="test-pass",
        )
        invoice, origin_document, detail = self._accepted_origin_invoice(quantity=2)
        ECFSequence.objects.create(
            company=origin_document.issuer.company,
            issuer=origin_document.issuer,
            ecf_type="34",
            start_number=50,
            end_number=80,
            next_number=50,
        )

        with patch("facturacion.services.credit_notes.enqueue_submission_pipeline"):
            CreditNoteService().create_credit_note(
                origin_invoice_id=invoice.id,
                details=[{"origin_detail": detail.id, "quantity": 1}],
                reason="Reverso parcial pendiente",
                user=user,
            )
            with self.assertRaisesMessage(ValueError, "pendiente o rechazada sin resolver"):
                CreditNoteService().create_credit_note(
                    origin_invoice_id=invoice.id,
                    details=[{"origin_detail": detail.id, "quantity": 1}],
                    reason="Reverso bloqueado",
                    user=user,
                )

        self.assertEqual(CreditNote.objects.filter(origin_invoice=invoice).count(), 1)

    def test_e34_accepted_confirms_inventory_reconciliation(self):
        user = get_user_model().objects.create_superuser(
            username="accepted-e34-admin",
            email="accepted-e34-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, _detail, result = self._created_e34(user, quantity=3)
        document = result.electronic_document
        document.fiscal_status = "submitted"
        document.status = "submitted"
        document.track_id = "track-e34-accepted"
        document.save(update_fields=["fiscal_status", "status", "track_id", "updated_at"])

        DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeDGIISOAPClient,
        ).check(document, user=user)

        note = result.credit_note
        note.refresh_from_db()
        self.assertEqual(note.fiscal_resolution_status, "confirmed")
        self.assertEqual(note.inventory_reconciliation_status, "confirmed")
        self.assertIsNotNone(note.inventory_reconciled_at)
        self.assertFalse(note.requires_manual_review)

    @override_settings(ECF_DGII_MOCK_ENABLED=False)
    def test_e34_rejected_requires_review_and_can_be_compensated_once(self):
        user = get_user_model().objects.create_superuser(
            username="rejected-e34-admin",
            email="rejected-e34-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, detail, result = self._created_e34(user, quantity=3)
        product = detail.product
        document = result.electronic_document
        document.fiscal_status = "submitted"
        document.status = "submitted"
        document.track_id = "track-e34-rejected"
        document.save(update_fields=["fiscal_status", "status", "track_id", "updated_at"])

        DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeRejectedDGIISOAPClient,
        ).check(document, user=user)

        note = result.credit_note
        note.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(note.fiscal_resolution_status, "rejected")
        self.assertEqual(note.inventory_reconciliation_status, "compensation_required")
        self.assertTrue(note.requires_manual_review)
        self.assertEqual(product.stock, 11)

        first = CreditNoteReconciliationService().compensate_inventory(note, user=user)
        product.refresh_from_db()
        self.assertTrue(first.changed)
        self.assertEqual(product.stock, 10)

        second = CreditNoteReconciliationService().compensate_inventory(note, user=user)
        product.refresh_from_db()
        self.assertFalse(second.changed)
        self.assertEqual(product.stock, 10)

    def test_e34_compensation_is_blocked_when_later_activity_exists(self):
        user = get_user_model().objects.create_superuser(
            username="blocked-comp-admin",
            email="blocked-comp-admin@example.test",
            password="test-pass",
        )
        invoice, _origin_document, detail, result = self._created_e34(user, quantity=3)
        note = result.credit_note
        note.fiscal_resolution_status = "rejected"
        note.inventory_reconciliation_status = "compensation_required"
        note.requires_manual_review = True
        note.save(update_fields=["fiscal_resolution_status", "inventory_reconciliation_status", "requires_manual_review", "updated_at"])
        later_invoice = Invoice.objects.create(
            company=invoice.company,
            client=invoice.client,
            subtotal=Decimal("100.00"),
            tax=Decimal("18.00"),
            discount=Decimal("0.00"),
            total=Decimal("118.00"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=later_invoice,
            product=detail.product,
            quantity=1,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00"),
        )

        with self.assertRaisesMessage(ValueError, "facturas posteriores"):
            CreditNoteReconciliationService().compensate_inventory(note, user=user)

        note.refresh_from_db()
        self.assertTrue(note.requires_manual_review)
        self.assertIsNone(note.inventory_compensated_at)

    @override_settings(ECF_DGII_MOCK_ENABLED=False)
    def test_e34_processing_keeps_reconciliation_pending(self):
        user = get_user_model().objects.create_superuser(
            username="processing-e34-admin",
            email="processing-e34-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, _detail, result = self._created_e34(user, quantity=3)
        document = result.electronic_document
        document.fiscal_status = "submitted"
        document.status = "submitted"
        document.track_id = "track-e34-processing"
        document.save(update_fields=["fiscal_status", "status", "track_id", "updated_at"])

        DGIIStatusService(
            environment_resolver=FakeEnvironmentResolver(),
            token_provider=FakeTokenProvider(),
            soap_client_class=FakeProcessingDGIISOAPClient,
        ).check(document, user=user)

        note = result.credit_note
        note.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "submitted")
        self.assertEqual(note.fiscal_resolution_status, "pending")
        self.assertEqual(note.inventory_reconciliation_status, "restored_pending")

    def test_e34_technical_failure_does_not_change_reconciliation(self):
        user = get_user_model().objects.create_superuser(
            username="technical-e34-admin",
            email="technical-e34-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, _detail, result = self._created_e34(user, quantity=3)
        document = result.electronic_document
        document.fiscal_status = "signed"
        document.status = "signed"
        document.save(update_fields=["fiscal_status", "status", "updated_at"])

        with self.assertRaises(Exception):
            check_status.apply(args=[document.id], kwargs={"user_id": user.id}).get()

        note = result.credit_note
        note.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(document.fiscal_status, "signed")
        self.assertEqual(document.job_status, "failed")
        self.assertEqual(note.fiscal_resolution_status, "pending")
        self.assertEqual(note.inventory_reconciliation_status, "restored_pending")

    def test_credit_note_api_filters_and_summary_for_e34_operation(self):
        user = get_user_model().objects.create_superuser(
            username="e34-api-admin",
            email="e34-api-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, _detail, result = self._created_e34(user, quantity=3)
        note = result.credit_note
        document = result.electronic_document
        document.fiscal_status = "rejected"
        document.status = "rejected"
        document.rejection_reason = "Firma invalida"
        document.save(update_fields=["fiscal_status", "status", "rejection_reason", "updated_at"])
        note.fiscal_resolution_status = "rejected"
        note.inventory_reconciliation_status = "compensation_required"
        note.requires_manual_review = True
        note.save(update_fields=["fiscal_resolution_status", "inventory_reconciliation_status", "requires_manual_review", "updated_at"])

        request = APIRequestFactory().get(
            "/credit-notes/",
            {
                "ecf_fiscal_status": "rejected",
                "fiscal_resolution_status": "rejected",
                "inventory_reconciliation_status": "compensation_required",
                "requires_manual_review": "true",
                "search": note.credit_note_number,
            },
        )
        request.session = {"active_company_id": note.company_id}
        force_authenticate(request, user=user)
        response = CreditNoteViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        rows = response.data["results"] if "results" in response.data else response.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["electronic_document_id"], document.id)
        self.assertEqual(rows[0]["fiscal_status"], "rejected")
        self.assertEqual(rows[0]["job_status"], "idle")
        self.assertEqual(rows[0]["origin_client_name"], "Cliente E34 SRL")
        self.assertEqual(rows[0]["origin_encf"], _origin_document.encf)
        self.assertEqual(rows[0]["dgii_rejection_reason"], "Firma invalida")

        summary_request = APIRequestFactory().get("/credit-notes/fiscal-summary/")
        summary_request.session = {"active_company_id": note.company_id}
        force_authenticate(summary_request, user=user)
        summary = CreditNoteViewSet.as_view({"get": "fiscal_summary"})(summary_request)

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["rejected"], 1)
        self.assertEqual(summary.data["requires_manual_review"], 1)
        self.assertEqual(summary.data["inventory_compensation_required"], 1)
        self.assertEqual(summary.data["total_rejected"], note.total)

    def test_credit_note_api_create_assigns_company_and_blocks_cross_company_origin(self):
        user = get_user_model().objects.create_superuser(
            username="e34-create-company-admin",
            email="e34-create-company-admin@example.test",
            password="test-pass",
        )
        invoice, origin_document, detail = self._accepted_origin_invoice(quantity=3)
        CompanyMembership.objects.create(user=user, company=invoice.company, role="admin")
        ECFSequence.objects.create(
            company=origin_document.issuer.company,
            issuer=origin_document.issuer,
            ecf_type="34",
            start_number=300,
            end_number=400,
            next_number=300,
        )
        other_company = Company.objects.create(name="Empresa Ajena E34", rnc="499999999")
        CompanyMembership.objects.create(user=user, company=other_company, role="admin")

        request = APIRequestFactory().post(
            "/credit-notes/",
            {
                "origin_invoice": invoice.id,
                "details": [{"origin_detail": detail.id, "quantity": 1}],
                "reason": "Creacion E34 por API scoped",
            },
            format="json",
        )
        request.session = {"active_company_id": invoice.company_id}
        force_authenticate(request, user=user)
        with patch("facturacion.services.credit_notes.enqueue_submission_pipeline"):
            response = CreditNoteViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        note = CreditNote.objects.get(id=response.data["id"])
        self.assertEqual(note.company_id, invoice.company_id)

        blocked_request = APIRequestFactory().post(
            "/credit-notes/",
            {
                "origin_invoice": invoice.id,
                "details": [{"origin_detail": detail.id, "quantity": 1}],
                "reason": "Cross tenant",
            },
            format="json",
        )
        blocked_request.session = {"active_company_id": other_company.id}
        force_authenticate(blocked_request, user=user)
        blocked_response = CreditNoteViewSet.as_view({"post": "create"})(blocked_request)

        self.assertEqual(blocked_response.status_code, 400)
        self.assertIn("empresa activa", blocked_response.data["origin_invoice"])

    def test_credit_note_api_delegates_check_status_and_retry_to_ecf_queue(self):
        user = get_user_model().objects.create_superuser(
            username="e34-action-admin",
            email="e34-action-admin@example.test",
            password="test-pass",
        )
        _invoice, _origin_document, _detail, result = self._created_e34(user, quantity=3)
        note = result.credit_note
        document = result.electronic_document
        document.track_id = "track-e34-actions"
        document.fiscal_status = "submitted"
        document.status = "submitted"
        document.save(update_fields=["track_id", "fiscal_status", "status", "updated_at"])

        check_queue = Mock(return_value={"enqueued": True, "task_id": "check-1"})
        with patch("facturacion.api.views.credit_notes._legacy_queue_callable", return_value=check_queue):
            request = APIRequestFactory().post(f"/credit-notes/{note.id}/check-status/", {})
            request.session = {"active_company_id": note.company_id}
            force_authenticate(request, user=user)
            response = CreditNoteViewSet.as_view({"post": "check_status"})(request, pk=note.id)

        self.assertEqual(response.status_code, 202)
        check_queue.assert_called_once_with(document.id, user_id=user.id, environment=None)

        document.track_id = ""
        document.fiscal_status = "signed"
        document.status = "signed"
        document.job_status = "failed"
        document.save(update_fields=["track_id", "fiscal_status", "status", "job_status", "updated_at"])
        retry_queue = Mock(return_value={"enqueued": True, "task_id": "retry-1"})
        with patch("facturacion.api.views.credit_notes._legacy_queue_callable", return_value=retry_queue):
            request = APIRequestFactory().post(f"/credit-notes/{note.id}/retry/", {})
            request.session = {"active_company_id": note.company_id}
            force_authenticate(request, user=user)
            response = CreditNoteViewSet.as_view({"post": "retry"})(request, pk=note.id)

        self.assertEqual(response.status_code, 202)
        retry_queue.assert_called_once_with(document.id, user_id=user.id, environment=None)

    def _accepted_origin_invoice(self, quantity=3):
        suffix = Category.objects.count() + 1
        company = Company.objects.create(name=f"Empresa E34 Tenant {quantity}-{suffix}", rnc=str(400000000 + suffix))
        category = Category.objects.create(company=company, name=f"E34-{quantity}-{suffix}")
        product = Product.objects.create(
            company=company,
            name=f"Producto E34 {quantity}",
            description="Producto para nota de credito",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente E34 SRL", ruc_ci="131111111", email="cliente@example.test")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("300.00") if quantity == 3 else Decimal("200.00"),
            tax=Decimal("54.00") if quantity == 3 else Decimal("36.00"),
            discount=Decimal("0.00"),
            total=Decimal("354.00") if quantity == 3 else Decimal("236.00"),
            status="paid",
        )
        detail = InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            price=Decimal("100.00"),
            subtotal=Decimal("100.00") * quantity,
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name=f"Empresa E34 {quantity} SRL",
            rnc=str(200000000 + suffix),
            address="Calle Fiscal 123",
            municipality="010100",
            province="010000",
            email="fiscal@example.test",
        )
        sequence = ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=20,
            next_number=2,
            expiration_date=datetime.now(timezone.utc).date() + timedelta(days=365),
        )
        document = ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=sequence,
            ecf_type="31",
            encf=f"E3100000{suffix:05d}",
            status="accepted",
            xml_content="<ECF />",
            signed_xml_content="<ECF />",
            track_id=f"track-e34-{quantity}",
        )
        return invoice, document, detail

    def _created_e34(self, user, quantity=3):
        invoice, origin_document, detail = self._accepted_origin_invoice(quantity=quantity)
        CompanyMembership.objects.get_or_create(user=user, company=invoice.company, defaults={"role": "admin"})
        ECFSequence.objects.create(
            company=origin_document.issuer.company,
            issuer=origin_document.issuer,
            ecf_type="34",
            start_number=100,
            end_number=200,
            next_number=100,
        )
        with patch("facturacion.services.credit_notes.enqueue_submission_pipeline"):
            result = CreditNoteService().create_credit_note(
                origin_invoice_id=invoice.id,
                details=[{"origin_detail": detail.id, "quantity": 1}],
                reason="Reconciliacion E34",
                user=user,
            )
        return invoice, origin_document, detail, result


@override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
class ECFConcurrencyHardeningTests(TransactionTestCase):
    """Exercise database locks used by fiscal sequence/idempotency code."""

    reset_sequences = True

    def test_concurrent_sequence_allocation_has_no_duplicate_encf(self):
        company = Company.objects.first() or Company.objects.create(name="Empresa Stress", rnc="701010199")
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Stress SRL",
            rnc="101010199",
            address="Calle Stress",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=30,
            next_number=1,
        )

        def allocate():
            close_old_connections()
            encf, _sequence = ECFSequence.allocate_next(issuer=issuer, ecf_type="32")
            close_old_connections()
            return encf

        with ThreadPoolExecutor(max_workers=6) as pool:
            encfs = [future.result() for future in as_completed(pool.submit(allocate) for _ in range(20))]

        self.assertEqual(len(encfs), 20)
        self.assertEqual(len(set(encfs)), 20)
        self.assertEqual(sorted(encfs)[0], "E320000000001")
        self.assertEqual(sorted(encfs)[-1], "E320000000020")

    def test_concurrent_document_creation_for_same_invoice_is_idempotent(self):
        company = Company.objects.first() or Company.objects.create(name="Empresa Idempotente", rnc="701010198")
        category = Category.objects.create(company=company, name="IDEMPOTENCY")
        product = Product.objects.create(
            company=company,
            name="Producto Idempotente",
            description="Prueba",
            price=Decimal("25.00"),
            stock=50,
            category=category,
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa Idempotente SRL",
            rnc="101010198",
            address="Calle Idempotencia",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )
        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("25.00"),
            tax=Decimal("4.50"),
            discount=Decimal("0.00"),
            total=Decimal("29.50"),
            status="paid",
        )
        InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=1,
            price=Decimal("25.00"),
            subtotal=Decimal("25.00"),
        )

        def create_document():
            close_old_connections()
            result = ECFDocumentFactoryService().create_for_invoice(invoice, issuer_id=issuer.id, ecf_type="32")
            close_old_connections()
            return result.document.encf

        with ThreadPoolExecutor(max_workers=5) as pool:
            encfs = [future.result() for future in as_completed(pool.submit(create_document) for _ in range(5))]

        self.assertEqual(set(encfs), {"E320000000001"})
        self.assertEqual(ElectronicFiscalDocument.objects.filter(invoice=invoice).count(), 1)
        sequence = ECFSequence.objects.get(issuer=issuer, ecf_type="32")
        self.assertEqual(sequence.next_number, 2)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_e34_partial_reversals_do_not_exceed_origin_quantity(self):
        user = get_user_model().objects.create_superuser(
            username="e34-thread-admin",
            email="e34-thread-admin@example.test",
            password="test-pass",
        )
        company = Company.objects.create(name="Empresa E34 Thread Tenant", rnc="555000176")
        CompanyMembership.objects.create(user=user, company=company, role="admin")
        category = Category.objects.create(company=company, name="E34-THREAD")
        product = Product.objects.create(
            company=company,
            name="Producto E34 Thread",
            description="Prueba concurrencia E34",
            price=Decimal("100.00"),
            stock=10,
            category=category,
        )
        client = Client.objects.create(company=company, name="Cliente E34 Thread", ruc_ci="131111112")
        invoice = Invoice.objects.create(
            company=company,
            client=client,
            subtotal=Decimal("200.00"),
            tax=Decimal("36.00"),
            discount=Decimal("0.00"),
            total=Decimal("236.00"),
            status="paid",
        )
        detail = InvoiceDetail.objects.create(
            invoice=invoice,
            product=product,
            quantity=2,
            price=Decimal("100.00"),
            subtotal=Decimal("200.00"),
        )
        issuer = ECFIssuerConfig.objects.create(
            company=company,
            business_name="Empresa E34 Thread SRL",
            rnc="101010176",
            address="Calle Thread",
        )
        origin_sequence = ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="31",
            start_number=1,
            end_number=20,
            next_number=2,
            expiration_date=datetime.now(timezone.utc).date() + timedelta(days=365),
        )
        ElectronicFiscalDocument.objects.create(
            company=company,
            invoice=invoice,
            issuer=issuer,
            sequence=origin_sequence,
            ecf_type="31",
            encf="E310000000177",
            status="accepted",
            fiscal_status="accepted",
            xml_content="<ECF />",
            signed_xml_content="<ECF />",
            track_id="track-e34-thread",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="34",
            start_number=1,
            end_number=20,
            next_number=1,
        )

        def reverse_one():
            close_old_connections()
            try:
                with patch("facturacion.services.credit_notes.enqueue_submission_pipeline"):
                    CreditNoteService().create_credit_note(
                        origin_invoice_id=invoice.id,
                        details=[{"origin_detail": detail.id, "quantity": 1}],
                        reason="Reverso parcial concurrente real",
                        user=user,
                    )
                return "success"
            except ValueError:
                return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = [future.result() for future in as_completed(pool.submit(reverse_one) for _ in range(4))]

        product.refresh_from_db()
        self.assertEqual(results.count("success"), 1)
        self.assertEqual(CreditNote.objects.filter(origin_invoice=invoice).count(), 1)
        self.assertEqual(product.stock, 11)


class NumberSequenceHardeningTests(TransactionTestCase):
    """Validate transactional commercial/internal number allocation."""

    reset_sequences = True

    def test_concurrent_invoice_numbers_are_unique(self):
        company = Company.objects.create(name="Empresa Invoice Sequence", rnc="719999001")

        def create_invoice():
            close_old_connections()
            invoice = Invoice.objects.create(
                company_id=company.id,
                subtotal=Decimal("10.00"),
                tax=Decimal("1.80"),
                discount=Decimal("0.00"),
                total=Decimal("11.80"),
                status="paid",
            )
            number = invoice.invoice_number
            close_old_connections()
            return number

        numbers = self._run_concurrently(create_invoice, count=20, max_workers=6)

        self.assertEqual(len(numbers), 20)
        self.assertEqual(len(set(numbers)), 20)
        self.assertTrue(all(number.startswith("FAC-") for number in numbers))

    def test_concurrent_quotation_numbers_are_unique(self):
        company = Company.objects.create(name="Empresa Quotation Sequence", rnc="719999002")

        def create_quotation():
            close_old_connections()
            quotation = Quotation.objects.create(
                company_id=company.id,
                customer_name="Cliente Concurrente",
                subtotal=Decimal("10.00"),
                tax=Decimal("1.80"),
                discount=Decimal("0.00"),
                total=Decimal("11.80"),
            )
            number = quotation.quotation_number
            close_old_connections()
            return number

        numbers = self._run_concurrently(create_quotation, count=20, max_workers=6)

        self.assertEqual(len(numbers), 20)
        self.assertEqual(len(set(numbers)), 20)
        self.assertTrue(all(number.startswith("COT-") for number in numbers))

    def test_concurrent_credit_note_numbers_are_unique(self):
        company = Company.objects.create(name="Empresa CreditNote Sequence", rnc="719999004")

        def create_credit_note():
            from facturacion.services.numbering import NumberingService

            close_old_connections()
            number = NumberingService().allocate_unique(
                code="credit_note",
                model_class=CreditNote,
                field_name="credit_note_number",
                company=company,
            )
            close_old_connections()
            return number

        numbers = self._run_concurrently(create_credit_note, count=20, max_workers=6)

        self.assertEqual(len(numbers), 20)
        self.assertEqual(len(set(numbers)), 20)
        self.assertTrue(all(number.startswith("NC-") for number in numbers))

    def test_concurrent_product_internal_codes_are_unique(self):
        company = Company.objects.create(name="Empresa Barcode Stress", rnc="709999001")
        category = Category.objects.create(company=company, name="BARCODE-STRESS")

        def create_product():
            close_old_connections()
            product = Product.objects.create(
                company_id=company.id,
                name="Producto Barcode",
                description="Prueba",
                price=Decimal("10.00"),
                stock=5,
                category_id=category.id,
            )
            barcode = product.barcode
            close_old_connections()
            return barcode

        barcodes = self._run_concurrently(create_product, count=20, max_workers=6)

        self.assertEqual(len(barcodes), 20)
        self.assertEqual(len(set(barcodes)), 20)
        self.assertTrue(all(barcode.startswith("PRD-") for barcode in barcodes))

    def test_rolled_back_invoice_number_is_not_consumed(self):
        company = Company.objects.create(name="Empresa Invoice Rollback", rnc="719999003")
        NumberSequence.objects.update_or_create(
            company=company,
            code="invoice",
            scope_key="default",
            branch_code="",
            issuer=None,
            defaults={
                "sequence_kind": "commercial",
                "document_type": "invoice",
                "prefix": "FAC-",
                "suffix": "",
                "padding": 8,
                "next_number": 500,
                "scope_key": "default",
                "is_active": True,
            },
        )

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                Invoice.objects.create(
                    company=company,
                    subtotal=Decimal("10.00"),
                    tax=Decimal("1.80"),
                    discount=Decimal("0.00"),
                    total=Decimal("11.80"),
                    status="paid",
                )
                raise RuntimeError("forcing rollback")

        sequence = NumberSequence.objects.get(company=company, code="invoice")
        self.assertEqual(sequence.next_number, 500)

        invoice = Invoice.objects.create(
            company=company,
            subtotal=Decimal("10.00"),
            tax=Decimal("1.80"),
            discount=Decimal("0.00"),
            total=Decimal("11.80"),
            status="paid",
        )
        self.assertEqual(invoice.invoice_number, "FAC-00000500")

    def _run_concurrently(self, callback, *, count: int, max_workers: int):
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(callback) for _ in range(count)]
            return [future.result() for future in as_completed(futures)]


@override_settings(ECF_AUTO_ENQUEUE_ENABLED=False)
class QuotationFlowTests(TestCase):
    """Validate commercial quotation behavior before SaaS tenant work."""

    def test_quotation_does_not_decrement_stock_or_create_fiscal_document(self):
        product = self._product(stock=7)

        result = QuotationService().create_quotation(
            client_id=None,
            customer_name="Cliente Comercial",
            details=[{"product": product.id, "quantity": 3, "price": Decimal("100.00")}],
            discount=Decimal("0.00"),
            company=product.company,
        )

        product.refresh_from_db()
        self.assertEqual(product.stock, 7)
        self.assertEqual(result.quotation.status, "draft")
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(ElectronicFiscalDocument.objects.count(), 0)

    def test_approved_quotation_converts_to_pending_invoice_with_traceability(self):
        product = self._product(stock=7)
        issuer = ECFIssuerConfig.objects.create(
            company=product.company,
            business_name="Empresa Cotiza SRL",
            rnc="101010177",
            address="Calle Cotizacion",
        )
        ECFSequence.objects.create(
            company=issuer.company,
            issuer=issuer,
            ecf_type="32",
            start_number=1,
            end_number=10,
            next_number=1,
        )
        quotation = QuotationService().create_quotation(
            client_id=None,
            customer_name="Cliente Comercial",
            details=[{"product": product.id, "quantity": 2, "price": Decimal("100.00")}],
            discount=Decimal("0.00"),
            company=product.company,
        ).quotation
        QuotationService().approve(quotation.id)

        result = QuotationService().convert_to_invoice(
            quotation_id=quotation.id,
            issuer_id=issuer.id,
            payment_method="cash",
            status="pending",
        )

        product.refresh_from_db()
        result.quotation.refresh_from_db()
        result.invoice.refresh_from_db()
        self.assertEqual(product.stock, 7)
        self.assertEqual(result.invoice.origin_quotation_id, quotation.id)
        self.assertEqual(result.invoice.status, "pending")
        self.assertIsNone(result.invoice.inventory_committed_at)
        self.assertIsNotNone(result.quotation.converted_at)
        self.assertIsNone(result.electronic_document)
        self.assertFalse(result.ecf_enqueued)

    def _product(self, stock=10):
        company = Company.objects.create(name=f"Empresa Quote Flow {stock}", rnc=f"8010101{stock:02d}")
        category = Category.objects.create(company=company, name=f"QUOTE-{stock}")
        return Product.objects.create(
            company=company,
            name=f"Producto Cotizacion {stock}",
            description="Producto comercial",
            price=Decimal("100.00"),
            stock=stock,
            category=category,
        )
