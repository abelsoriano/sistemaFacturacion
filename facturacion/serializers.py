"""Legacy compatibility facade for selected serializer exports.

New code should import from facturacion.api.serializers.* directly.
"""

from facturacion.api.serializers.ecf_runtime import (
    ElectronicFiscalDocumentSerializer,
    _effective_fiscal_status,
    _effective_job_status,
)
from facturacion.api.serializers.sales_legacy import SaleSerializer


__all__ = [
    "ElectronicFiscalDocumentSerializer",
    "SaleSerializer",
    "_effective_fiscal_status",
    "_effective_job_status",
]
