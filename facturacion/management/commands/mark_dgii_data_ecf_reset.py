from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from facturacion.models import DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = 'Marca aceptaciones locales de Datos e-CF como obsoletas por reinicio DGII, sin enviar XML.'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True)
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--evidence', required=True, help='Referencia verificable del reset en DGII.')
        parser.add_argument('--confirm', action='store_true')
        parser.add_argument(
            '--reason',
            default='Las pruebas de datos de eCF han sido reiniciadas debido a que se han rechazado comprobantes.',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError('Debe confirmar explícitamente el reset con --confirm.')
        try:
            plan = DGIICertificationPlan.objects.get(id=options['plan_id'])
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CommandError(f'No existe plan DGII con id={options["plan_id"]}.') from exc

        try:
            actor = get_user_model().objects.get(pk=options['user_id'])
        except get_user_model().DoesNotExist as exc:
            raise CommandError('El usuario autorizante no existe.') from exc

        affected = DGIICertificationDGIISubmitter().mark_data_ecf_acceptances_stale(
            plan=plan,
            user=actor,
            reason=options['reason'],
            evidence=options['evidence'],
            confirmed=True,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Aceptaciones de Datos e-CF marcadas como obsoletas: {affected}. No se envio XML.'
            )
        )
