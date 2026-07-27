"""Compare DGII certification group raw_data against generated XML."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationItem
from facturacion.services.dgii_certification import DGIICertificationDocumentGenerator


class Command(BaseCommand):
    help = "Compara los e-CF de un grupo DGII contra raw_data del Excel."

    checked_fields = [
        ("FechaVencimientoSecuencia", "FechaVencimientoSecuencia"),
        ("FechaEmision", "FechaEmision"),
        ("TipoIngresos", "TipoIngresos"),
        ("RNCComprador", "RNCComprador"),
        ("IdentificadorExtranjero", "IdentificadorExtranjero"),
        ("RazonSocialComprador", "RazonSocialComprador"),
        ("ContactoComprador", "ContactoComprador"),
        ("CorreoComprador", "CorreoComprador"),
        ("DireccionComprador", "DireccionComprador"),
        ("MunicipioComprador", "MunicipioComprador"),
        ("ProvinciaComprador", "ProvinciaComprador"),
        ("FechaEntrega", "FechaEntrega"),
        ("FechaOrdenCompra", "FechaOrdenCompra"),
        ("NumeroOrdenCompra", "NumeroOrdenCompra"),
        ("CodigoInternoComprador", "CodigoInternoComprador"),
        ("Municipio", "Municipio"),
        ("Provincia", "Provincia"),
        ("WebSite", "WebSite"),
        ("NumeroFacturaInterna", "NumeroFacturaInterna"),
        ("NumeroPedidoInterno", "NumeroPedidoInterno"),
        ("ZonaVenta", "ZonaVenta"),
        ("TipoPago", "TipoPago"),
        ("MontoPeriodo", "MontoPeriodo"),
        ("ValorPagar", "ValorPagar"),
        ("TotalITBISRetenido", "TotalITBISRetenido"),
        ("TotalISRRetencion", "TotalISRRetencion"),
        ("TotalITBIS", "TotalITBIS"),
        ("TotalITBIS3", "TotalITBIS3"),
    ]

    def add_arguments(self, parser):
        parser.add_argument("--group", type=int, required=True, dest="group_number")
        parser.add_argument("--plan-id", type=int, default=None)

    def handle(self, *args, **options):
        group_number = options["group_number"]
        queryset = DGIICertificationItem.objects.filter(dgii_group=group_number).order_by("-plan_id", "source_row", "id")
        if options["plan_id"]:
            queryset = queryset.filter(plan_id=options["plan_id"])
        elif queryset.exists():
            queryset = queryset.filter(plan_id=queryset.first().plan_id)
        if not queryset.exists():
            raise CommandError("No hay items para ese grupo DGII.")

        generator = DGIICertificationDocumentGenerator()
        current_plan = queryset.first().plan_id
        self.stdout.write(f"Plan {current_plan} - Grupo {group_number}")

        ok_count = 0
        diff_count = 0
        for item in queryset:
            status, details = self._compare_item(generator, item)
            if status == "OK":
                ok_count += 1
            else:
                diff_count += 1
            self.stdout.write(f"{status:10} {item.encf} tipo={item.ecf_type} fila={item.source_row}")
            for detail in details:
                self.stdout.write(f"  - {detail}")

        self.stdout.write(f"Resumen: OK={ok_count} DIFERENCIA={diff_count}")

    def _compare_item(self, generator: DGIICertificationDocumentGenerator, item: DGIICertificationItem):
        try:
            issuer = generator._resolve_issuer(item.company)
            payload = generator._build_payload(item=item, issuer=issuer)
            root = generator.builder_factory.get(item.ecf_type).build(payload)
            xml = etree.tostring(root, encoding="unicode")
        except Exception as exc:  # noqa: BLE001 - diagnostic command must report controlled differences.
            return "DIFERENCIA", [f"Error generando XML: {exc}"]

        xml_fields = self._flatten_xml(xml)
        xml_items = self._item_xml_fields(xml)
        details = []
        for raw_key, xml_key in self.checked_fields:
            if raw_key == "RNCComprador":
                expected = self._clean(payload.buyer.get("rnc")) if payload.include_buyer else ""
            elif raw_key == "IdentificadorExtranjero":
                expected = self._clean(payload.buyer.get("foreign_identifier")) if payload.include_buyer else ""
            elif raw_key == "RazonSocialComprador":
                expected = self._clean(payload.buyer.get("business_name")) if payload.include_buyer else ""
            elif raw_key == "TipoPago":
                expected = self._clean(payload.payment_type)
            else:
                expected = self._clean(generator._raw_value(item, raw_key))
            actual = ", ".join(xml_fields.get(xml_key, []))
            if expected != actual:
                details.append(f"{raw_key}: raw={expected!r} xml={actual!r}")

        expected_payments = generator._build_payment_forms(item, payload.totals)
        has_payment_table = "<TablaFormasPago>" in xml
        if bool(expected_payments) != has_payment_table:
            details.append(f"TablaFormasPago: esperado={bool(expected_payments)} xml={has_payment_table}")
        expected_amounts = [str(payment["amount"]) for payment in expected_payments]
        actual_amounts = xml_fields.get("MontoPago", [])
        if expected_amounts != actual_amounts:
            details.append(f"MontoPago: raw={expected_amounts!r} xml={actual_amounts!r}")

        document = getattr(item, "certification_document", None)
        if document and document.signed_xml_path:
            expected_filename = f"{item.encf}.xml"
            actual_filename = Path(document.signed_xml_path).name
            if expected_filename != actual_filename:
                details.append(f"NombreArchivo: esperado={expected_filename!r} firmado={actual_filename!r}")

        foreign_identifier = self._clean(generator._raw_value(item, "IdentificadorExtranjero"))
        rnc_comprador = self._clean(generator._raw_value(item, "RNCComprador"))
        if foreign_identifier:
            actual_foreign = ", ".join(xml_fields.get("IdentificadorExtranjero", []))
            if foreign_identifier != actual_foreign:
                details.append(f"IdentificadorExtranjero: raw={foreign_identifier!r} xml={actual_foreign!r}")
            if not rnc_comprador and xml_fields.get("RNCComprador"):
                details.append("RNCComprador: aparece aunque el set DGII trae IdentificadorExtranjero")

        for item_payload in payload.items:
            line = item_payload["line_number"]
            for raw_name, xml_name in (
                ("CantidadItem", "CantidadItem"),
                ("PrecioUnitarioItem", "PrecioUnitarioItem"),
                ("MontoItem", "MontoItem"),
                ("DescuentoMonto", "DescuentoMonto"),
                ("RecargoMonto", "RecargoMonto"),
                ("UnidadMedida", "UnidadMedida"),
            ):
                expected_text = self._clean(generator._raw_item_text(item, f"{raw_name}[{line}]"))
                actual_text = xml_items.get(line, {}).get(xml_name, "")
                if expected_text != actual_text:
                    details.append(f"{raw_name}[{line}]: raw={expected_text!r} xml={actual_text!r}")

            retention = item_payload.get("retention") or {}
            expected_isr = self._clean(retention.get("isr"))
            if expected_isr:
                actual_isr = xml_items.get(line, {}).get("MontoISRRetenido", "")
                if expected_isr != actual_isr:
                    details.append(f"MontoISRRetenido[{line}]: raw={expected_isr!r} xml={actual_isr!r}")

        if xml_fields.get("MunicipioEmisor"):
            details.append("MunicipioEmisor: tag no permitido por XSD real DGII")
        if xml_fields.get("ProvinciaEmisor"):
            details.append("ProvinciaEmisor: tag no permitido por XSD real DGII")
        if xml_fields.get("TablaSubDescuento"):
            details.append("TablaSubDescuento: nodo rechazado por DGII para este set")
        if xml_fields.get("TablaSubRecargo"):
            details.append("TablaSubRecargo: nodo rechazado por DGII para este set")

        prohibited_when_empty = [
            ("CodigoVendedor", "CodigoVendedor"),
            ("TipoIngresos", "TipoIngresos"),
            ("TipoPago", "TipoPago"),
            ("FormaPago[1]", "TablaFormasPago"),
        ]
        for raw_key, xml_key in prohibited_when_empty:
            if not self._clean(generator._raw_value(item, raw_key)) and xml_fields.get(xml_key):
                details.append(f"{xml_key}: aparece aunque {raw_key} viene vacio/#e")

        return ("OK" if not details else "DIFERENCIA"), details

    def _flatten_xml(self, xml: str) -> dict[str, list[str]]:
        root = etree.fromstring(xml.encode("utf-8"))
        fields: dict[str, list[str]] = {}
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            text = (element.text or "").strip()
            tag = element.tag.split("}", 1)[-1]
            fields.setdefault(tag, [])
            if text:
                fields[tag].append(text)
        return fields

    def _item_xml_fields(self, xml: str) -> dict[int, dict[str, str]]:
        root = etree.fromstring(xml.encode("utf-8"))
        items: dict[int, dict[str, str]] = {}
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            if element.tag.split("}", 1)[-1] != "Item":
                continue
            fields: dict[str, str] = {}
            for child in element.iterdescendants():
                if not isinstance(child.tag, str):
                    continue
                tag = child.tag.split("}", 1)[-1]
                text = (child.text or "").strip()
                if text:
                    fields[tag] = text
            line_text = fields.get("NumeroLinea")
            try:
                line = int(line_text) if line_text else len(items) + 1
            except ValueError:
                line = len(items) + 1
            items[line] = fields
        return items

    def _clean(self, value):
        if value in (None, "", "#e"):
            return ""
        return str(value)
