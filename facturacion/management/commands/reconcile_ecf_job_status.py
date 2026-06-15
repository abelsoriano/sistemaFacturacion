from django.core.management.base import BaseCommand

from facturacion.ecf.services.job_reconciliation import ECFJobStatusReconciliationService


class Command(BaseCommand):
    help = "Reconcile stale e-CF job_status values for terminal fiscal documents."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Maximum number of documents to reconcile.")

    def handle(self, *args, **options):
        reconciled = ECFJobStatusReconciliationService().reconcile_terminal_queryset(limit=options.get("limit"))
        self.stdout.write(self.style.SUCCESS(f"Documentos e-CF reconciliados: {reconciled}"))
