from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from facturacion.models import DGIICertificationPlan
from facturacion.services.certification_reset import CertificationResetService


class Command(BaseCommand):
    help = 'Marca documentos de certificacion DGII como pendientes de reenvio, sin tocar XML ni enviar a DGII.'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True)
        parser.add_argument('--data-ecf', action='store_true', help='Marca Datos e-CF: backend groups 1 + 2.')
        parser.add_argument('--rfce', action='store_true', help='Marca RFCE: backend group 3.')
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--evidence', required=True, help='Referencia verificable del reset en DGII.')
        parser.add_argument('--confirm', action='store_true')
        parser.add_argument(
            '--reason',
            default='El portal DGII reinicio el set de pruebas; requiere reenvio desde Assys.',
        )

    def handle(self, *args, **options):
        if not options['data_ecf'] and not options['rfce']:
            raise CommandError('Debe indicar al menos una fase: --data-ecf o --rfce.')
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
        groups = []
        if options['data_ecf']:
            groups.extend((1, 2))
        if options['rfce']:
            groups.append(3)
        result = CertificationResetService().apply_reset(
            plan_id=plan.pk,
            groups=groups,
            source=CertificationResetService.SOURCE_MANUAL,
            reason=options['reason'],
            evidence=options['evidence'],
            actor=actor,
            confirmed=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Documentos marcados para reenvio: '
                f'total={result.applied}, idempotentes={result.idempotent}. No se envio XML.'
            )
        )
