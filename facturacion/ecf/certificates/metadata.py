"""Certificate metadata extraction for DGII issuer configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from pathlib import Path
import re

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.db import transaction
from django.utils import timezone

from facturacion.models import ECFIssuerConfig


RNC_CANDIDATE_RE = re.compile(r"(?<!\d)(?:\d[\s-]?){9}(?:(?:\d[\s-]?){2})?(?!\d)")


@dataclass(frozen=True)
class CertificateMetadataResult:
    issuer: ECFIssuerConfig
    status: str


class ECFCertificateMetadataService:
    """Refresh non-secret certificate metadata on an issuer config."""

    EXPIRING_SOON_DAYS = 30

    def refresh(self, issuer: ECFIssuerConfig) -> CertificateMetadataResult:
        with transaction.atomic():
            locked_issuer = ECFIssuerConfig.objects.select_for_update().get(pk=issuer.pk)
            self._refresh_locked(locked_issuer)
            return CertificateMetadataResult(issuer=locked_issuer, status=locked_issuer.certificate_status)

    def _refresh_locked(self, issuer: ECFIssuerConfig) -> None:
        now = timezone.now()
        reset_fields = {
            "certificate_subject": None,
            "certificate_issuer": None,
            "certificate_serial_number": None,
            "certificate_fingerprint": None,
            "certificate_not_valid_before": None,
            "certificate_not_valid_after": None,
            "certificate_rnc_detected": None,
            "certificate_rnc_match_status": ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN,
            "certificate_status_updated_at": now,
        }

        if not issuer.certificate_path:
            self._save_metadata(
                issuer,
                {
                    **reset_fields,
                    "certificate_status": ECFIssuerConfig.CERTIFICATE_STATUS_MISSING,
                    "certificate_rnc_match_status": ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND,
                },
            )
            return

        try:
            certificate = self._load_certificate_for_metadata(issuer.certificate_path, issuer.certificate_password)
            not_valid_before = self._not_valid_before(certificate)
            not_valid_after = self._not_valid_after(certificate)
            status = self._status_for_dates(now, not_valid_before, not_valid_after)
            rnc_candidates = extract_rnc_candidates_from_certificate(certificate)
            rnc_match_status = self._rnc_match_status(issuer.rnc, rnc_candidates)
            self._save_metadata(
                issuer,
                {
                    "certificate_subject": certificate.subject.rfc4514_string(),
                    "certificate_issuer": certificate.issuer.rfc4514_string(),
                    "certificate_serial_number": str(certificate.serial_number),
                    "certificate_fingerprint": certificate.fingerprint(hashes.SHA256()).hex(),
                    "certificate_not_valid_before": not_valid_before,
                    "certificate_not_valid_after": not_valid_after,
                    "certificate_rnc_detected": ", ".join(rnc_candidates) if rnc_candidates else None,
                    "certificate_rnc_match_status": rnc_match_status,
                    "certificate_status": status,
                    "certificate_status_updated_at": now,
                },
            )
        except Exception:
            self._save_metadata(
                issuer,
                {
                    **reset_fields,
                    "certificate_status": ECFIssuerConfig.CERTIFICATE_STATUS_INVALID,
                },
            )

    def _load_certificate_for_metadata(self, certificate_path: str, password: str | bytes | None):
        path = Path(certificate_path)
        if not path.exists() or not path.is_file():
            raise ValueError("Certificate file does not exist.")
        private_key, certificate, _additional = pkcs12.load_key_and_certificates(
            path.read_bytes(),
            self._password_bytes(password),
        )
        if private_key is None or certificate is None:
            raise ValueError("PKCS#12 file does not contain a private key and certificate.")
        return certificate

    def _status_for_dates(self, now, not_valid_before, not_valid_after) -> str:
        if not_valid_before > now:
            return ECFIssuerConfig.CERTIFICATE_STATUS_INVALID
        if not_valid_after <= now:
            return ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED
        if not_valid_after <= now + timezone.timedelta(days=self.EXPIRING_SOON_DAYS):
            return ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRING
        return ECFIssuerConfig.CERTIFICATE_STATUS_ACTIVE

    def _save_metadata(self, issuer: ECFIssuerConfig, values: dict) -> None:
        for field, value in values.items():
            setattr(issuer, field, value)
        issuer.save(update_fields=[*values.keys(), "updated_at"])

    def _password_bytes(self, password: str | bytes | None) -> bytes | None:
        if password is None or password == "":
            return None
        if isinstance(password, bytes):
            return password
        return password.encode("utf-8")

    def _not_valid_before(self, certificate):
        if hasattr(certificate, "not_valid_before_utc"):
            return certificate.not_valid_before_utc
        return certificate.not_valid_before.replace(tzinfo=datetime_timezone.utc)

    def _not_valid_after(self, certificate):
        if hasattr(certificate, "not_valid_after_utc"):
            return certificate.not_valid_after_utc
        return certificate.not_valid_after.replace(tzinfo=datetime_timezone.utc)

    def _rnc_match_status(self, issuer_rnc: str, candidates: list[str]) -> str:
        if not candidates:
            return ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND
        normalized_issuer_rnc = normalize_rnc_candidate(issuer_rnc)
        if not normalized_issuer_rnc:
            return ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN
        if normalized_issuer_rnc in candidates:
            return ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MATCHED
        return ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MISMATCH


def extract_rnc_candidates_from_certificate(certificate) -> list[str]:
    """Return normalized 9/11 digit RNC-like values found in X.509 metadata."""
    values = certificate_metadata_values(certificate)
    candidates: list[str] = []
    seen: set[str] = set()
    for value in values:
        for match in RNC_CANDIDATE_RE.finditer(str(value or "")):
            normalized = normalize_rnc_candidate(match.group(0))
            if normalized and normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)
    return candidates


def certificate_metadata_values(certificate) -> list[str]:
    """Collect subject, SAN and extension values useful for fiscal metadata inspection."""
    values = [
        certificate.subject.rfc4514_string(),
        certificate.issuer.rfc4514_string(),
        str(certificate.serial_number),
    ]

    attribute_oids = [
        NameOID.COMMON_NAME,
        NameOID.ORGANIZATION_NAME,
        NameOID.ORGANIZATIONAL_UNIT_NAME,
        NameOID.SERIAL_NUMBER,
    ]
    for oid in attribute_oids:
        values.extend(attribute.value for attribute in certificate.subject.get_attributes_for_oid(oid))

    for attribute in certificate.subject:
        values.append(attribute.value)
        values.append(attribute.oid.dotted_string)
        values.append(getattr(attribute.oid, "_name", ""))

    for extension in certificate.extensions:
        values.append(extension.oid.dotted_string)
        values.append(getattr(extension.oid, "_name", ""))
        values.append(str(extension.value))
        if isinstance(extension.value, x509.SubjectAlternativeName):
            for name in extension.value:
                values.append(str(name.value if hasattr(name, "value") else name))

    return [value for value in values if value]


def normalize_rnc_candidate(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) in {9, 11}:
        return digits
    return None
