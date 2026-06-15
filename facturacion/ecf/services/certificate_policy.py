"""Signing policy for DGII certificates before XML signature."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from facturacion.ecf.certificates.resolver import active_certificate_for_issuer
from facturacion.ecf.certificates.metadata import ECFCertificateMetadataService
from facturacion.models import ECFEventLog, ECFIssuerConfig, ElectronicFiscalDocument
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService


@dataclass(frozen=True)
class ECFCertificateSigningPolicyResult:
    allowed: bool
    blocked: bool
    warnings: list[str] = field(default_factory=list)
    reason: str = ""
    code: str = ""


class ECFCertificateSigningPolicy:
    """Evaluate whether an issuer certificate can be used to sign e-CF XML."""

    def __init__(
        self,
        metadata_service: ECFCertificateMetadataService | None = None,
        status_transitions: ECFStatusTransitionService | None = None,
    ) -> None:
        self.metadata_service = metadata_service or ECFCertificateMetadataService()
        self.status_transitions = status_transitions or ECFStatusTransitionService()

    def evaluate(self, issuer: ECFIssuerConfig, *, refresh_metadata: bool = True) -> ECFCertificateSigningPolicyResult:
        issuer = self._refresh_metadata_if_needed(issuer) if refresh_metadata else issuer
        active_certificate = active_certificate_for_issuer(issuer)
        certificate_status = (
            active_certificate.status
            if active_certificate
            else issuer.certificate_status
        ) or ECFIssuerConfig.CERTIFICATE_STATUS_MISSING
        rnc_match_status = (
            active_certificate.rnc_match_status
            if active_certificate
            else issuer.certificate_rnc_match_status
        ) or ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN
        permissive = self._is_permissive_environment()

        if certificate_status == ECFIssuerConfig.CERTIFICATE_STATUS_INVALID:
            return self._blocked(
                "certificate_invalid",
                "El certificado DGII configurado es inválido o no pudo cargarse.",
            )
        if certificate_status == ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRED:
            return self._blocked(
                "certificate_expired",
                "El certificado DGII está vencido. Renueve el certificado antes de firmar e-CF.",
            )
        if certificate_status == ECFIssuerConfig.CERTIFICATE_STATUS_MISSING:
            if permissive and getattr(settings, "ECF_ALLOW_GLOBAL_CERTIFICATE_FALLBACK", False):
                return self._allowed(
                    "certificate_missing_with_fallback",
                    ["El emisor no tiene certificado DGII propio; se usará fallback global habilitado para pruebas."],
                )
            return self._blocked(
                "certificate_missing",
                "El emisor fiscal no tiene certificado DGII configurado.",
            )

        warnings: list[str] = []
        code = "certificate_policy_allowed"
        if certificate_status == ECFIssuerConfig.CERTIFICATE_STATUS_EXPIRING:
            warnings.append("El certificado DGII está próximo a vencer.")
            code = "certificate_expiring_soon"

        if rnc_match_status == ECFIssuerConfig.CERTIFICATE_RNC_MATCH_MISMATCH:
            message = "El RNC detectado en el certificado no coincide con el RNC del emisor fiscal configurado."
            if permissive:
                warnings.append(message)
                code = "certificate_rnc_mismatch_warning"
            else:
                return self._blocked("certificate_rnc_mismatch", message)
        elif rnc_match_status == ECFIssuerConfig.CERTIFICATE_RNC_MATCH_NOT_FOUND:
            warnings.append("No se pudo detectar el RNC en el certificado. Verifique manualmente el emisor.")
            code = "certificate_rnc_not_found_warning"
        elif rnc_match_status == ECFIssuerConfig.CERTIFICATE_RNC_MATCH_UNKNOWN:
            warnings.append("La coincidencia RNC del certificado está en estado desconocido.")
            code = "certificate_rnc_unknown_warning"

        return self._allowed(code, warnings)

    def log_warnings(
        self,
        document: ElectronicFiscalDocument,
        result: ECFCertificateSigningPolicyResult,
        *,
        user=None,
    ) -> None:
        for warning in result.warnings:
            ECFEventLog.objects.create(
                electronic_document=document,
                event_type="warning",
                message=warning,
                payload={
                    "stage": "certificate_policy",
                    "code": result.code,
                    **self._certificate_payload(document.issuer),
                },
                created_by=user,
            )

    def record_blocked(
        self,
        document: ElectronicFiscalDocument,
        result: ECFCertificateSigningPolicyResult,
        *,
        user=None,
        source: str = "certificate_policy_blocked",
        task_id: str | None = None,
    ) -> ElectronicFiscalDocument:
        transition = self.status_transitions.transition(
            document,
            job_status="failed",
            source=source,
            reason=result.reason,
            task_id=task_id,
            validate=False,
            extra_update_fields={"last_error": result.reason, "next_retry_at": None},
        )
        document = transition.document
        ECFEventLog.objects.create(
            electronic_document=document,
            event_type="error",
            message=result.reason,
            payload={
                "stage": "certificate_policy",
                "code": result.code,
                **self._certificate_payload(document.issuer),
            },
            created_by=user,
        )
        return document

    def _refresh_metadata_if_needed(self, issuer: ECFIssuerConfig) -> ECFIssuerConfig:
        if not self._metadata_is_stale(issuer):
            return issuer
        try:
            result = self.metadata_service.refresh(issuer)
            return result.issuer
        except Exception:
            issuer.refresh_from_db()
            return issuer

    def _metadata_is_stale(self, issuer: ECFIssuerConfig) -> bool:
        if not issuer.certificate_status_updated_at:
            return True
        if issuer.certificate_path and not issuer.certificate_fingerprint:
            return True
        stale_hours = getattr(settings, "ECF_CERTIFICATE_METADATA_STALE_HOURS", 24)
        return issuer.certificate_status_updated_at <= timezone.now() - timezone.timedelta(hours=stale_hours)

    def _is_permissive_environment(self) -> bool:
        return (
            bool(getattr(settings, "DEBUG", False))
            or bool(getattr(settings, "ECF_DGII_MOCK_ENABLED", False))
            or getattr(settings, "ECF_DGII_ENVIRONMENT", "") == "testing"
        )

    def _certificate_payload(self, issuer: ECFIssuerConfig) -> dict:
        active_certificate = active_certificate_for_issuer(issuer)
        if active_certificate:
            return {
                "certificate_id": active_certificate.id,
                "certificate_status": active_certificate.status,
                "certificate_rnc_match_status": active_certificate.rnc_match_status,
            }
        return {
            "certificate_id": None,
            "certificate_status": issuer.certificate_status,
            "certificate_rnc_match_status": issuer.certificate_rnc_match_status,
        }

    def _allowed(self, code: str, warnings: list[str] | None = None) -> ECFCertificateSigningPolicyResult:
        warnings = warnings or []
        return ECFCertificateSigningPolicyResult(
            allowed=True,
            blocked=False,
            warnings=warnings,
            reason=warnings[0] if warnings else "",
            code=code,
        )

    def _blocked(self, code: str, reason: str) -> ECFCertificateSigningPolicyResult:
        return ECFCertificateSigningPolicyResult(
            allowed=False,
            blocked=True,
            warnings=[],
            reason=reason,
            code=code,
        )
