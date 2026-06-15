"""XMLDSig signing for DGII e-CF XML documents."""

from __future__ import annotations

from lxml import etree
from signxml import XMLSigner, methods
from signxml.algorithms import CanonicalizationMethod, DigestAlgorithm, SignatureMethod

from facturacion.ecf.certificates.loader import LoadedCertificate
from facturacion.ecf.constants import XMLDSIG_NAMESPACE
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.xml.render import render_xml


class ECFXMLSigner:
    """Sign e-CF XML with an enveloped XMLDSig SHA256 signature."""

    def sign(self, xml_content: str, certificate: LoadedCertificate) -> str:
        """Return signed XML, replacing any existing placeholder signature."""
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        try:
            root = etree.fromstring(xml_content.encode("utf-8"), parser)
        except etree.XMLSyntaxError as exc:
            raise ECFValidationError(f"XML inválido antes de firmar: {exc}") from exc

        self._remove_existing_signature(root)

        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm=SignatureMethod.RSA_SHA256,
            digest_algorithm=DigestAlgorithm.SHA256,
            c14n_algorithm=CanonicalizationMethod.CANONICAL_XML_1_0,
        )

        try:
            signed_root = signer.sign(
                root,
                key=certificate.private_key_pem,
                cert=certificate.certificate_pem,
            )
        except Exception as exc:
            raise ECFValidationError("No fue posible firmar el XML e-CF.") from exc

        return render_xml(signed_root)

    def _remove_existing_signature(self, root: etree._Element) -> None:
        signature_xpath = f".//{{{XMLDSIG_NAMESPACE}}}Signature"
        for signature in root.findall(signature_xpath):
            parent = signature.getparent()
            if parent is not None:
                parent.remove(signature)
