"""DGII e-CF SOAP client facade."""

from __future__ import annotations

from facturacion.ecf.soap.auth import DGIIBearerToken
from facturacion.ecf.soap.clients.base import BaseZeepSOAPClient, SOAPCallResult
from facturacion.ecf.soap.environments import DGIISOAPEnvironment


class DGIISOAPClient:
    """Facade over DGII SOAP operations used by e-CF workflows."""

    def __init__(self, environment: DGIISOAPEnvironment, token: DGIIBearerToken) -> None:
        self.environment = environment
        self.headers = {
            "Authorization": token.authorization_header,
            "Accept": "text/xml, application/xml, application/soap+xml",
        }

    def submit_ecf(self, signed_xml_content: str, encf: str, issuer_rnc: str) -> SOAPCallResult:
        """Submit a signed e-CF XML to DGII and return raw SOAP response."""
        client = self._client(self.environment.reception_wsdl)
        return client.call(
            self.environment.submit_operation,
            xml=signed_xml_content,
            encf=encf,
            rncEmisor=issuer_rnc,
        )

    def query_status(self, track_id: str) -> SOAPCallResult:
        """Query DGII processing result by TrackID."""
        client = self._client(self.environment.status_wsdl)
        return client.call(
            self.environment.status_operation,
            trackId=track_id,
        )

    def query_trackids(self, issuer_rnc: str, encf: str) -> SOAPCallResult:
        """Query DGII TrackIDs associated with an e-NCF."""
        wsdl = self.environment.trackids_wsdl or self.environment.status_wsdl
        client = self._client(wsdl)
        return client.call(
            self.environment.trackids_operation,
            rncEmisor=issuer_rnc,
            encf=encf,
        )

    def _client(self, wsdl_url: str) -> BaseZeepSOAPClient:
        return BaseZeepSOAPClient(
            wsdl_url=wsdl_url,
            timeout=self.environment.timeout,
            retries=self.environment.retries,
            retry_backoff=self.environment.retry_backoff,
            verify_tls=self.environment.verify_tls,
            headers=self.headers,
        )

