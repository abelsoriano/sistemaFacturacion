"""DGII e-CF REST client facade."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings

from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.rest.auth import DGIIRESTAuthClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironment, DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.responses import DGIIRESTCallResult


class DGIIRESTClient:
    """Facade over DGII REST endpoints used by real pre-certification flows."""

    submit_path = "/api/Recepcion/ECF"
    status_path = "/api/ConsultaResultado"
    trackids_path = "/api/ConsultaTrackIds"
    rfce_path = "/api/RecepcionFC"

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
        paths = getattr(settings, "ECF_DGII_REST_PATHS", {})
        self.submit_path = paths.get("reception", self.submit_path)
        self.status_path = paths.get("status", self.status_path)
        self.trackids_path = paths.get("trackids", self.trackids_path)
        self.rfce_path = paths.get("rfce", self.rfce_path)

    def submit_ecf(
        self,
        *,
        signed_xml_content: str,
        encf: str,
        issuer_rnc: str,
        certificate_path: str,
        certificate_password: str | bytes | None,
        filename: str | None = None,
    ) -> DGIIRESTCallResult:
        token = self.auth_client.get_token(certificate_path, certificate_password, issuer_rnc=issuer_rnc)
        url = self._url(self.environment.reception_base_url, self.submit_path)
        upload_filename = filename or f"{encf}.xml"
        response = self.session.post(
            url,
            headers={"Authorization": token.authorization_header},
            files={"xml": (upload_filename, signed_xml_content.encode("utf-8"), "text/xml")},
            data={"rncEmisor": issuer_rnc, "eNCF": encf},
            timeout=self.environment.timeout,
        )
        return self._result(response, request_xml=signed_xml_content, url=url, encf=encf)

    def submit_rfce(
        self,
        *,
        signed_xml_content: str,
        encf: str,
        issuer_rnc: str,
        certificate_path: str,
        certificate_password: str | bytes | None,
        filename: str | None = None,
        multipart_field: str | None = None,
        content_type: str | None = None,
    ) -> DGIIRESTCallResult:
        if not self.environment.rfce_base_url:
            raise ECFValidationError("No hay URL REST RFCE DGII configurada.")
        token = self.auth_client.get_token(certificate_path, certificate_password, issuer_rnc=issuer_rnc)
        url = self._url(self.environment.rfce_base_url, self.rfce_path)
        upload_filename = filename or f"{issuer_rnc}{encf}.xml"
        field_name = multipart_field or getattr(settings, "ECF_DGII_RFCE_MULTIPART_FIELD", "xml")
        upload_content_type = content_type or getattr(settings, "ECF_DGII_RFCE_CONTENT_TYPE", "text/xml")
        response = self.session.post(
            url,
            headers={"Authorization": token.authorization_header},
            files={field_name: (upload_filename, signed_xml_content.encode("utf-8"), upload_content_type)},
            data={"rncEmisor": issuer_rnc, "eNCF": encf},
            timeout=self.environment.timeout,
        )
        return self._result(response, request_xml=signed_xml_content, url=url, encf=encf)

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

    def _result(
        self,
        response: requests.Response,
        *,
        request_xml: str | None,
        url: str | None = None,
        encf: str | None = None,
    ) -> DGIIRESTCallResult:
        if response.status_code >= 400:
            raise DGIIRESTHTTPError(response=response, url=url or response.url, encf=encf)
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


class DGIIRESTHTTPError(ECFValidationError):
    """HTTP error from DGII with sanitized diagnostics for certification retries."""

    safe_header_names = {
        "allow",
        "content-type",
        "request-context",
        "date",
        "server",
    }

    def __init__(self, *, response: requests.Response, url: str | None = None, encf: str | None = None) -> None:
        self.status_code = response.status_code
        self.url = url or response.url
        self.encf = encf or ""
        self.response_text = (response.text or "").strip()
        self.response_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() in self.safe_header_names
        }
        super().__init__(f"Error invocando REST DGII: HTTP {self.status_code}.")

    def as_safe_payload(self) -> dict:
        return {
            "status_code": self.status_code,
            "url": self.url,
            "encf": self.encf,
            "response_text": self.response_text,
            "response_headers": self.response_headers,
        }
