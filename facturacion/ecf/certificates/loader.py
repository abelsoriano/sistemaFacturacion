"""Secure loading and validation of PKCS#12 certificates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from django.utils import timezone

from facturacion.ecf.exceptions import ECFValidationError


@dataclass(frozen=True)
class LoadedCertificate:
    """Private key and X509 certificate material ready for XMLDSig."""

    private_key_pem: bytes
    certificate_pem: bytes
    certificate: x509.Certificate
    subject: str
    issuer: str
    serial_number: str
    not_valid_after: str
    sha256_fingerprint: str


class PKCS12CertificateLoader:
    """Load a .p12/.pfx file without leaking password material."""

    def load(self, certificate_path: str | Path, password: str | bytes | None) -> LoadedCertificate:
        """Load a PKCS#12 certificate and validate its usability."""
        path = Path(certificate_path)
        if not path.exists() or not path.is_file():
            raise ECFValidationError(f"No existe el certificado configurado: {path}")

        password_bytes = self._password_bytes(password)
        try:
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                path.read_bytes(),
                password_bytes,
            )
        except Exception as exc:
            raise ECFValidationError("No fue posible abrir el certificado .p12 con el password configurado.") from exc

        if private_key is None or certificate is None:
            raise ECFValidationError("El archivo .p12 no contiene llave privada y certificado X509.")

        self._validate_expiration(certificate)

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
        fingerprint = certificate.fingerprint(hashes.SHA256()).hex()

        return LoadedCertificate(
            private_key_pem=private_key_pem,
            certificate_pem=certificate_pem,
            certificate=certificate,
            subject=certificate.subject.rfc4514_string(),
            issuer=certificate.issuer.rfc4514_string(),
            serial_number=str(certificate.serial_number),
            not_valid_after=self._not_valid_after(certificate).isoformat(),
            sha256_fingerprint=fingerprint or hashlib.sha256(certificate_pem).hexdigest(),
        )

    def _password_bytes(self, password: str | bytes | None) -> bytes | None:
        if password is None or password == "":
            return None
        if isinstance(password, bytes):
            return password
        return password.encode("utf-8")

    def _validate_expiration(self, certificate: x509.Certificate) -> None:
        now = timezone.now()
        if self._not_valid_before(certificate) > now:
            raise ECFValidationError("El certificado digital aún no es válido.")
        if self._not_valid_after(certificate) <= now:
            raise ECFValidationError("El certificado digital está vencido.")

    def _not_valid_before(self, certificate: x509.Certificate):
        if hasattr(certificate, "not_valid_before_utc"):
            return certificate.not_valid_before_utc
        return certificate.not_valid_before.replace(tzinfo=datetime_timezone.utc)

    def _not_valid_after(self, certificate: x509.Certificate):
        if hasattr(certificate, "not_valid_after_utc"):
            return certificate.not_valid_after_utc
        return certificate.not_valid_after.replace(tzinfo=datetime_timezone.utc)
