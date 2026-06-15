from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.rest.clients import DGIIRESTClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.manual_tools import resolve_manual_certificate_context, summarize_payload, write_rest_artifact


class Command(BaseCommand):
    help = "Query DGII REST result by TrackID without changing local fiscal/job status."

    def add_arguments(self, parser):
        parser.add_argument("--track-id", required=True, help="DGII TrackID to query.")
        parser.add_argument("--environment", default=None, help="DGII environment key. Defaults to ECF_DGII_ENVIRONMENT.")
        parser.add_argument("--company-id", type=int, default=None, help="Company context used to validate issuer/certificate.")
        parser.add_argument("--issuer-id", type=int, default=None, help="Issuer config used to resolve certificate/RNC.")
        parser.add_argument("--issuer-rnc", default=None, help="Issuer RNC for authentication context.")
        parser.add_argument("--certificate-path", default=None, help="PKCS#12 certificate path.")
        parser.add_argument("--certificate-password", default=None, help="PKCS#12 password. Prefer ECF_CERTIFICATE_PASSWORD.")
        parser.add_argument("--save-artifact", action="store_true", help="Persist raw DGII response in media/ecf/rest-tests.")

    def handle(self, *args, **options):
        try:
            environment = DGIIRESTEnvironmentResolver().resolve(options.get("environment"))
            context = resolve_manual_certificate_context(
                company_id=options.get("company_id"),
                issuer_id=options.get("issuer_id"),
                certificate_path=options.get("certificate_path"),
                certificate_password=options.get("certificate_password"),
                issuer_rnc=options.get("issuer_rnc"),
            )
            result = DGIIRESTClient(environment=environment).query_status(
                track_id=options["track_id"],
                certificate_path=context.certificate_path,
                certificate_password=context.certificate_password,
                issuer_rnc=context.issuer_rnc,
            )

            self.stdout.write(self.style.SUCCESS("Consulta DGII REST completada."))
            self.stdout.write(f"HTTP: {result.status_code}")
            self.stdout.write(f"Respuesta: {summarize_payload(result.result)}")
            self.stdout.write(f"Estados locales: no modificados")

            if options.get("save_artifact"):
                path = write_rest_artifact(
                    f"trackid-{options['track_id']}",
                    {
                        "track_id": options["track_id"],
                        "environment": environment.name,
                        "http_status": result.status_code,
                        "result": result.result,
                        "response_raw": result.response_xml,
                    },
                )
                self.stdout.write(f"Artifact: {path}")
        except ECFError as exc:
            raise CommandError(str(exc)) from exc
