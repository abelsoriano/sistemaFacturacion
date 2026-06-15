"""Serialize normalized e-CF payloads into lxml elements."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from lxml import etree

from facturacion.ecf.constants import ECF_VERSION, XMLDSIG_NAMESPACE
from facturacion.ecf.mappers.invoice_mapper import ECFPayload
from facturacion.ecf.utils.decimals import format_money, format_unit_price


class ECFXMLSerializer:
    """Serialize e-CF payloads using the exact order expected by the DGII XSD."""

    def serialize(self, payload: ECFPayload) -> etree._Element:
        """Build and return the root ECF XML element."""
        root = etree.Element("ECF")
        self._append_header(root, payload)
        self._append_items(root, payload.items)
        self._append_modified_document(root, payload)
        etree.SubElement(root, "FechaHoraFirma").text = payload.signature_datetime
        if payload.include_signature_placeholder:
            self._append_signature_placeholder(root)
        return root

    def _append_header(self, root: etree._Element, payload: ECFPayload) -> None:
        encabezado = etree.SubElement(root, "Encabezado")
        etree.SubElement(encabezado, "Version").text = ECF_VERSION
        self._append_id_doc(encabezado, payload)
        self._append_issuer(encabezado, payload)
        self._append_buyer(encabezado, payload)
        self._append_totals(encabezado, payload)

    def _append_id_doc(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        id_doc = etree.SubElement(encabezado, "IdDoc")
        etree.SubElement(id_doc, "TipoeCF").text = payload.ecf_type
        etree.SubElement(id_doc, "eNCF").text = payload.encf
        if payload.ecf_type == "34":
            etree.SubElement(id_doc, "IndicadorNotaCredito").text = payload.credit_note_indicator or "0"
        if payload.ecf_type == "31" and payload.sequence_expiration_date:
            etree.SubElement(id_doc, "FechaVencimientoSecuencia").text = payload.sequence_expiration_date
        etree.SubElement(id_doc, "TipoIngresos").text = payload.income_type
        etree.SubElement(id_doc, "TipoPago").text = payload.payment_type

        if payload.ecf_type != "34":
            payment_table = etree.SubElement(id_doc, "TablaFormasPago")
            payment = etree.SubElement(payment_table, "FormaDePago")
            etree.SubElement(payment, "FormaPago").text = payload.payment_form
            etree.SubElement(payment, "MontoPago").text = format_money(payload.totals["amount_total"])

    def _append_issuer(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        issuer = payload.issuer
        emisor = etree.SubElement(encabezado, "Emisor")
        self._text(emisor, "RNCEmisor", issuer["rnc"])
        self._text(emisor, "RazonSocialEmisor", issuer["business_name"])
        self._text(emisor, "NombreComercial", issuer.get("trade_name"))
        self._text(emisor, "DireccionEmisor", issuer["address"])
        self._text(emisor, "Municipio", issuer.get("municipality"))
        self._text(emisor, "Provincia", issuer.get("province"))
        if issuer.get("phone"):
            phones = etree.SubElement(emisor, "TablaTelefonoEmisor")
            self._text(phones, "TelefonoEmisor", issuer["phone"])
        self._text(emisor, "CorreoEmisor", issuer.get("email"))
        self._text(emisor, "NumeroFacturaInterna", payload.internal_invoice_number)
        etree.SubElement(emisor, "FechaEmision").text = payload.issue_date

    def _append_buyer(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        buyer = payload.buyer
        comprador = etree.SubElement(encabezado, "Comprador")
        if payload.ecf_type == "31":
            self._text(comprador, "RNCComprador", buyer.get("rnc"))
            self._text(comprador, "RazonSocialComprador", buyer.get("business_name"))
        else:
            self._text(comprador, "RNCComprador", buyer.get("rnc"))
            self._text(comprador, "RazonSocialComprador", buyer.get("business_name"))
        self._text(comprador, "CorreoComprador", buyer.get("email"))
        self._text(comprador, "DireccionComprador", buyer.get("address"))
        self._text(comprador, "TelefonoAdicional", buyer.get("phone"))

    def _append_totals(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        totals = payload.totals
        totales = etree.SubElement(encabezado, "Totales")
        taxable_amount = totals["taxable_amount"]
        exempt_amount = totals["exempt_amount"]
        itbis_rate = totals["itbis_rate"]
        total_itbis = totals["total_itbis"]

        if taxable_amount > 0:
            etree.SubElement(totales, "MontoGravadoTotal").text = format_money(taxable_amount)
            if itbis_rate == Decimal("18.00"):
                etree.SubElement(totales, "MontoGravadoI1").text = format_money(taxable_amount)
            elif itbis_rate == Decimal("16.00"):
                etree.SubElement(totales, "MontoGravadoI2").text = format_money(taxable_amount)
            elif itbis_rate == Decimal("0.00"):
                etree.SubElement(totales, "MontoGravadoI3").text = format_money(taxable_amount)

        if exempt_amount > 0:
            etree.SubElement(totales, "MontoExento").text = format_money(exempt_amount)

        if taxable_amount > 0:
            if itbis_rate == Decimal("18.00"):
                etree.SubElement(totales, "ITBIS1").text = "18"
                etree.SubElement(totales, "TotalITBIS").text = format_money(total_itbis)
                etree.SubElement(totales, "TotalITBIS1").text = format_money(total_itbis)
            elif itbis_rate == Decimal("16.00"):
                etree.SubElement(totales, "ITBIS2").text = "16"
                etree.SubElement(totales, "TotalITBIS").text = format_money(total_itbis)
                etree.SubElement(totales, "TotalITBIS2").text = format_money(total_itbis)
            elif itbis_rate == Decimal("0.00"):
                etree.SubElement(totales, "ITBIS3").text = "0"
                etree.SubElement(totales, "TotalITBIS").text = format_money(total_itbis)
                etree.SubElement(totales, "TotalITBIS3").text = format_money(total_itbis)

        etree.SubElement(totales, "MontoTotal").text = format_money(totals["amount_total"])

    def _append_items(self, root: etree._Element, items: list[dict[str, Any]]) -> None:
        detalles = etree.SubElement(root, "DetallesItems")
        for item in items:
            item_node = etree.SubElement(detalles, "Item")
            etree.SubElement(item_node, "NumeroLinea").text = str(item["line_number"])
            if item.get("code"):
                codes = etree.SubElement(item_node, "TablaCodigosItem")
                code = etree.SubElement(codes, "CodigosItem")
                etree.SubElement(code, "TipoCodigo").text = "Interno"
                etree.SubElement(code, "CodigoItem").text = item["code"]
            etree.SubElement(item_node, "IndicadorFacturacion").text = item["billing_indicator"]
            etree.SubElement(item_node, "NombreItem").text = item["name"]
            etree.SubElement(item_node, "IndicadorBienoServicio").text = item["is_good_or_service"]
            self._text(item_node, "DescripcionItem", item.get("description"))
            etree.SubElement(item_node, "CantidadItem").text = format_money(item["quantity"])
            etree.SubElement(item_node, "PrecioUnitarioItem").text = format_unit_price(item["unit_price"])
            if item.get("discount") and item["discount"] > 0:
                etree.SubElement(item_node, "DescuentoMonto").text = format_money(item["discount"])
            etree.SubElement(item_node, "MontoItem").text = format_money(item["amount"])

    def _append_modified_document(self, root: etree._Element, payload: ECFPayload) -> None:
        if not payload.modified_document:
            return
        info = etree.SubElement(root, "InformacionReferencia")
        self._text(info, "NCFModificado", payload.modified_document.get("encf"))
        self._text(info, "FechaNCFModificado", payload.modified_document.get("issue_date"))
        self._text(info, "CodigoModificacion", payload.modified_document.get("code") or "3")
        self._text(info, "RazonModificacion", payload.modified_document.get("reason"))

    def _append_signature_placeholder(self, root: etree._Element) -> None:
        signature = etree.SubElement(root, f"{{{XMLDSIG_NAMESPACE}}}Signature")
        signature.append(etree.Comment("Placeholder: reemplazar en el modulo de firma digital."))

    def _text(self, parent: etree._Element, tag: str, value: Any) -> None:
        if value is not None and value != "":
            etree.SubElement(parent, tag).text = str(value)
