"""Business validations before generating DGII XML."""

from decimal import Decimal

from facturacion.models import ElectronicFiscalDocument
from facturacion.ecf.constants import SUPPORTED_XML_TYPES
from facturacion.ecf.exceptions import ECFValidationError
from facturacion.ecf.utils.decimals import quantize_money
from facturacion.ecf.utils.text import digits_only


class ECFBusinessValidator:
    """Validate local invoice data before XML serialization."""

    def validate(self, document: ElectronicFiscalDocument) -> None:
        """Raise ECFValidationError when the document cannot be serialized."""
        errors: list[str] = []
        source = document.credit_note if document.credit_note_id else document.invoice

        if document.ecf_type not in SUPPORTED_XML_TYPES:
            errors.append(f"Tipo e-CF {document.ecf_type} no soportado para XML.")
        if not document.encf or len(document.encf) != 13 or not document.encf.startswith(f"E{document.ecf_type}"):
            errors.append("El e-NCF no corresponde al tipo e-CF del documento.")
        if document.ecf_type == "31":
            self._validate_credit_fiscal_buyer(document, errors)
            if not document.sequence.expiration_date:
                errors.append("E31 requiere FechaVencimientoSecuencia en la secuencia e-NCF.")
        if document.ecf_type == "34":
            if not document.credit_note_id:
                errors.append("E34 requiere nota de credito.")
            else:
                origin_invoice = document.credit_note.origin_invoice
                origin_document = getattr(origin_invoice, "electronic_document", None)
                if not origin_document:
                    errors.append("E34 requiere una factura origen con e-CF.")
                elif origin_document.fiscal_status != "accepted":
                    errors.append("E34 requiere que la factura origen este aceptada por DGII.")
                if origin_invoice.status == "cancelled":
                    errors.append("No se puede emitir E34 contra una factura comercial cancelada.")
                if not getattr(origin_document, "encf", None):
                    errors.append("E34 requiere e-NCF de la factura origen.")
        if not source or not source.details.exists():
            errors.append("El documento debe tener al menos un detalle.")
        if source and quantize_money(source.total) <= Decimal("0.00"):
            errors.append("El total del documento debe ser mayor a cero.")
        if source and quantize_money(source.tax) < Decimal("0.00"):
            errors.append("El ITBIS no puede ser negativo.")
        if not document.issuer.rnc or not digits_only(document.issuer.rnc):
            errors.append("El emisor debe tener RNC válido.")

        if errors:
            raise ECFValidationError(" ".join(errors))

    def _validate_credit_fiscal_buyer(self, document: ElectronicFiscalDocument, errors: list[str]) -> None:
        invoice = document.credit_note.origin_invoice if document.credit_note_id else document.invoice
        client = invoice.client
        if not client:
            errors.append("E31 requiere cliente.")
            return
        if not digits_only(client.ruc_ci):
            errors.append("E31 requiere RNC/Cédula del comprador.")
        if not client.name:
            errors.append("E31 requiere razón social del comprador.")
