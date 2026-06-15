"""Manual DGII REST test helpers used by management commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.models import Company, ECFIssuerConfig


@dataclass(frozen=True)
class ManualCertificateContext:
    certificate_path: str
    certificate_password: str | bytes | None
    issuer_rnc: str | None
    issuer: ECFIssuerConfig | None
    company: Company | None


def resolve_manual_certificate_context(
    *,
    company_id: int | None = None,
    company: Company | None = None,
    issuer_id: int | None = None,
    certificate_path: str | None = None,
    certificate_password: str | None = None,
    issuer_rnc: str | None = None,
) -> ManualCertificateContext:
    company = company or (Company.objects.get(pk=company_id) if company_id else None)
    issuer = None
    if issuer_id:
        issuer = ECFIssuerConfig.objects.select_related("company").get(pk=issuer_id)
        if company and issuer.company_id != company.id:
            raise ECFValidationError("El emisor indicado no pertenece a la empresa seleccionada.")
        company = company or issuer.company
        resolved_path, resolved_password = resolve_certificate_credentials(issuer)
        certificate_path = certificate_path or resolved_path
        certificate_password = certificate_password if certificate_password is not None else resolved_password
        issuer_rnc = issuer_rnc or issuer.rnc

    if not company:
        raise ECFValidationError("Indica --company-id o --issuer-id para establecer un contexto fiscal seguro.")

    certificate_path = certificate_path or getattr(settings, "ECF_CERTIFICATE_PATH", None)
    certificate_password = certificate_password if certificate_password is not None else getattr(settings, "ECF_CERTIFICATE_PASSWORD", None)

    if not certificate_path:
        raise ECFValidationError("Configura --certificate-path, --issuer-id o ECF_CERTIFICATE_PATH.")

    return ManualCertificateContext(
        certificate_path=certificate_path,
        certificate_password=certificate_password,
        issuer_rnc=issuer_rnc,
        issuer=issuer,
        company=company,
    )


def mask_token(token: str | None) -> str:
    if not token:
        return ""
    if len(token) <= 12:
        return token[:2] + "***"
    return f"{token[:6]}...{token[-4:]}"


def write_rest_artifact(prefix: str, payload: Any, *, suffix: str = "json") -> Path:
    directory = Path(settings.BASE_DIR) / "media" / "ecf" / "rest-tests"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    path = directory / f"{timestamp}-{prefix}.{suffix}"
    if suffix == "json":
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    return path


def summarize_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        keys = ", ".join(str(key) for key in payload.keys())
        return f"dict({keys})"
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    if isinstance(payload, str):
        return f"str[{len(payload)}]"
    return type(payload).__name__
