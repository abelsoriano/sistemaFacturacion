from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.rest.clients import DGIIRESTClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.manual_tools import resolve_manual_certificate_context, summarize_payload, write_rest_artifact
from facturacion.ecf.utils.text import digits_only
from facturacion.models import Company, ElectronicFiscalDocument


class Command(BaseCommand):
    help = "Send a signed XML to DGII REST in manual mode without changing local fiscal/job status."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, default=None, help="ElectronicFiscalDocument with signed XML.")
        parser.add_argument("--file", default=None, help="Signed XML file path. Requires --encf and issuer context.")
        parser.add_argument("--encf", default=None, help="e-NCF. Required with --file.")
        parser.add_argument("--environment", default=None, help="DGII environment key. Defaults to ECF_DGII_ENVIRONMENT.")
        parser.add_argument("--company-id", type=int, default=None, help="Company context used to validate document/issuer.")
        parser.add_argument("--issuer-id", type=int, default=None, help="Issuer config used to resolve certificate/RNC.")
        parser.add_argument("--issuer-rnc", default=None, help="Issuer RNC. Required with --file unless --issuer-id is used.")
        parser.add_argument("--certificate-path", default=None, help="PKCS#12 certificate path.")
        parser.add_argument("--certificate-password", default=None, help="PKCS#12 password. Prefer ECF_CERTIFICATE_PASSWORD.")
        parser.add_argument("--save-artifact", action="store_true", default=True, help="Persist raw DGII response. Enabled by default.")
        parser.add_argument("--no-save-artifact", action="store_false", dest="save_artifact", help="Do not persist response artifact.")

    def handle(self, *args, **options):
        document = None
        company = Company.objects.get(pk=options["company_id"]) if options.get("company_id") else None
        if options.get("document_id") and options.get("file"):
            raise CommandError("Usa --document-id o --file, no ambos.")
        if not options.get("document_id") and not options.get("file"):
            raise CommandError("Indica --document-id o --file.")

        if options.get("document_id"):
            document = ElectronicFiscalDocument.objects.select_related("company", "issuer__company").get(pk=options["document_id"])
            if company and document.company_id != company.id:
                raise CommandError("El documento indicado no pertenece a la empresa seleccionada.")
            company = company or document.company
            signed_xml = document.signed_xml_content
            encf = document.encf
            issuer_id = document.issuer_id
            issuer_rnc = document.issuer.rnc
            if not signed_xml:
                raise CommandError("El documento no tiene signed_xml_content.")
        else:
            file_path = Path(options["file"])
            if not file_path.exists() or not file_path.is_file():
                raise CommandError(f"No existe el archivo XML firmado: {file_path}")
            signed_xml = file_path.read_text(encoding="utf-8")
            encf = options.get("encf")
            issuer_id = options.get("issuer_id")
            issuer_rnc = options.get("issuer_rnc")
            if not encf:
                raise CommandError("--encf es requerido cuando se usa --file.")
            if not issuer_id and not issuer_rnc:
                raise CommandError("--issuer-id o --issuer-rnc es requerido cuando se usa --file.")

        try:
            environment = DGIIRESTEnvironmentResolver().resolve(options.get("environment"))
            context = resolve_manual_certificate_context(
                company=company,
                issuer_id=issuer_id,
                certificate_path=options.get("certificate_path"),
                certificate_password=options.get("certificate_password"),
                issuer_rnc=issuer_rnc,
            )
            issuer_rnc_digits = digits_only(context.issuer_rnc or issuer_rnc or "")
            if not issuer_rnc_digits:
                raise CommandError("No se pudo resolver RNC emisor para envio.")

            result = DGIIRESTClient(environment=environment).submit_ecf(
                signed_xml_content=signed_xml,
                encf=encf,
                issuer_rnc=issuer_rnc_digits,
                certificate_path=context.certificate_path,
                certificate_password=context.certificate_password,
            )

            self.stdout.write(self.style.SUCCESS("Envio DGII REST manual completado."))
            self.stdout.write(f"HTTP: {result.status_code}")
            self.stdout.write(f"Respuesta: {summarize_payload(result.result)}")
            self.stdout.write("Estados locales: no modificados")

            if options.get("save_artifact"):
                path = write_rest_artifact(
                    f"send-{encf}",
                    {
                        "document_id": document.id if document else None,
                        "encf": encf,
                        "issuer_rnc": issuer_rnc_digits,
                        "environment": environment.name,
                        "http_status": result.status_code,
                        "result": result.result,
                        "response_raw": result.response_xml,
                    },
                )
                self.stdout.write(f"Artifact: {path}")
        except ECFError as exc:
            raise CommandError(str(exc)) from exc
