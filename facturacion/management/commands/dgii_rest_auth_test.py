from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.exceptions import ECFError
from facturacion.ecf.rest.auth import DGIIRESTAuthClient
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.rest.manual_tools import mask_token, resolve_manual_certificate_context, write_rest_artifact
from facturacion.ecf.signer.xml_signer import ECFXMLSigner


class Command(BaseCommand):
    help = "Run an isolated DGII REST authentication test without touching fiscal documents."

    def add_arguments(self, parser):
        parser.add_argument("--environment", default=None, help="DGII environment key. Defaults to ECF_DGII_ENVIRONMENT.")
        parser.add_argument("--company-id", type=int, default=None, help="Company context used to validate issuer/certificate.")
        parser.add_argument("--issuer-id", type=int, default=None, help="Issuer config used to resolve certificate/RNC.")
        parser.add_argument("--issuer-rnc", default=None, help="Issuer RNC for token cache/audit context.")
        parser.add_argument("--certificate-path", default=None, help="PKCS#12 certificate path. Password is never printed.")
        parser.add_argument("--certificate-password", default=None, help="PKCS#12 password. Prefer ECF_CERTIFICATE_PASSWORD.")
        parser.add_argument("--save-artifacts", action="store_true", help="Persist sanitized seed/token metadata.")

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
            auth_client = DGIIRESTAuthClient(environment=environment)

            self.stdout.write(f"Ambiente: {environment.name}")
            self.stdout.write(f"Auth URL: {environment.auth_base_url}")
            self.stdout.write("Solicitando semilla DGII...")
            seed = auth_client.request_seed()
            self.stdout.write(f"Semilla recibida: {len(seed.xml)} caracteres")

            certificate = PKCS12CertificateLoader().load(context.certificate_path, context.certificate_password)
            signed_seed = ECFXMLSigner().sign(seed.xml, certificate)
            self.stdout.write(f"Semilla firmada: {len(signed_seed)} caracteres")

            token = auth_client.validate_seed(signed_seed)
            self.stdout.write(self.style.SUCCESS("Token DGII obtenido correctamente."))
            self.stdout.write(f"Token: {mask_token(token.value)}")
            self.stdout.write(f"Expira en: {token.expires_in} segundos")

            if options.get("save_artifacts"):
                path = write_rest_artifact(
                    "auth-test",
                    {
                        "environment": environment.name,
                        "auth_base_url": environment.auth_base_url,
                        "issuer_rnc": context.issuer_rnc,
                        "seed_length": len(seed.xml),
                        "signed_seed_length": len(signed_seed),
                        "token_masked": mask_token(token.value),
                        "expires_in": token.expires_in,
                    },
                )
                self.stdout.write(f"Artifact: {path}")
        except ECFError as exc:
            raise CommandError(str(exc)) from exc
