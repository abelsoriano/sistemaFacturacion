"""Typed responses returned by DGII REST services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DGIIRESTCallResult:
    """Raw REST call result plus request/response metadata for audit trails."""

    result: Any
    request_xml: str | None
    response_xml: str | None
    status_code: int


@dataclass(frozen=True)
class DGIIRESTToken:
    """Bearer token returned by DGII authentication."""

    value: str
    expires_in: int

    @property
    def authorization_header(self) -> str:
        return f"Bearer {self.value}"
