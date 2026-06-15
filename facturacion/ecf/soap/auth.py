"""Authentication helpers for DGII SOAP clients."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from facturacion.ecf.exceptions import ECFValidationError


@dataclass(frozen=True)
class DGIIBearerToken:
    """Bearer token used to authenticate DGII service calls."""

    value: str

    @property
    def authorization_header(self) -> str:
        return f"Bearer {self.value}"


class SettingsTokenProvider:
    """Read the current DGII bearer token from Django settings."""

    def get_token(self) -> DGIIBearerToken:
        """Return a configured token or raise a validation error."""
        token = getattr(settings, "ECF_DGII_AUTH_TOKEN", None)
        if not token:
            raise ECFValidationError("ECF_DGII_AUTH_TOKEN no está configurado.")
        return DGIIBearerToken(token)

