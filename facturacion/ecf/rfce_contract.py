"""Local RFCE contract helpers for DGII certification.

RFCE submission remains blocked until an official XSD or example XML is placed
under ``facturacion/ecf/schemas/rfce/`` and the generator is validated against it.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings


RFCE_CONTRACT_MISSING_MESSAGE = "No se puede enviar RFCE hasta cargar XSD/estructura oficial RFCE."
RFCE_SCHEMA_DIR = Path(settings.BASE_DIR) / "facturacion" / "ecf" / "schemas" / "rfce"
RFCE_XSD_PATTERNS = ("*.xsd", "*.XSD")
RFCE_EXAMPLE_PATTERNS = ("*.xml", "*.XML")


def rfce_schema_dir() -> Path:
    return RFCE_SCHEMA_DIR


def rfce_xsd_files() -> list[Path]:
    return _contract_files(RFCE_XSD_PATTERNS)


def rfce_example_files() -> list[Path]:
    return _contract_files(RFCE_EXAMPLE_PATTERNS)


def has_rfce_contract() -> bool:
    return bool(rfce_xsd_files() or rfce_example_files())


def _contract_files(patterns: tuple[str, ...]) -> list[Path]:
    if not RFCE_SCHEMA_DIR.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in RFCE_SCHEMA_DIR.glob(pattern) if path.is_file())
    return sorted(files)
