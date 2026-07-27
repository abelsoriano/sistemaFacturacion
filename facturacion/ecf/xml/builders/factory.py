"""Factory for resolving XML builders by e-CF type."""

from facturacion.ecf.exceptions import UnsupportedECFTypeError
from facturacion.ecf.xml.builders.base import BaseECFBuilder
from facturacion.ecf.xml.builders.invoice import E31XMLBuilder, E32XMLBuilder, E33XMLBuilder, E34XMLBuilder


class ECFBuilderFactory:
    """Resolve a concrete XML builder for an e-CF type."""

    builders: dict[str, type[BaseECFBuilder]] = {
        E31XMLBuilder.supported_type: E31XMLBuilder,
        E32XMLBuilder.supported_type: E32XMLBuilder,
        E33XMLBuilder.supported_type: E33XMLBuilder,
        E34XMLBuilder.supported_type: E34XMLBuilder,
        # Certification-only e-CF types reuse the generic invoice serializer path.
        # This keeps the XML construction inside the existing fiscal engine while
        # avoiding a parallel template generator for DGII certification scenarios.
        "41": E31XMLBuilder,
        "43": E31XMLBuilder,
        "44": E31XMLBuilder,
        "45": E31XMLBuilder,
        "46": E31XMLBuilder,
        "47": E31XMLBuilder,
    }

    def get(self, ecf_type: str) -> BaseECFBuilder:
        """Return a builder instance for the requested e-CF type."""
        builder_class = self.builders.get(ecf_type)
        if not builder_class:
            raise UnsupportedECFTypeError(f"Tipo e-CF no soportado para XML: {ecf_type}")
        return builder_class()
