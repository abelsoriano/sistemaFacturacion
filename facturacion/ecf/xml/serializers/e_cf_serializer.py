"""Serialize normalized e-CF payloads into lxml elements."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from lxml import etree

from facturacion.ecf.constants import ECF_TYPE_RULES, ECF_VERSION, XMLDSIG_NAMESPACE, should_include_buyer
from facturacion.ecf.mappers.invoice_mapper import ECFPayload
from facturacion.ecf.utils.decimals import format_money, format_unit_price


EXPLICIT_ITBIS2_TYPES = {"31", "32", "33", "34", "41", "45"}
EXPLICIT_ITBIS3_TYPES = EXPLICIT_ITBIS2_TYPES | {"46"}


class ECFXMLSerializer:
    """Serialize e-CF payloads using the exact order expected by the DGII XSD."""

    def serialize(self, payload: ECFPayload) -> etree._Element:
        """Build and return the root ECF XML element."""
        root = etree.Element("ECF")
        self._append_header(root, payload)
        self._append_items(root, payload.items)
        self._append_discounts_or_surcharges(root, payload)
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
        if should_include_buyer(payload.ecf_type, payload.include_buyer):
            self._append_buyer(encabezado, payload)
        self._append_totals(encabezado, payload)

    def _append_id_doc(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        id_doc = etree.SubElement(encabezado, "IdDoc")
        etree.SubElement(id_doc, "TipoeCF").text = payload.ecf_type
        etree.SubElement(id_doc, "eNCF").text = payload.encf
        if (
            ECF_TYPE_RULES.get(payload.ecf_type, {}).get("allow_sequence_expiration_date", False)
            and payload.sequence_expiration_date
        ):
            etree.SubElement(id_doc, "FechaVencimientoSecuencia").text = payload.sequence_expiration_date
        id_doc_fields = payload.id_doc_fields or {}
        rules = ECF_TYPE_RULES.get(payload.ecf_type, {})
        self._text(
            id_doc,
            "IndicadorNotaCredito",
            payload.credit_note_indicator if rules.get("allow_credit_note_indicator", False) else None,
        )
        self._text(
            id_doc,
            "IndicadorNotaCredito",
            id_doc_fields.get("IndicadorNotaCredito")
            if rules.get("allow_credit_note_indicator", False)
            else None,
        )
        self._text(id_doc, "IndicadorEnvioDiferido", id_doc_fields.get("IndicadorEnvioDiferido"))
        self._text(id_doc, "IndicadorMontoGravado", id_doc_fields.get("IndicadorMontoGravado"))
        self._text(
            id_doc,
            "IndicadorServicioTodoIncluido",
            id_doc_fields.get("IndicadorServicioTodoIncluido")
            if rules.get("allow_service_all_included_indicator", False)
            else None,
        )
        self._text(
            id_doc,
            "TipoIngresos",
            payload.income_type if rules.get("allow_income_type", True) else None,
        )
        self._text(id_doc, "TipoPago", payload.payment_type)
        self._text(id_doc, "FechaLimitePago", id_doc_fields.get("FechaLimitePago"))
        self._text(
            id_doc,
            "TerminoPago",
            id_doc_fields.get("TerminoPago") if rules.get("allow_payment_term", True) else None,
        )

        payment_forms = payload.payment_forms
        if payment_forms is None and rules.get("allow_default_payment_forms", True):
            payment_forms = [{
                "form": payload.payment_form,
                "amount": payload.totals["amount_total"],
            }]
        if payment_forms:
            payment_table = etree.SubElement(id_doc, "TablaFormasPago")
            for payment_data in payment_forms:
                payment = etree.SubElement(payment_table, "FormaDePago")
                etree.SubElement(payment, "FormaPago").text = str(payment_data["form"])
                etree.SubElement(payment, "MontoPago").text = format_money(payment_data["amount"])

    def _append_issuer(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        issuer = payload.issuer
        emisor = etree.SubElement(encabezado, "Emisor")
        self._text(emisor, "RNCEmisor", issuer["rnc"])
        self._text(emisor, "RazonSocialEmisor", issuer["business_name"])
        self._text(emisor, "NombreComercial", issuer.get("trade_name"))
        self._text(emisor, "DireccionEmisor", issuer["address"])
        municipality_tag = "MunicipioEmisor" if payload.use_issuer_location_emisor_tags else "Municipio"
        province_tag = "ProvinciaEmisor" if payload.use_issuer_location_emisor_tags else "Provincia"
        self._text(emisor, municipality_tag, issuer.get("municipality"))
        self._text(emisor, province_tag, issuer.get("province"))
        issuer_phones = issuer.get("phones") or ([issuer.get("phone")] if issuer.get("phone") else [])
        if issuer_phones:
            phones = etree.SubElement(emisor, "TablaTelefonoEmisor")
            for phone in issuer_phones:
                self._text(phones, "TelefonoEmisor", phone)
        self._text(emisor, "CorreoEmisor", issuer.get("email"))
        self._text(emisor, "WebSite", issuer.get("website"))
        self._text(emisor, "ActividadEconomica", issuer.get("economic_activity"))
        self._text(emisor, "CodigoVendedor", issuer.get("seller_code"))
        self._text(emisor, "NumeroFacturaInterna", payload.internal_invoice_number)
        self._text(emisor, "NumeroPedidoInterno", issuer.get("order_number"))
        self._text(emisor, "ZonaVenta", issuer.get("sales_zone"))
        self._text(emisor, "RutaVenta", issuer.get("sales_route"))
        self._text(emisor, "InformacionAdicionalEmisor", issuer.get("additional_information"))
        etree.SubElement(emisor, "FechaEmision").text = payload.issue_date

    def _append_buyer(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        buyer = payload.buyer
        comprador = etree.SubElement(encabezado, "Comprador")
        if buyer.get("foreign_identifier"):
            self._text(comprador, "IdentificadorExtranjero", buyer.get("foreign_identifier"))
            self._text(comprador, "RazonSocialComprador", buyer.get("business_name"))
        elif payload.ecf_type == "31":
            self._text(comprador, "RNCComprador", buyer.get("rnc"))
            self._text(comprador, "RazonSocialComprador", buyer.get("business_name"))
        else:
            self._text(comprador, "RNCComprador", buyer.get("rnc"))
            self._text(comprador, "RazonSocialComprador", buyer.get("business_name"))
        self._text(comprador, "ContactoComprador", buyer.get("contact"))
        self._text(comprador, "CorreoComprador", buyer.get("email"))
        self._text(comprador, "DireccionComprador", buyer.get("address"))
        self._text(comprador, "MunicipioComprador", buyer.get("municipality"))
        self._text(comprador, "ProvinciaComprador", buyer.get("province"))
        self._text(comprador, "FechaEntrega", buyer.get("delivery_date"))
        self._text(comprador, "ContactoEntrega", buyer.get("delivery_contact"))
        self._text(comprador, "DireccionEntrega", buyer.get("delivery_address"))
        self._text(comprador, "TelefonoAdicional", buyer.get("phone"))
        self._text(comprador, "FechaOrdenCompra", buyer.get("purchase_order_date"))
        self._text(comprador, "NumeroOrdenCompra", buyer.get("purchase_order_number"))
        self._text(comprador, "CodigoInternoComprador", buyer.get("internal_code"))

    def _append_totals(self, encabezado: etree._Element, payload: ECFPayload) -> None:
        totals = payload.totals
        totales = etree.SubElement(encabezado, "Totales")
        if totals.get("explicit_fiscal_totals"):
            self._append_explicit_totals(totales, totals, payload.ecf_type)
            return

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

    def _append_explicit_totals(
        self,
        totales: etree._Element,
        totals: dict[str, Decimal],
        ecf_type: str,
    ) -> None:
        taxable_total = totals.get("taxable_amount", Decimal("0.00"))
        exempt_amount = totals.get("exempt_amount", Decimal("0.00"))
        total_itbis = totals.get("total_itbis", Decimal("0.00"))
        amount_total = totals["amount_total"]

        taxable_i1 = totals.get("taxable_amount_i1", Decimal("0.00"))
        taxable_i2 = totals.get("taxable_amount_i2", Decimal("0.00"))
        taxable_i3 = totals.get("taxable_amount_i3", Decimal("0.00"))
        total_itbis1 = totals.get("total_itbis1", Decimal("0.00"))
        total_itbis2 = totals.get("total_itbis2", Decimal("0.00"))
        total_itbis3 = totals.get("total_itbis3", Decimal("0.00"))
        additional_tax = totals.get("additional_tax", Decimal("0.00"))
        non_billable_amount = totals.get("non_billable_amount", Decimal("0.00"))
        present_fields = totals.get("present_total_fields", {})

        if taxable_total > 0:
            etree.SubElement(totales, "MontoGravadoTotal").text = format_money(taxable_total)
        if taxable_i1 > 0:
            etree.SubElement(totales, "MontoGravadoI1").text = format_money(taxable_i1)
        if taxable_i2 > 0:
            etree.SubElement(totales, "MontoGravadoI2").text = format_money(taxable_i2)
        if taxable_i3 > 0:
            etree.SubElement(totales, "MontoGravadoI3").text = format_money(taxable_i3)
        if exempt_amount > 0:
            etree.SubElement(totales, "MontoExento").text = format_money(exempt_amount)

        if taxable_i1 > 0:
            etree.SubElement(totales, "ITBIS1").text = str(totals.get("itbis_rate1") or "18")
        if (
            ecf_type in EXPLICIT_ITBIS2_TYPES
            and (taxable_i2 > 0 or present_fields.get("ITBIS2"))
        ):
            etree.SubElement(totales, "ITBIS2").text = str(totals.get("itbis_rate2") or "16")
        if (
            ecf_type in EXPLICIT_ITBIS3_TYPES
            and (taxable_i3 > 0 or present_fields.get("ITBIS3"))
        ):
            etree.SubElement(totales, "ITBIS3").text = str(totals.get("itbis_rate3") or "0")
        if total_itbis > 0 or present_fields.get("TotalITBIS"):
            etree.SubElement(totales, "TotalITBIS").text = format_money(total_itbis)
        if total_itbis1 > 0 or present_fields.get("TotalITBIS1"):
            etree.SubElement(totales, "TotalITBIS1").text = format_money(total_itbis1)
        if total_itbis2 > 0 or present_fields.get("TotalITBIS2"):
            etree.SubElement(totales, "TotalITBIS2").text = format_money(total_itbis2)
        if total_itbis3 > 0 or present_fields.get("TotalITBIS3"):
            etree.SubElement(totales, "TotalITBIS3").text = format_money(total_itbis3)
        if additional_tax > 0:
            etree.SubElement(totales, "MontoImpuestoAdicional").text = format_money(additional_tax)

        etree.SubElement(totales, "MontoTotal").text = format_money(amount_total)
        if non_billable_amount or present_fields.get("MontoNoFacturable"):
            etree.SubElement(totales, "MontoNoFacturable").text = format_money(non_billable_amount)
        amount_period = totals.get("amount_period", Decimal("0.00"))
        value_to_pay = totals.get("value_to_pay", Decimal("0.00"))
        total_itbis_retained = totals.get("total_itbis_retained", Decimal("0.00"))
        total_isr_retention = totals.get("total_isr_retention", Decimal("0.00"))
        if amount_period > 0 or present_fields.get("MontoPeriodo"):
            etree.SubElement(totales, "MontoPeriodo").text = format_money(amount_period)
        if value_to_pay > 0 or present_fields.get("ValorPagar"):
            etree.SubElement(totales, "ValorPagar").text = format_money(value_to_pay)
        if total_itbis_retained > 0 or present_fields.get("TotalITBISRetenido"):
            etree.SubElement(totales, "TotalITBISRetenido").text = format_money(total_itbis_retained)
        if total_isr_retention > 0 or present_fields.get("TotalISRRetencion"):
            etree.SubElement(totales, "TotalISRRetencion").text = format_money(total_isr_retention)

    def _append_items(self, root: etree._Element, items: list[dict[str, Any]]) -> None:
        detalles = etree.SubElement(root, "DetallesItems")
        for item in items:
            item_node = etree.SubElement(detalles, "Item")
            etree.SubElement(item_node, "NumeroLinea").text = str(item["line_number"])
            if item.get("code"):
                codes = etree.SubElement(item_node, "TablaCodigosItem")
                item_codes = item.get("codes") or [{"type": "Interno", "value": item["code"]}]
                for item_code in item_codes:
                    code = etree.SubElement(codes, "CodigosItem")
                    etree.SubElement(code, "TipoCodigo").text = item_code["type"]
                    etree.SubElement(code, "CodigoItem").text = item_code["value"]
            etree.SubElement(item_node, "IndicadorFacturacion").text = item["billing_indicator"]
            self._append_item_retention(item_node, item)
            etree.SubElement(item_node, "NombreItem").text = item["name"]
            etree.SubElement(item_node, "IndicadorBienoServicio").text = item["is_good_or_service"]
            self._text(item_node, "DescripcionItem", item.get("description"))
            etree.SubElement(item_node, "CantidadItem").text = item.get("quantity_text") or format_money(item["quantity"])
            self._text(item_node, "UnidadMedida", item.get("unit_measure"))
            if item.get("quantity_reference") is not None:
                etree.SubElement(item_node, "CantidadReferencia").text = (
                    item.get("quantity_reference_text") or format_money(item["quantity_reference"])
                )
            self._text(item_node, "UnidadReferencia", item.get("reference_unit"))
            if item.get("alcohol_degrees") is not None:
                etree.SubElement(item_node, "GradosAlcohol").text = (
                    item.get("alcohol_degrees_text") or format_money(item["alcohol_degrees"])
                )
            if item.get("reference_unit_price") is not None:
                etree.SubElement(item_node, "PrecioUnitarioReferencia").text = (
                    item.get("reference_unit_price_text") or format_money(item["reference_unit_price"])
                )
            self._text(item_node, "FechaElaboracion", item.get("manufacturing_date"))
            self._text(item_node, "FechaVencimientoItem", item.get("item_expiration_date"))
            etree.SubElement(item_node, "PrecioUnitarioItem").text = item.get("unit_price_text") or format_unit_price(item["unit_price"])
            if not item.get("suppress_item_adjustments"):
                if item.get("discount") and item["discount"] > 0:
                    etree.SubElement(item_node, "DescuentoMonto").text = item.get("discount_text") or format_money(item["discount"])
                self._append_item_sub_discounts(item_node, item)
                if item.get("surcharge") and item["surcharge"] > 0:
                    etree.SubElement(item_node, "RecargoMonto").text = item.get("surcharge_text") or format_money(item["surcharge"])
                self._append_item_sub_surcharges(item_node, item)
            etree.SubElement(item_node, "MontoItem").text = item.get("amount_text") or format_money(item["amount"])

    def _append_item_sub_discounts(self, item_node: etree._Element, item: dict[str, Any]) -> None:
        sub_discounts = item.get("sub_discounts") or []
        if not sub_discounts:
            return
        table = etree.SubElement(item_node, "TablaSubDescuento")
        for sub_discount in sub_discounts:
            node = etree.SubElement(table, "SubDescuento")
            etree.SubElement(node, "TipoSubDescuento").text = sub_discount["type"]
            if sub_discount.get("percentage") is not None:
                etree.SubElement(node, "SubDescuentoPorcentaje").text = format_money(sub_discount["percentage"])
            if sub_discount.get("amount") is not None:
                etree.SubElement(node, "MontoSubDescuento").text = format_money(sub_discount["amount"])

    def _append_item_sub_surcharges(self, item_node: etree._Element, item: dict[str, Any]) -> None:
        sub_surcharges = item.get("sub_surcharges") or []
        if not sub_surcharges:
            return
        table = etree.SubElement(item_node, "TablaSubRecargo")
        for sub_surcharge in sub_surcharges:
            node = etree.SubElement(table, "SubRecargo")
            etree.SubElement(node, "TipoSubRecargo").text = sub_surcharge["type"]
            if sub_surcharge.get("percentage") is not None:
                etree.SubElement(node, "SubRecargoPorcentaje").text = format_money(sub_surcharge["percentage"])
            if sub_surcharge.get("amount") is not None:
                etree.SubElement(node, "MontoSubRecargo").text = format_money(sub_surcharge["amount"])

    def _append_item_retention(self, item_node: etree._Element, item: dict[str, Any]) -> None:
        retention = item.get("retention") or {}
        if not retention:
            return
        node = etree.SubElement(item_node, "Retencion")
        self._text(node, "IndicadorAgenteRetencionoPercepcion", retention.get("indicator"))
        if retention.get("itbis") is not None:
            etree.SubElement(node, "MontoITBISRetenido").text = format_money(retention["itbis"])
        if retention.get("isr") is not None:
            etree.SubElement(node, "MontoISRRetenido").text = format_money(retention["isr"])

    def _append_discounts_or_surcharges(self, root: etree._Element, payload: ECFPayload) -> None:
        adjustments = payload.discounts_or_surcharges or []
        if not adjustments:
            return
        container = etree.SubElement(root, "DescuentosORecargos")
        for adjustment in adjustments:
            node = etree.SubElement(container, "DescuentoORecargo")
            etree.SubElement(node, "NumeroLinea").text = str(adjustment["line_number"])
            etree.SubElement(node, "TipoAjuste").text = adjustment["adjustment_type"]
            self._text(node, "DescripcionDescuentooRecargo", adjustment.get("description"))
            self._text(node, "TipoValor", adjustment.get("value_type"))
            if adjustment.get("value") is not None:
                etree.SubElement(node, "ValorDescuentooRecargo").text = format_money(adjustment["value"])
            if adjustment.get("amount") is not None:
                etree.SubElement(node, "MontoDescuentooRecargo").text = format_money(adjustment["amount"])
            self._text(
                node,
                "IndicadorFacturacionDescuentooRecargo",
                adjustment.get("billing_indicator"),
            )

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
