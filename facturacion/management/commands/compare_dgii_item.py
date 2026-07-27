"""Compare a DGII certification item raw_data against the generated XML."""

from __future__ import annotations

from lxml import etree

from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationItem
from facturacion.services.dgii_certification import DGIICertificationDocumentGenerator


class Command(BaseCommand):
    help = "Compara raw_data, payload y XML generado para un e-NCF del plan DGII."

    field_pairs = [
        ("TipoeCF", "TipoeCF"),
        ("ENCF", "eNCF"),
        ("FechaVencimientoSecuencia", "FechaVencimientoSecuencia"),
        ("IndicadorMontoGravado", "IndicadorMontoGravado"),
        ("TipoIngresos", "TipoIngresos"),
        ("TipoPago", "TipoPago"),
        ("FormaPago[1]", "FormaPago"),
        ("MontoPago[1]", "MontoPago"),
        ("RNCEmisor", "RNCEmisor"),
        ("RazonSocialEmisor", "RazonSocialEmisor"),
        ("NombreComercial", "NombreComercial"),
        ("DireccionEmisor", "DireccionEmisor"),
        ("Municipio", "Municipio"),
        ("Provincia", "Provincia"),
        ("TelefonoEmisor[1]", "TelefonoEmisor"),
        ("CorreoEmisor", "CorreoEmisor"),
        ("WebSite", "WebSite"),
        ("ActividadEconomica", "ActividadEconomica"),
        ("CodigoVendedor", "CodigoVendedor"),
        ("NumeroFacturaInterna", "NumeroFacturaInterna"),
        ("NumeroPedidoInterno", "NumeroPedidoInterno"),
        ("ZonaVenta", "ZonaVenta"),
        ("RutaVenta", "RutaVenta"),
        ("InformacionAdicionalEmisor", "InformacionAdicionalEmisor"),
        ("FechaEmision", "FechaEmision"),
        ("RNCComprador", "RNCComprador"),
        ("RazonSocialComprador", "RazonSocialComprador"),
        ("CorreoComprador", "CorreoComprador"),
        ("DireccionComprador", "DireccionComprador"),
        ("MontoGravadoTotal", "MontoGravadoTotal"),
        ("MontoGravadoI1", "MontoGravadoI1"),
        ("MontoGravadoI2", "MontoGravadoI2"),
        ("MontoGravadoI3", "MontoGravadoI3"),
        ("MontoExento", "MontoExento"),
        ("ITBIS1", "ITBIS1"),
        ("ITBIS2", "ITBIS2"),
        ("ITBIS3", "ITBIS3"),
        ("TotalITBIS", "TotalITBIS"),
        ("TotalITBIS1", "TotalITBIS1"),
        ("TotalITBIS2", "TotalITBIS2"),
        ("TotalITBIS3", "TotalITBIS3"),
        ("MontoImpuestoAdicional", "MontoImpuestoAdicional"),
        ("MontoTotal", "MontoTotal"),
    ]

    def add_arguments(self, parser):
        parser.add_argument("--encf", required=True, help="e-NCF a comparar, por ejemplo E320000000004.")
        parser.add_argument("--plan-id", type=int, default=None, help="Plan DGII especifico si hay duplicados.")

    def handle(self, *args, **options):
        queryset = DGIICertificationItem.objects.filter(encf=options["encf"]).order_by("-plan_id", "-id")
        if options["plan_id"]:
            queryset = queryset.filter(plan_id=options["plan_id"])
        item = queryset.first()
        if not item:
            raise CommandError("No existe item DGII con ese e-NCF.")

        generator = DGIICertificationDocumentGenerator()
        issuer = generator._resolve_issuer(item.company)
        payload = generator._build_payload(item=item, issuer=issuer)
        builder = generator.builder_factory.get(item.ecf_type)
        xml = etree.tostring(builder.build(payload), encoding="unicode")
        xml_fields = self._flatten_xml(xml)
        raw_data = item.raw_data or {}

        self.stdout.write(f"Item: {item.id} plan={item.plan_id} empresa={item.company_id}")
        self.stdout.write(f"Origen: hoja={item.source_sheet} fila={item.source_row} tipo={item.ecf_type}")
        self.stdout.write("")
        self.stdout.write("Comparacion raw_data -> XML:")
        for raw_key, xml_key in self.field_pairs:
            raw_value = self._clean(generator._raw_value(item, raw_key))
            xml_values = xml_fields.get(xml_key, [])
            xml_value = ", ".join(xml_values) if xml_values else ""
            marker = "OK" if raw_value == xml_value or (not raw_value and not xml_value) else "DIFF"
            self.stdout.write(f"{marker:4} {raw_key}={raw_value!r} -> {xml_key}={xml_value!r}")

        self.stdout.write("")
        self.stdout.write("Items:")
        for index, item_payload in enumerate(payload.items, start=1):
            self.stdout.write(
                f"{index}. {item_payload['name']} "
                f"indicador={item_payload['billing_indicator']} "
                f"cantidad={item_payload['quantity']} "
                f"precio={item_payload['unit_price']} "
                f"monto={item_payload['amount']}"
            )

        if payload.discounts_or_surcharges:
            self.stdout.write("")
            self.stdout.write("Descuentos/recargos:")
            for adjustment in payload.discounts_or_surcharges:
                self.stdout.write(str(adjustment))

    def _flatten_xml(self, xml: str) -> dict[str, list[str]]:
        root = etree.fromstring(xml.encode("utf-8"))
        fields: dict[str, list[str]] = {}
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            text = (element.text or "").strip()
            if not text:
                continue
            tag = element.tag.split("}", 1)[-1]
            fields.setdefault(tag, []).append(text)
        return fields

    def _clean(self, value):
        if value in (None, "", "#e"):
            return ""
        return str(value)
