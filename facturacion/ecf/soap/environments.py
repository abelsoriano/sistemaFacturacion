"""DGII SOAP environment configuration."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from facturacion.ecf.exceptions import ECFValidationError


@dataclass(frozen=True)
class DGIISOAPEnvironment:
    """Resolved WSDL and operation settings for one DGII environment."""

    name: str
    reception_wsdl: str
    status_wsdl: str
    trackids_wsdl: str | None
    submit_operation: str
    status_operation: str
    trackids_operation: str
    timeout: int
    retries: int
    retry_backoff: float
    verify_tls: bool


class DGIISOAPEnvironmentResolver:
    """Resolve DGII SOAP configuration from Django settings."""

    def resolve(self, environment: str | None = None) -> DGIISOAPEnvironment:
        """Return validated SOAP settings for the selected environment."""
        env_name = environment or getattr(settings, "ECF_DGII_ENVIRONMENT", "testing")
        wsdl_map = getattr(settings, "ECF_DGII_SOAP_WSDLS", {}).get(env_name, {})
        operations = getattr(settings, "ECF_DGII_SOAP_OPERATIONS", {})

        reception_wsdl = wsdl_map.get("reception")
        status_wsdl = wsdl_map.get("status")
        if not reception_wsdl:
            raise ECFValidationError(f"No hay WSDL de recepción DGII configurado para ambiente {env_name}.")
        if not status_wsdl:
            raise ECFValidationError(f"No hay WSDL de consulta DGII configurado para ambiente {env_name}.")

        return DGIISOAPEnvironment(
            name=env_name,
            reception_wsdl=reception_wsdl,
            status_wsdl=status_wsdl,
            trackids_wsdl=wsdl_map.get("trackids"),
            submit_operation=operations.get("submit", "RecepcionECF"),
            status_operation=operations.get("status", "ConsultaResultado"),
            trackids_operation=operations.get("trackids", "ConsultaTrackIds"),
            timeout=getattr(settings, "ECF_DGII_TIMEOUT", 30),
            retries=getattr(settings, "ECF_DGII_RETRIES", 3),
            retry_backoff=getattr(settings, "ECF_DGII_RETRY_BACKOFF", 0.5),
            verify_tls=getattr(settings, "ECF_DGII_VERIFY_TLS", True),
        )

