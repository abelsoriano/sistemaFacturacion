"""Inspect one generated RFCE XML against imported DGII Excel data."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.rfce_contract import rfce_example_files, rfce_schema_dir, rfce_xsd_files
from facturacion.models import DGIICertificationDocument


class Command(BaseCommand):
    help = "Inspecciona estructura XML RFCE y raw_data importado sin enviar a DGII."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True)
        parser.add_argument("--encf", required=True)
        parser.add_argument(
            "--source",
            choices=["signed", "generated"],
            default="signed",
            help="XML a inspeccionar. Por defecto usa el XML firmado.",
        )
        parser.add_argument(
            "--include-signature-values",
            action="store_true",
            help="Incluye valores largos de SignatureValue/X509Certificate en la salida.",
        )

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        encf = options["encf"]
        source = options["source"]
        include_signature_values = options["include_signature_values"]

        try:
            document = (
                DGIICertificationDocument.objects
                .select_related("plan", "item", "company")
                .get(plan_id=plan_id, encf=encf, ecf_type="RFCE")
            )
        except DGIICertificationDocument.DoesNotExist as exc:
            raise CommandError(f"No existe RFCE {encf} en plan={plan_id}.") from exc

        xml_text = self._xml_text(document, source)
        try:
            root = ET.fromstring(xml_text.encode("utf-8"))
        except ET.ParseError as exc:
            raise CommandError(f"XML RFCE no parsea: {exc}") from exc

        raw_data = document.item.raw_data or {}
        fields = self._leaf_fields(root, include_signature_values=include_signature_values)
        raw_real = {
            key: value
            for key, value in sorted(raw_data.items())
            if self._clean(value)
        }
        xsd_files = rfce_xsd_files()
        example_files = rfce_example_files()
        differences = self._differences(fields, raw_real)

        self.stdout.write(f"RFCE XML inspection | plan={plan_id} | encf={encf} | source={source}")
        self.stdout.write(f"Empresa: {document.company_id} | item={document.item_id} | doc={document.id}")
        self.stdout.write(f"XML path: {document.signed_xml_path if source == 'signed' else 'document.xml_content'}")
        self.stdout.write(f"Raiz: {self._tag(root)}")
        self.stdout.write(f"Carpeta contrato RFCE: {rfce_schema_dir()}")
        self.stdout.write(f"XSD RFCE local: {', '.join(str(path) for path in xsd_files) or 'NO DISPONIBLE'}")
        self.stdout.write(f"Ejemplo XML oficial RFCE: {', '.join(str(path) for path in example_files) or 'NO DISPONIBLE'}")
        if xsd_files:
            self.stdout.write("Validacion XSD: pendiente de integrar con el XSD RFCE local cargado.")
        else:
            self.stdout.write("Validacion XSD: no ejecutada; no hay XSD RFCE local oficial.")

        self.stdout.write("")
        self.stdout.write("Orden de nodos:")
        for path in self._node_paths(root):
            self.stdout.write(f"- {path}")

        self.stdout.write("")
        self.stdout.write("Campos XML RFCE:")
        for path, value in fields:
            self.stdout.write(f"- {path}: {value or '-'}")

        self.stdout.write("")
        self.stdout.write("Valores Excel/raw_data con dato real:")
        for key, value in raw_real.items():
            self.stdout.write(f"- {key}: {value}")

        self.stdout.write("")
        self.stdout.write("Diferencias XML vs raw_data por nombre de tag:")
        if differences:
            for line in differences:
                self.stdout.write(f"- {line}")
        else:
            self.stdout.write("- No hay diferencias simples por tags coincidentes.")

        self.stdout.write("")
        self.stdout.write("Observaciones estructurales:")
        for observation in self._structural_observations(root, has_xsd=bool(xsd_files)):
            self.stdout.write(f"- {observation}")

    def _xml_text(self, document, source):
        if source == "generated":
            if not document.xml_content:
                raise CommandError(f"{document.encf} no tiene XML generado en base de datos.")
            return document.xml_content
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            raise CommandError(f"{document.encf} no tiene XML firmado disponible.")
        with default_storage.open(document.signed_xml_path, "rb") as signed_file:
            return signed_file.read().decode("utf-8", errors="replace")

    def _node_paths(self, root):
        paths = []

        def walk(node, prefix):
            path = f"{prefix}/{self._tag(node)}" if prefix else self._tag(node)
            paths.append(path)
            for child in list(node):
                walk(child, path)

        walk(root, "")
        return paths

    def _leaf_fields(self, root, *, include_signature_values):
        fields = []
        hidden_signature_tags = {"SignatureValue", "X509Certificate", "DigestValue"}

        def walk(node, prefix):
            path = f"{prefix}/{self._tag(node)}" if prefix else self._tag(node)
            children = list(node)
            if not children:
                tag = self._tag(node)
                value = (node.text or "").strip()
                if tag in hidden_signature_tags and not include_signature_values:
                    value = "[omitido; use --include-signature-values]"
                fields.append((path, value))
                return
            for child in children:
                walk(child, path)

        walk(root, "")
        return fields

    def _differences(self, fields, raw_data):
        by_tag = {}
        for path, value in fields:
            by_tag.setdefault(path.rsplit("/", 1)[-1], []).append(value)

        differences = []
        for tag, values in sorted(by_tag.items()):
            raw_value = self._clean(raw_data.get(tag))
            if raw_value and raw_value not in values:
                differences.append(f"{tag}: XML={values} | Excel={raw_value}")
            if not raw_value and any(self._clean(value) for value in values):
                differences.append(f"{tag}: XML trae {values}; raw_data no tiene campo equivalente directo.")

        for key, value in sorted(raw_data.items()):
            clean_value = self._clean(value)
            if clean_value and key not in by_tag and not key.startswith("col_"):
                differences.append(f"{key}: Excel={clean_value}; no aparece como tag XML.")
        return differences

    def _structural_observations(self, root, *, has_xsd):
        tags = [self._tag(node) for node in root.iter()]
        observations = []
        if self._tag(root) != "RFCE":
            observations.append(f"Raiz distinta a la esperada por XSD RFCE: {self._tag(root)}.")
        if "Signature" not in tags:
            observations.append("No incluye Signature en el XML inspeccionado.")
        for tag in ("Version", "IdDoc", "Emisor", "Comprador", "Totales", "CodigoSeguridadeCF"):
            if tag not in tags:
                observations.append(f"No contiene nodo requerido por XSD RFCE: {tag}.")
        if has_xsd:
            observations.append("El XSD RFCE oficial local no exige Detalle ni rangos eNCF en la raiz RFCE.")
        if not observations:
            observations.append("No se detectaron alertas estructurales basicas.")
        return observations

    def _tag(self, node):
        return node.tag.split("}", 1)[-1]

    def _clean(self, value):
        text = str(value or "").strip()
        return "" if text in {"#e", "ªç"} else text
