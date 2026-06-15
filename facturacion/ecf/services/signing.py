"""Service layer for signing and storing DGII e-CF XML documents."""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from facturacion.models import ECFEventLog, ElectronicFiscalDocument
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.exceptions import ECFError, ECFValidationError
from facturacion.ecf.signer.xml_signer import ECFXMLSigner
from facturacion.ecf.validators.signature import ECFSignatureValidator
from facturacion.ecf.validators.xsd import ECFXSDValidator


@dataclass(frozen=True)
class ECFSigningResult:
    """Result returned after signing an e-CF XML."""

    document: ElectronicFiscalDocument
    signed_xml_content: str
    signature_validated: bool
    xsd_validated: bool


class ECFSigningService:
    """Sign generated e-CF XML, validate it and persist the signed XML."""

    def __init__(
        self,
        certificate_loader: PKCS12CertificateLoader | None = None,
        signer: ECFXMLSigner | None = None,
        signature_validator: ECFSignatureValidator | None = None,
        xsd_validator: ECFXSDValidator | None = None,
    ) -> None:
        self.certificate_loader = certificate_loader or PKCS12CertificateLoader()
        self.signer = signer or ECFXMLSigner()
        self.signature_validator = signature_validator or ECFSignatureValidator()
        self.xsd_validator = xsd_validator or ECFXSDValidator()
        self.state_machine = ECFStateMachine()
        self.status_transitions = ECFStatusTransitionService()

    def sign(
        self,
        document: ElectronicFiscalDocument,
        certificate_path: str,
        certificate_password: str | bytes | None,
        user=None,
        validate_xsd: bool = True,
    ) -> ECFSigningResult:
        """Sign an e-CF XML and write the signed content to the document."""
        try:
            return self._sign_atomic(document, certificate_path, certificate_password, user, validate_xsd)
        except ECFError as exc:
            self._log_error(document, str(exc), user)
            raise

    @transaction.atomic
    def _sign_atomic(
        self,
        document: ElectronicFiscalDocument,
        certificate_path: str,
        certificate_password: str | bytes | None,
        user=None,
        validate_xsd: bool = True,
    ) -> ECFSigningResult:
        locked_document = (
            ElectronicFiscalDocument.objects
            .select_for_update()
            .get(pk=document.pk)
        )

        if not locked_document.xml_content:
            raise ECFValidationError("El documento no tiene XML generado para firmar.")
        self.status_transitions.fiscal_state_machine.assert_transition(locked_document.fiscal_status, "signed")

        certificate = self.certificate_loader.load(certificate_path, certificate_password)
        signed_xml = self.signer.sign(locked_document.xml_content, certificate)
        self.signature_validator.validate(signed_xml, certificate)

        if validate_xsd:
            self.xsd_validator.validate(locked_document.ecf_type, signed_xml)

        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="signed",
            source="xml_signing",
            reason="XML e-CF firmado y validado.",
            extra_update_fields={"signed_xml_content": signed_xml},
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="signed",
            message="XML e-CF firmado y validado criptográficamente.",
            payload={
                "signature_validated": True,
                "xsd_validated": validate_xsd,
                "certificate_subject": certificate.subject,
                "certificate_issuer": certificate.issuer,
                "certificate_serial_number": certificate.serial_number,
                "certificate_not_valid_after": str(certificate.not_valid_after),
                "certificate_sha256_fingerprint": certificate.sha256_fingerprint,
            },
            created_by=user,
        )

        return ECFSigningResult(
            document=locked_document,
            signed_xml_content=signed_xml,
            signature_validated=True,
            xsd_validated=validate_xsd,
        )

    def _log_error(self, document: ElectronicFiscalDocument, message: str, user=None) -> None:
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="error",
            message=f"Error firmando XML e-CF: {message}",
            payload={"stage": "xml_signature"},
            created_by=user,
        )
