"""Authentication helpers for DGII REST services."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import requests
from django.core.cache import cache

from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.rest.environments import DGIIRESTEnvironment, DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.responses import DGIIRESTToken
from facturacion.ecf.signer.xml_signer import ECFXMLSigner


@dataclass(frozen=True)
class DGIISeedPayload:
    """Seed XML returned by DGII before certificate validation."""

    xml: str
    raw: Any


class DGIIRESTAuthClient:
    """Obtain and cache DGII REST bearer tokens using signed seed XML."""

    seed_path = "/api/Autenticacion/Semilla"
    validate_seed_path = "/api/Autenticacion/ValidarSemilla"
    default_expires_in = 3300

    def __init__(
        self,
        environment: DGIIRESTEnvironment | None = None,
        environment_resolver: DGIIRESTEnvironmentResolver | None = None,
        certificate_loader: PKCS12CertificateLoader | None = None,
        signer: ECFXMLSigner | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.environment = environment or (environment_resolver or DGIIRESTEnvironmentResolver()).resolve()
        self.certificate_loader = certificate_loader or PKCS12CertificateLoader()
        self.signer = signer or ECFXMLSigner()
        self.session = session or requests.Session()
        self.session.verify = self.environment.verify_tls

    def get_token(self, certificate_path: str, certificate_password: str | bytes | None, issuer_rnc: str | None = None) -> DGIIRESTToken:
        cache_key = self._cache_key(certificate_path, issuer_rnc)
        cached = cache.get(cache_key)
        if cached:
            return DGIIRESTToken(value=cached, expires_in=self.default_expires_in)

        seed = self.request_seed()
        certificate = self.certificate_loader.load(certificate_path, certificate_password)
        signed_seed = self.signer.sign(seed.xml, certificate)
        token = self.validate_seed(signed_seed)
        cache_timeout = max(60, min(token.expires_in, self.default_expires_in))
        cache.set(cache_key, token.value, timeout=cache_timeout)
        return token

    def request_seed(self) -> DGIISeedPayload:
        response = self.session.get(
            self._url(self.seed_path),
            timeout=self.environment.timeout,
        )
        self._raise_for_status(response, "obteniendo semilla DGII")
        data = self._response_data(response)
        seed_xml = self._first(data, "semilla", "Semilla", "xml", "Xml", "valor")
        if not seed_xml:
            raise ECFValidationError("DGII no retorno semilla para autenticacion.")
        return DGIISeedPayload(xml=str(seed_xml), raw=data)

    def validate_seed(self, signed_seed_xml: str) -> DGIIRESTToken:
        response = self.session.post(
            self._url(self.validate_seed_path),
            files={"xml": ("semilla_firmada.xml", signed_seed_xml.encode("utf-8"), "text/xml")},
            timeout=self.environment.timeout,
        )
        self._raise_for_status(response, "validando semilla DGII")
        data = self._response_data(response)
        token = self._first(data, "token", "Token", "access_token", "accessToken")
        if not token:
            raise ECFValidationError("DGII no retorno token de autenticacion.")
        expires_in = self._int_or_default(self._first(data, "expiraEn", "expires_in", "expiresIn"), self.default_expires_in)
        return DGIIRESTToken(value=str(token), expires_in=expires_in)

    def _url(self, path: str) -> str:
        return f"{self.environment.auth_base_url}{path}"

    def _cache_key(self, certificate_path: str, issuer_rnc: str | None) -> str:
        raw = f"{self.environment.name}:{issuer_rnc or ''}:{certificate_path}"
        return "dgii-rest-token:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _response_data(self, response: requests.Response) -> Any:
        text = response.text.strip()
        if not text:
            return {}
        try:
            return response.json()
        except ValueError:
            if text.startswith("<"):
                return {"xml": text}
            return {"valor": text}

    def _raise_for_status(self, response: requests.Response, action: str) -> None:
        if response.status_code >= 400:
            raise ECFValidationError(f"Error DGII REST {action}: HTTP {response.status_code}.")

    def _first(self, data: Any, *keys: str):
        if not isinstance(data, dict):
            return None
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            if key in data:
                return data[key]
            if key.lower() in lowered:
                return lowered[key.lower()]
        if len(data) == 1:
            only_value = next(iter(data.values()))
            if isinstance(only_value, str) and (only_value.strip().startswith("<") or len(keys) == 1):
                return only_value
        return None

    def _int_or_default(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
