"""Builders for invoice-like e-CF types E31, E32 and E34."""

from lxml import etree

from facturacion.ecf.mappers.invoice_mapper import ECFPayload
from facturacion.ecf.xml.builders.base import BaseECFBuilder
from facturacion.ecf.xml.serializers.e_cf_serializer import ECFXMLSerializer


class E31XMLBuilder(BaseECFBuilder):
    """Build XML for Factura de Crédito Fiscal Electrónica."""

    supported_type = "31"

    def __init__(self, serializer: ECFXMLSerializer | None = None) -> None:
        self.serializer = serializer or ECFXMLSerializer()

    def build(self, payload: ECFPayload) -> etree._Element:
        return self.serializer.serialize(payload)


class E32XMLBuilder(BaseECFBuilder):
    """Build XML for Factura de Consumo Electrónica."""

    supported_type = "32"

    def __init__(self, serializer: ECFXMLSerializer | None = None) -> None:
        self.serializer = serializer or ECFXMLSerializer()

    def build(self, payload: ECFPayload) -> etree._Element:
        return self.serializer.serialize(payload)


class E34XMLBuilder(BaseECFBuilder):
    """Build XML for Nota de Crédito Electrónica."""

    supported_type = "34"

    def __init__(self, serializer: ECFXMLSerializer | None = None) -> None:
        self.serializer = serializer or ECFXMLSerializer()

    def build(self, payload: ECFPayload) -> etree._Element:
        return self.serializer.serialize(payload)
