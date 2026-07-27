from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = 'Marca documentos de certificacion DGII como pendientes de reenvio, sin tocar XML ni enviar a DGII.'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True)
        parser.add_argument('--data-ecf', action='store_true', help='Marca Datos e-CF: backend groups 1 + 2.')
        parser.add_argument('--rfce', action='store_true', help='Marca RFCE: backend group 3.')
        parser.add_argument(
            '--reason',
            default='El portal DGII reinicio el set de pruebas; requiere reenvio desde Assys.',
        )

    def handle(self, *args, **options):
        if not options['data_ecf'] and not options['rfce']:
            raise CommandError('Debe indicar al menos una fase: --data-ecf o --rfce.')

        try:
            plan = DGIICertificationPlan.objects.get(id=options['plan_id'])
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CommandError(f'No existe plan DGII con id={options["plan_id"]}.') from exc

        submitter = DGIICertificationDGIISubmitter()
        data_ecf_marked = 0
        rfce_marked = 0

        if options['data_ecf']:
            data_ecf_marked = submitter.mark_data_ecf_acceptances_stale(
                plan=plan,
                reason=options['reason'],
            )
        if options['rfce']:
            rfce_marked = submitter.mark_acceptances_stale(
                plan=plan,
                groups=(3,),
                reason=options['reason'],
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Documentos marcados para reenvio: '
                f'Datos e-CF={data_ecf_marked}, RFCE={rfce_marked}. No se envio XML.'
            )
        )
