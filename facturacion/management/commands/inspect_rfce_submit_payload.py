"""Inspect one RFCE certification submit payload without sending it."""

from __future__ import annotations

import json

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationDocument
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = "Inspecciona un payload RFCE de certificacion sin enviarlo a DGII."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True)
        parser.add_argument("--encf", required=True)
        parser.add_argument("--xml-lines", type=int, default=20)

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        encf = options["encf"]
        xml_lines = max(1, options["xml_lines"])

        try:
            document = (
                DGIICertificationDocument.objects
                .select_related("plan", "item", "company")
                .get(plan_id=plan_id, encf=encf, ecf_type="RFCE")
            )
        except DGIICertificationDocument.DoesNotExist as exc:
            raise CommandError(f"No existe RFCE {encf} en plan={plan_id}.") from exc

        submitter = DGIICertificationDGIISubmitter()
        diagnostics = submitter._inspect_document_submit_payload(document)
        rfce_payload = diagnostics.get("rfce_payload") or {}
        signed_xml = self._read_signed_xml(document)

        self.stdout.write(f"RFCE submit payload | plan={plan_id} | encf={encf}")
        self.stdout.write(f"URL: {rfce_payload.get('url') or '-'}")
        self.stdout.write(f"Metodo: {rfce_payload.get('method') or 'POST'}")
        self.stdout.write(f"Campo multipart: {rfce_payload.get('multipart_field') or '-'}")
        self.stdout.write(f"Filename multipart: {rfce_payload.get('multipart_filename') or diagnostics.get('multipart_filename') or '-'}")
        self.stdout.write(f"Content-Type: {rfce_payload.get('content_type') or '-'}")
        self.stdout.write(f"Tamano XML: {rfce_payload.get('xml_size_bytes') or diagnostics.get('size_bytes') or 0} bytes")
        self.stdout.write(f"Primer nodo XML: {rfce_payload.get('first_xml_node') or '-'}")
        includes_signature = rfce_payload.get("includes_signature")
        self.stdout.write(f"Incluye Signature: {'SI' if includes_signature else 'NO'}")
        self.stdout.write(f"Tipo declarado: {rfce_payload.get('declared_type') or '-'}")
        self.stdout.write(f"Signed XML path: {document.signed_xml_path or '-'}")
        self.stdout.write(f"SHA256: {diagnostics.get('sha256') or document.signed_xml_hash or '-'}")

        errors = diagnostics.get("errors") or []
        if errors:
            self.stdout.write("")
            self.stdout.write("Errores de inspeccion:")
            for error in errors:
                self.stdout.write(f"- {error}")

        self.stdout.write("")
        self.stdout.write(f"Primeras {xml_lines} lineas XML:")
        if signed_xml:
            for line in signed_xml.splitlines()[:xml_lines]:
                self.stdout.write(line)
        else:
            self.stdout.write("- XML firmado no disponible.")

        self.stdout.write("")
        self.stdout.write("Response DGII guardada:")
        self.stdout.write(self._stored_response_text(document))

    def _read_signed_xml(self, document):
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            return ""
        with default_storage.open(document.signed_xml_path, "rb") as signed_file:
            return signed_file.read().decode("utf-8", errors="replace")

    def _stored_response_text(self, document):
        response = document.dgii_response or {}
        candidates = []
        if isinstance(response, dict):
            candidates.extend([
                response.get("response_text"),
                response.get("body"),
                response.get("message"),
                response.get("error"),
            ])
            dgii_error = response.get("dgii_error")
            if isinstance(dgii_error, dict):
                candidates.extend([
                    dgii_error.get("response_text"),
                    dgii_error.get("body"),
                    dgii_error.get("message"),
                    dgii_error.get("error"),
                ])
        elif response:
            candidates.append(str(response))

        candidates.extend([
            document.dgii_response_message,
            document.submit_error,
        ])
        for value in candidates:
            if value:
                return str(value)
        if response:
            return json.dumps(response, ensure_ascii=False, indent=2)
        return "- No hay respuesta DGII guardada para este documento."
