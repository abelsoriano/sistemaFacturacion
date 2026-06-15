"""Normalize DGII SOAP responses into typed DTOs."""

from __future__ import annotations

import json
from typing import Any

from lxml import etree
from zeep.helpers import serialize_object

from facturacion.ecf.soap.responses.dgii import DGIIStatusResponse, DGIISubmissionResponse


class DGIISOAPResponseParser:
    """Parse DGII SOAP results regardless of zeep's concrete return shape."""

    accepted_values = {"aceptado", "aceptado condicional"}
    rejected_values = {"rechazado"}
    processing_values = {"en proceso", "procesando", "pendiente"}
    not_found_values = {"no encontrado"}

    def parse_submission(self, response: Any) -> DGIISubmissionResponse:
        """Parse reception response and extract TrackID."""
        data = self._to_data(response)
        track_id = self._first(data, "trackId", "trackID", "TrackId", "trackid", "numeroRespuesta")
        status = self._first(data, "estado", "status", default="pending")
        code = self._first(data, "codigo", "code")
        messages = self._messages(data)

        return DGIISubmissionResponse(
            track_id=str(track_id) if track_id is not None else None,
            status=str(status),
            code=self._int_or_none(code),
            messages=messages,
            raw=data,
        )

    def parse_status(self, response: Any) -> DGIIStatusResponse:
        """Parse status response and normalize DGII state."""
        data = self._to_data(response)
        status = str(self._first(data, "estado", "status", default="pending"))
        code = self._first(data, "codigo", "code")
        track_id = self._first(data, "trackId", "TrackId", "trackid")

        return DGIIStatusResponse(
            track_id=str(track_id) if track_id is not None else None,
            status=status,
            normalized_status=self.normalize_status(status, code),
            code=self._int_or_none(code),
            rnc=self._first(data, "rnc", "rncEmisor"),
            encf=self._first(data, "eNCF", "encf", "ncfElectronico"),
            sequence_used=self._bool_or_none(self._first(data, "secuenciaUtilizada")),
            received_at=self._first(data, "fechaRecepcion"),
            messages=self._messages(data),
            raw=data,
        )

    def normalize_status(self, status: str, code: Any = None) -> str:
        """Map DGII status values to local document statuses."""
        value = (status or "").strip().lower()
        numeric_code = self._int_or_none(code)
        if value in self.accepted_values or numeric_code in (1, 4):
            return "accepted"
        if value in self.rejected_values or numeric_code == 2:
            return "rejected"
        if value in self.processing_values or numeric_code == 3:
            return "processing"
        if value in self.not_found_values or numeric_code == 0:
            return "pending"
        return "error"

    def _to_data(self, response: Any) -> Any:
        if isinstance(response, (dict, list)):
            return response
        if isinstance(response, str):
            return self._parse_string(response)
        return serialize_object(response)

    def _parse_string(self, response: str) -> Any:
        text = response.strip()
        if not text:
            return {}
        if text.startswith("{") or text.startswith("["):
            return json.loads(text)
        if text.startswith("<"):
            root = etree.fromstring(text.encode("utf-8"))
            return self._xml_to_dict(root)
        return {"value": text}

    def _xml_to_dict(self, node: etree._Element) -> dict[str, Any]:
        children = list(node)
        if not children:
            return {self._tag(node): node.text}
        data: dict[str, Any] = {}
        for child in children:
            tag = self._tag(child)
            child_data = self._xml_to_dict(child)
            value = child_data.get(tag) if list(child) == [] else child_data
            if tag in data:
                if not isinstance(data[tag], list):
                    data[tag] = [data[tag]]
                data[tag].append(value)
            else:
                data[tag] = value
        return data

    def _tag(self, node: etree._Element) -> str:
        return etree.QName(node).localname

    def _first(self, data: Any, *keys: str, default=None):
        if not isinstance(data, dict):
            return default
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            if key in data:
                return data[key]
            if key.lower() in lowered:
                return lowered[key.lower()]
        return default

    def _messages(self, data: Any) -> list[dict[str, Any]]:
        messages = self._first(data, "mensajes", "messages", default=[])
        if messages is None:
            return []
        if isinstance(messages, dict):
            return [messages]
        if isinstance(messages, list):
            return [msg if isinstance(msg, dict) else {"valor": str(msg)} for msg in messages]
        return [{"valor": str(messages)}]

    def _int_or_none(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _bool_or_none(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        return str(value).strip().lower() in {"true", "1", "si", "sí"}
