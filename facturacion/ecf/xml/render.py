"""Render lxml trees into UTF-8 XML strings."""

from lxml import etree


def render_xml(root: etree._Element, pretty_print: bool = True) -> str:
    """Render an XML element to a UTF-8 document string."""
    xml_bytes = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=pretty_print,
        standalone=False,
    )
    return xml_bytes.decode("utf-8")

