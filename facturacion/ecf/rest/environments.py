"""DGII REST environment configuration."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from facturacion.ecf.exceptions import ECFValidationError


@dataclass(frozen=True)
class DGIIRESTEnvironment:
    """Resolved REST endpoint settings for one DGII environment."""

    name: str
    auth_base_url: str
    reception_base_url: str
    status_base_url: str
    trackids_base_url: str | None
    timeout: int
    retries: int
    retry_backoff: float
    verify_tls: bool


class DGIIRESTEnvironmentResolver:
    """Resolve DGII REST configuration from Django settings."""

    def resolve(self, environment: str | None = None) -> DGIIRESTEnvironment:
        env_name = environment or getattr(settings, "ECF_DGII_ENVIRONMENT", "testing")
        url_map = getattr(settings, "ECF_DGII_REST_BASE_URLS", {}).get(env_name, {})

        auth_base_url = self._clean(url_map.get("auth"))
        reception_base_url = self._clean(url_map.get("reception"))
        status_base_url = self._clean(url_map.get("status"))
        trackids_base_url = self._clean(url_map.get("trackids"))

        if not auth_base_url:
            raise ECFValidationError(f"No hay URL REST de autenticacion DGII configurada para ambiente {env_name}.")
        if not reception_base_url:
            raise ECFValidationError(f"No hay URL REST de recepcion DGII configurada para ambiente {env_name}.")
        if not status_base_url:
            raise ECFValidationError(f"No hay URL REST de consulta DGII configurada para ambiente {env_name}.")

        return DGIIRESTEnvironment(
            name=env_name,
            auth_base_url=auth_base_url,
            reception_base_url=reception_base_url,
            status_base_url=status_base_url,
            trackids_base_url=trackids_base_url,
            timeout=getattr(settings, "ECF_DGII_TIMEOUT", 30),
            retries=getattr(settings, "ECF_DGII_RETRIES", 3),
            retry_backoff=getattr(settings, "ECF_DGII_RETRY_BACKOFF", 0.5),
            verify_tls=getattr(settings, "ECF_DGII_VERIFY_TLS", True),
        )

    def _clean(self, value: str | None) -> str | None:
        if not value:
            return None
        return value.rstrip("/")
