"""Factory for resolving XML builders by e-CF type."""

from facturacion.ecf.exceptions import UnsupportedECFTypeError
from facturacion.ecf.xml.builders.base import BaseECFBuilder
from facturacion.ecf.xml.builders.invoice import E31XMLBuilder, E32XMLBuilder, E34XMLBuilder


class ECFBuilderFactory:
    """Resolve a concrete XML builder for an e-CF type."""

    builders: dict[str, type[BaseECFBuilder]] = {
        E31XMLBuilder.supported_type: E31XMLBuilder,
        E32XMLBuilder.supported_type: E32XMLBuilder,
        E34XMLBuilder.supported_type: E34XMLBuilder,
    }

    def get(self, ecf_type: str) -> BaseECFBuilder:
        """Return a builder instance for the requested e-CF type."""
        builder_class = self.builders.get(ecf_type)
        if not builder_class:
            raise UnsupportedECFTypeError(f"Tipo e-CF no soportado para XML: {ecf_type}")
        return builder_class()
