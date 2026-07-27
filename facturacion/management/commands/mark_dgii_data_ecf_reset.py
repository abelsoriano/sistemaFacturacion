from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = 'Marca aceptaciones locales de Datos e-CF como obsoletas por reinicio DGII, sin enviar XML.'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True)
        parser.add_argument(
            '--reason',
            default='Las pruebas de datos de eCF han sido reiniciadas debido a que se han rechazado comprobantes.',
        )

    def handle(self, *args, **options):
        try:
            plan = DGIICertificationPlan.objects.get(id=options['plan_id'])
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CommandError(f'No existe plan DGII con id={options["plan_id"]}.') from exc

        affected = DGIICertificationDGIISubmitter().mark_data_ecf_acceptances_stale(
            plan=plan,
            reason=options['reason'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Aceptaciones de Datos e-CF marcadas como obsoletas: {affected}. No se envio XML.'
            )
        )
