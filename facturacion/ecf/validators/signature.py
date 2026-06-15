"""Cryptographic validation for signed e-CF XML documents."""

from __future__ import annotations

from lxml import etree
from signxml import XMLVerifier
from signxml.exceptions import InvalidSignature

from facturacion.ecf.certificates.loader import LoadedCertificate
from facturacion.ecf.exceptions import ECFValidationError


class ECFSignatureValidator:
    """Validate XMLDSig signatures using the expected certificate."""

    def validate(self, signed_xml_content: str, certificate: LoadedCertificate) -> None:
        """Raise ECFValidationError when the XML signature is invalid."""
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        try:
            XMLVerifier().verify(
                signed_xml_content.encode("utf-8"),
                x509_cert=certificate.certificate_pem,
                parser=parser,
            )
        except InvalidSignature as exc:
            raise ECFValidationError("La firma XMLDSig no es válida.") from exc
        except Exception as exc:
            raise ECFValidationError("No fue posible validar la firma XMLDSig.") from exc

