"""Base Zeep SOAP client with controlled retries, timeouts and history capture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zeep import Client, Settings
from zeep.exceptions import Error as ZeepError
from zeep.plugins import HistoryPlugin
from zeep.transports import Transport

from facturacion.ecf.exceptions import ECFValidationError


@dataclass(frozen=True)
class SOAPCallResult:
    """Raw SOAP call result plus serialized request/response envelopes."""

    result: Any
    request_xml: str | None
    response_xml: str | None


class BaseZeepSOAPClient:
    """Small wrapper around Zeep with auditable envelopes and resilient transport."""

    def __init__(
        self,
        wsdl_url: str,
        timeout: int = 30,
        retries: int = 3,
        retry_backoff: float = 0.5,
        verify_tls: bool = True,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.history = HistoryPlugin()
        self.session = self._build_session(retries, retry_backoff, verify_tls, headers)
        self.transport = Transport(session=self.session, timeout=timeout, operation_timeout=timeout)
        self.client = Client(
            wsdl=wsdl_url,
            transport=self.transport,
            settings=Settings(strict=True, xml_huge_tree=False),
            plugins=[self.history],
        )

    def call(self, operation_name: str, **payload) -> SOAPCallResult:
        """Call a SOAP operation and capture envelopes for persistence."""
        try:
            operation = getattr(self.client.service, operation_name)
        except AttributeError as exc:
            raise ECFValidationError(f"Operación SOAP no disponible en WSDL: {operation_name}") from exc

        try:
            result = operation(**payload)
        except (requests.RequestException, ZeepError, Exception) as exc:
            raise ECFValidationError(f"Error invocando SOAP DGII operación {operation_name}.") from exc

        return SOAPCallResult(
            result=result,
            request_xml=self._envelope_to_string(self.history.last_sent),
            response_xml=self._envelope_to_string(self.history.last_received),
        )

    def _build_session(
        self,
        retries: int,
        retry_backoff: float,
        verify_tls: bool,
        headers: dict[str, str] | None,
    ) -> requests.Session:
        session = requests.Session()
        session.verify = verify_tls
        if headers:
            session.headers.update(headers)

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=retry_backoff,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _envelope_to_string(self, envelope_entry: dict[str, Any] | None) -> str | None:
        if not envelope_entry:
            return None
        envelope = envelope_entry.get("envelope")
        if envelope is None:
            return None
        return etree.tostring(
            envelope,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
        ).decode("utf-8")

