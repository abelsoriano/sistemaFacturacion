"""Resolve issuer certificates with an explicit development fallback."""

from __future__ import annotations

from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.utils import timezone

from facturacion.models import ECFCertificate


def resolve_certificate_credentials(issuer):
    """Return certificate credentials for an issuer with SaaS-safe fallbacks."""
    active_certificate = active_certificate_for_issuer(issuer)
    if active_certificate:
        return active_certificate.certificate_reference, active_certificate.password_secret_reference

    if issuer.certificate_path and _legacy_fallback_allowed():
        return issuer.certificate_path, issuer.certificate_password or getattr(settings, "ECF_CERTIFICATE_PASSWORD", None)

    allow_non_production_fallback = (
        getattr(settings, "DEBUG", False)
        or getattr(settings, "ECF_DGII_ENVIRONMENT", "") == "testing"
    )
    if (
        allow_non_production_fallback
        and getattr(settings, "ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK", False)
        and getattr(settings, "ECF_CERTIFICATE_PATH", None)
    ):
        return getattr(settings, "ECF_CERTIFICATE_PATH"), getattr(settings, "ECF_CERTIFICATE_PASSWORD", None)

    if getattr(settings, "ECF_ALLOW_DEV_SELF_SIGNED_CERT", False):
        password = getattr(settings, "ECF_DEV_CERTIFICATE_PASSWORD", "dev-ecf-password")
        return str(_ensure_dev_certificate(issuer, password)), password

    return None, None


def active_certificate_for_issuer(issuer):
    return (
        ECFCertificate.objects
        .filter(
            company_id=issuer.company_id,
            issuer_id=issuer.id,
            environment=issuer.environment,
            is_active=True,
        )
        .order_by('-activated_at', '-uploaded_at')
        .first()
    )


def _legacy_fallback_allowed() -> bool:
    production_like = (
        not getattr(settings, "DEBUG", False)
        and not getattr(settings, "ECF_DGII_MOCK_ENABLED", False)
        and getattr(settings, "ECF_DGII_ENVIRONMENT", "") == "production"
    )
    if production_like and not getattr(settings, "ECF_ALLOW_LEGACY_CERTIFICATE_FALLBACK", True):
        return False
    return True


def _ensure_dev_certificate(issuer, password: str) -> Path:
    cert_dir = Path(settings.BASE_DIR) / "media" / "ecf" / "certificates"
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / f"dev-ecf-{issuer.rnc}.p12"
    if cert_path.exists():
        return cert_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = timezone.now()
    subject = issuer_name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DO"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, issuer.business_name[:64]),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{issuer.business_name[:48]} DEV e-CF"),
        ]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timezone.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    p12 = pkcs12.serialize_key_and_certificates(
        name=f"{issuer.rnc}-dev-ecf".encode("utf-8"),
        key=key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    cert_path.write_bytes(p12)
    return cert_path
