from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.certificates.metadata import ECFCertificateMetadataService
from facturacion.models import ECFIssuerConfig


class Command(BaseCommand):
    help = "Refresh non-secret DGII certificate metadata for issuer configurations."

    def add_arguments(self, parser):
        parser.add_argument("--issuer-id", type=int, default=None, help="Refresh a single issuer config.")

    def handle(self, *args, **options):
        queryset = ECFIssuerConfig.objects.all()
        if options.get("issuer_id"):
            queryset = queryset.filter(pk=options["issuer_id"])
            if not queryset.exists():
                raise CommandError("No existe el emisor indicado.")

        service = ECFCertificateMetadataService()
        refreshed = 0
        for issuer in queryset.order_by("id"):
            result = service.refresh(issuer)
            refreshed += 1
            self.stdout.write(
                f"Emisor {result.issuer.id}: certificado {result.status}"
            )

        self.stdout.write(self.style.SUCCESS(f"Metadata de certificados actualizada: {refreshed}"))
