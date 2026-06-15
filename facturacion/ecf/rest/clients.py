"""DGII e-CF REST client facade."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.rest.auth import DGIIRESTAuthClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironment, DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.responses import DGIIRESTCallResult


class DGIIRESTClient:
    """Facade over DGII REST endpoints used by real pre-certification flows."""

    submit_path = "/api/Recepcion/ECF"
    status_path = "/api/ConsultaResultado"
    trackids_path = "/api/ConsultaTrackIds"

    def __init__(
        self,
        environment: DGIIRESTEnvironment | None = None,
        environment_resolver: DGIIRESTEnvironmentResolver | None = None,
        auth_client: DGIIRESTAuthClient | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.environment = environment or (environment_resolver or DGIIRESTEnvironmentResolver()).resolve()
        self.session = session or self._build_session()
        self.auth_client = auth_client or DGIIRESTAuthClient(environment=self.environment, session=self.session)

    def submit_ecf(
        self,
        *,
        signed_xml_content: str,
        encf: str,
        issuer_rnc: str,
        certificate_path: str,
        certificate_password: str | bytes | None,
    ) -> DGIIRESTCallResult:
        token = self.auth_client.get_token(certificate_path, certificate_password, issuer_rnc=issuer_rnc)
        response = self.session.post(
            self._url(self.environment.reception_base_url, self.submit_path),
            headers={"Authorization": token.authorization_header},
            files={"xml": (f"{encf}.xml", signed_xml_content.encode("utf-8"), "text/xml")},
            data={"rncEmisor": issuer_rnc, "eNCF": encf},
            timeout=self.environment.timeout,
        )
        return self._result(response, request_xml=signed_xml_content)

    def query_status(
        self,
        *,
        track_id: str,
        certificate_path: str,
        certificate_password: str | bytes | None,
        issuer_rnc: str | None = None,
    ) -> DGIIRESTCallResult:
        token = self.auth_client.get_token(certificate_path, certificate_password, issuer_rnc=issuer_rnc)
        response = self.session.get(
            self._url(self.environment.status_base_url, self.status_path),
            headers={"Authorization": token.authorization_header},
            params={"trackId": track_id},
            timeout=self.environment.timeout,
        )
        return self._result(response, request_xml=None)

    def query_trackids(
        self,
        *,
        issuer_rnc: str,
        encf: str,
        certificate_path: str,
        certificate_password: str | bytes | None,
    ) -> DGIIRESTCallResult:
        if not self.environment.trackids_base_url:
            raise ECFValidationError("No hay URL REST de consulta TrackIDs DGII configurada.")
        token = self.auth_client.get_token(certificate_path, certificate_password, issuer_rnc=issuer_rnc)
        response = self.session.get(
            self._url(self.environment.trackids_base_url, self.trackids_path),
            headers={"Authorization": token.authorization_header},
            params={"rncEmisor": issuer_rnc, "eNCF": encf},
            timeout=self.environment.timeout,
        )
        return self._result(response, request_xml=None)

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.verify = self.environment.verify_tls
        retry = Retry(
            total=self.environment.retries,
            connect=self.environment.retries,
            read=self.environment.retries,
            status=self.environment.retries,
            backoff_factor=self.environment.retry_backoff,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _result(self, response: requests.Response, *, request_xml: str | None) -> DGIIRESTCallResult:
        if response.status_code >= 400:
            raise ECFValidationError(f"Error invocando REST DGII: HTTP {response.status_code}.")
        return DGIIRESTCallResult(
            result=self._response_data(response),
            request_xml=request_xml,
            response_xml=response.text,
            status_code=response.status_code,
        )

    def _response_data(self, response: requests.Response) -> Any:
        text = response.text.strip()
        if not text:
            return {}
        try:
            return response.json()
        except ValueError:
            if text.startswith("<"):
                return text
            return {"valor": text}

    def _url(self, base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"
