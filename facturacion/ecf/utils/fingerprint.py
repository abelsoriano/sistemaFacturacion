"""Stable submission fingerprints shared by production and certification flows."""

import hashlib

from facturacion.ecf.utils.text import digits_only


def submission_fingerprint(*, issuer_rnc: str, encf: str, signed_xml: str) -> str:
    payload = "\n".join(
        [
            digits_only(issuer_rnc) or issuer_rnc,
            encf,
            signed_xml or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
