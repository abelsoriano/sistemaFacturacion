from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.rest.clients import DGIIRESTClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.manual_tools import resolve_manual_certificate_context, summarize_payload, write_rest_artifact
from facturacion.models import Company, ElectronicFiscalDocument


class Command(BaseCommand):
    help = "Query DGII REST TrackIDs by issuer RNC and e-NCF without changing local state."

    def add_arguments(self, parser):
        parser.add_argument("--encf", default=None, help="e-NCF to query. Optional when --document-id is provided.")
        parser.add_argument("--document-id", type=int, default=None, help="Document used to infer e-NCF and issuer.")
        parser.add_argument("--environment", default=None, help="DGII environment key. Defaults to ECF_DGII_ENVIRONMENT.")
        parser.add_argument("--company-id", type=int, default=None, help="Company context used to validate document/issuer.")
        parser.add_argument("--issuer-id", type=int, default=None, help="Issuer config used to resolve certificate/RNC.")
        parser.add_argument("--issuer-rnc", default=None, help="Issuer RNC.")
        parser.add_argument("--certificate-path", default=None, help="PKCS#12 certificate path.")
        parser.add_argument("--certificate-password", default=None, help="PKCS#12 password. Prefer ECF_CERTIFICATE_PASSWORD.")
        parser.add_argument("--save-artifact", action="store_true", help="Persist raw DGII response in media/ecf/rest-tests.")

    def handle(self, *args, **options):
        document = None
        company = Company.objects.get(pk=options["company_id"]) if options.get("company_id") else None
        if options.get("document_id"):
            document = ElectronicFiscalDocument.objects.select_related("company", "issuer__company").get(pk=options["document_id"])
            if company and document.company_id != company.id:
                raise CommandError("El documento indicado no pertenece a la empresa seleccionada.")
            company = company or document.company

        encf = options.get("encf") or (document.encf if document else None)
        issuer_id = options.get("issuer_id") or (document.issuer_id if document else None)
        issuer_rnc = options.get("issuer_rnc") or (document.issuer.rnc if document else None)
        if not encf:
            raise CommandError("Indica --encf o --document-id.")
        if not issuer_rnc and not issuer_id:
            raise CommandError("Indica --issuer-rnc, --issuer-id o --document-id.")

        try:
            environment = DGIIRESTEnvironmentResolver().resolve(options.get("environment"))
            context = resolve_manual_certificate_context(
                company=company,
                issuer_id=issuer_id,
                certificate_path=options.get("certificate_path"),
                certificate_password=options.get("certificate_password"),
                issuer_rnc=issuer_rnc,
            )
            if not context.issuer_rnc:
                raise CommandError("No se pudo resolver RNC emisor para consulta TrackIDs.")

            result = DGIIRESTClient(environment=environment).query_trackids(
                issuer_rnc=context.issuer_rnc,
                encf=encf,
                certificate_path=context.certificate_path,
                certificate_password=context.certificate_password,
            )

            self.stdout.write(self.style.SUCCESS("Consulta TrackIDs DGII REST completada."))
            self.stdout.write(f"HTTP: {result.status_code}")
            self.stdout.write(f"Respuesta: {summarize_payload(result.result)}")
            self.stdout.write("Estados locales: no modificados")

            if options.get("save_artifact"):
                path = write_rest_artifact(
                    f"trackids-{encf}",
                    {
                        "encf": encf,
                        "issuer_rnc": context.issuer_rnc,
                        "environment": environment.name,
                        "http_status": result.status_code,
                        "result": result.result,
                        "response_raw": result.response_xml,
                    },
                )
                self.stdout.write(f"Artifact: {path}")
        except ECFError as exc:
            raise CommandError(str(exc)) from exc
