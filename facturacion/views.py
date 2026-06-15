"""Legacy compatibility facade for selected view exports.

New code should import from facturacion.api.views.* directly.
"""

from facturacion.api.views.credit_notes import CreditNoteViewSet
from facturacion.api.views.ecf_runtime import ElectronicFiscalDocumentViewSet
from facturacion.api.views.invoices import InvoiceViewSet
from facturacion.api.views.reports import DashboardView
from facturacion.api.views.sales_legacy import SaleCreateView, SaleListView, SalesUpdateDeleteView
from facturacion.ecf.queues import enqueue_check_status, enqueue_retry_submission


__all__ = [
    "CreditNoteViewSet",
    "DashboardView",
    "ElectronicFiscalDocumentViewSet",
    "InvoiceViewSet",
    "SaleCreateView",
    "SaleListView",
    "SalesUpdateDeleteView",
    "enqueue_check_status",
    "enqueue_retry_submission",
]
