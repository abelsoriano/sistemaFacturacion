"""Base XML builder classes for DGII e-CF documents."""

from abc import ABC, abstractmethod

from lxml import etree

from facturacion.ecf.mappers.invoice_mapper import ECFPayload


class BaseECFBuilder(ABC):
    """Base class for type-specific e-CF XML builders."""

    supported_type: str

    @abstractmethod
    def build(self, payload: ECFPayload) -> etree._Element:
        """Build an XML tree for a normalized e-CF payload."""

