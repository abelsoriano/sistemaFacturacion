"""Probe the DGII RFCE HTTP contract for one certification document."""

from __future__ import annotations

import json

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.rest.clients import DGIIRESTClient, DGIIRESTHTTPError
from facturacion.ecf.rfce_contract import RFCE_CONTRACT_MISSING_MESSAGE, has_rfce_contract
from facturacion.ecf.utils.text import digits_only
from facturacion.models import DGIICertificationDocument
from facturacion.services.dgii_certification import DGIICertificationDocumentGenerator
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = "Envia un RFCE individual variando contrato HTTP sin modificar el XML fiscal."

    def add_arguments(self, parser):
        parser.add_argument("--plan-id", type=int, required=True)
        parser.add_argument("--encf", required=True)
        parser.add_argument("--field", default=None)
        parser.add_argument("--content-type", default=None, dest="content_type")
        parser.add_argument("--signed", default=None, choices=["true", "false", "True", "False", "1", "0"])

    def handle(self, *args, **options):
        plan_id = options["plan_id"]
        encf = options["encf"]
        multipart_field = options["field"]
        content_type = options["content_type"]
        signed = self._bool_option(options["signed"])
        if not has_rfce_contract():
            raise CommandError(RFCE_CONTRACT_MISSING_MESSAGE)

        try:
            document = (
                DGIICertificationDocument.objects
                .select_related("plan", "item", "company")
                .get(plan_id=plan_id, encf=encf, ecf_type="RFCE")
            )
        except DGIICertificationDocument.DoesNotExist as exc:
            raise CommandError(f"No existe RFCE {encf} en plan={plan_id}.") from exc

        xml_content = self._xml_for(document, signed=signed)
        issuer = DGIICertificationDocumentGenerator()._resolve_issuer(document.company)
        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        if not certificate_path:
            raise CommandError("El emisor fiscal no tiene certificado DGII disponible.")

        issuer_rnc = digits_only(issuer.rnc) or issuer.rnc
        submitter = DGIICertificationDGIISubmitter()
        filename = submitter._multipart_filename_for(document, issuer_rnc=issuer_rnc)
        client = DGIIRESTClient()
        field = multipart_field or getattr(settings, "ECF_DGII_RFCE_MULTIPART_FIELD", "xml")
        ctype = content_type or getattr(settings, "ECF_DGII_RFCE_CONTENT_TYPE", "text/xml")
        url = client._url(client.environment.rfce_base_url, client.rfce_path)

        payload = {
            "contract_test": True,
            "tested_at": timezone.now().isoformat(),
            "url": url,
            "method": "POST",
            "multipart_field": field,
            "multipart_filename": filename,
            "content_type": ctype,
            "signed": signed,
            "encf": document.encf,
            "ecf_type": document.ecf_type,
            "xml_size_bytes": len(xml_content.encode("utf-8")),
        }

        try:
            result = client.submit_rfce(
                signed_xml_content=xml_content,
                encf=document.encf,
                issuer_rnc=issuer_rnc,
                certificate_path=certificate_path,
                certificate_password=certificate_password,
                filename=filename,
                multipart_field=field,
                content_type=ctype,
            )
            payload.update({
                "status_code": result.status_code,
                "response_text": result.response_xml or json.dumps(result.result, ensure_ascii=False),
                "response_payload": result.result,
            })
            document.dgii_response_code = str(result.status_code)
            document.dgii_response_message = payload["response_text"]
            document.submit_error = ""
        except DGIIRESTHTTPError as exc:
            safe_payload = exc.as_safe_payload()
            payload.update(safe_payload)
            document.dgii_response_code = str(exc.status_code)
            document.dgii_response_message = safe_payload.get("response_text", "")
            document.submit_error = str(exc)
        except Exception as exc:  # noqa: BLE001 - command must persist diagnostic failures too.
            payload.update({
                "error": str(exc),
            })
            document.dgii_response_code = ""
            document.dgii_response_message = str(exc)
            document.submit_error = str(exc)

        document.dgii_response = self._append_contract_attempt(document.dgii_response, payload)
        document.submitted_at = timezone.now()
        document.save(update_fields=[
            "dgii_response",
            "dgii_response_code",
            "dgii_response_message",
            "submit_error",
            "submitted_at",
            "updated_at",
        ])

        self.stdout.write(f"URL: {payload.get('url')}")
        self.stdout.write(f"field: {payload.get('multipart_field')}")
        self.stdout.write(f"content-type: {payload.get('content_type')}")
        self.stdout.write(f"signed: {payload.get('signed')}")
        self.stdout.write(f"filename: {payload.get('multipart_filename')}")
        self.stdout.write(f"status_code: {payload.get('status_code') or '-'}")
        self.stdout.write(f"response_text: {payload.get('response_text') or payload.get('error') or '-'}")

    def _append_contract_attempt(self, current_response, payload):
        if isinstance(current_response, dict):
            attempts = list(current_response.get("rfce_contract_tests") or [])
        else:
            attempts = []
        attempts.append(payload)
        return {
            **payload,
            "rfce_contract_tests": attempts[-10:],
        }

    def _bool_option(self, value):
        if value is None:
            return bool(getattr(settings, "ECF_DGII_RFCE_SEND_SIGNED_XML", True))
        return str(value).lower() in {"true", "1"}

    def _xml_for(self, document, *, signed):
        if signed:
            if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
                raise CommandError(f"{document.encf} no tiene XML firmado disponible.")
            with default_storage.open(document.signed_xml_path, "rb") as signed_file:
                return signed_file.read().decode("utf-8", errors="replace")
        if not document.xml_content:
            raise CommandError(f"{document.encf} no tiene XML sin firmar disponible.")
        return document.xml_content
