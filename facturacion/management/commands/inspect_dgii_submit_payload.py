"""Inspect DGII certification submit payloads without sending them."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = "Inspecciona los XML firmados que se enviarian a DGII sin hacer submit."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True)
        parser.add_argument("--group", type=int, required=True, dest="group_number")

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        group_number = options["group_number"]
        try:
            plan = DGIICertificationPlan.objects.get(id=plan_id)
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CommandError(f"No existe plan DGII {plan_id}.") from exc

        submitter = DGIICertificationDGIISubmitter()
        diagnostics = submitter.inspect_submit_payload(plan=plan, group_number=group_number)
        if not diagnostics:
            raise CommandError("No hay documentos para inspeccionar.")

        ok_count = 0
        error_count = 0
        self.stdout.write(f"Plan {plan.id} - Grupo {group_number}")
        for item in diagnostics:
            errors = item.get("errors") or []
            if errors:
                error_count += 1
                status = "ERROR"
            else:
                ok_count += 1
                status = "OK"
            self.stdout.write(f"{status:5} {item['encf']} tipo={item['ecf_type']}")
            self.stdout.write(f"  signed_xml_path: {item['signed_xml_path']}")
            self.stdout.write(f"  RNCEmisor usado: {item['issuer_rnc'] or 'No disponible'}")
            self.stdout.write(f"  filename esperado: {item['expected_filename']}")
            self.stdout.write(f"  filename multipart: {item['multipart_filename']}")
            self.stdout.write(f"  longitud filename: {item['filename_length']}")
            self.stdout.write(f"  tamano bytes: {item['size_bytes']}")
            self.stdout.write(f"  sha256: {item['sha256']}")
            self.stdout.write(f"  CodigoVendedor XML: {item['CodigoVendedor'] or 'No disponible'}")
            self.stdout.write(f"  NumeroFacturaInterna XML: {item['NumeroFacturaInterna'] or 'No disponible'}")
            comprador = item["RNCComprador"] or item["IdentificadorExtranjero"] or "No disponible"
            self.stdout.write(f"  comprador XML: {comprador}")
            self.stdout.write(f"  NCFModificado XML: {item.get('NCFModificado') or 'No disponible'}")
            self.stdout.write(f"  documento origen local: {item.get('origin_document_id') or 'No encontrado'}")
            self.stdout.write(f"  estado origen local: {item.get('origin_document_status') or 'No disponible'}")
            self.stdout.write(f"  estado DGII origen local: {item.get('origin_document_dgii_status') or 'No disponible'}")
            self.stdout.write(f"  contiene CodigoVendedor AA000...0006: {item['contains_long_seller_code']}")
            self.stdout.write(f"  contiene 123456789016: {item['contains_expected_internal_invoice']}")
            for error in errors:
                self.stdout.write(f"  - {error}")

        self.stdout.write(f"Resumen: OK={ok_count} ERROR={error_count}")
        if error_count:
            raise CommandError("Preflight DGII submit fallo. No envie este grupo.")
