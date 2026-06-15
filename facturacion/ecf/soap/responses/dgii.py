"""Typed responses returned by DGII SOAP services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DGIISubmissionResponse:
    """Normalized response from DGII e-CF reception."""

    track_id: str | None
    status: str
    code: int | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None


@dataclass(frozen=True)
class DGIIStatusResponse:
    """Normalized response from DGII result/status query."""

    track_id: str | None
    status: str
    normalized_status: str
    code: int | None = None
    rnc: str | None = None
    encf: str | None = None
    sequence_used: bool | None = None
    received_at: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None

