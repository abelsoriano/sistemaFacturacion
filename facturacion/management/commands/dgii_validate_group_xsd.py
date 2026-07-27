from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.validators.xsd import ECFXSDValidator
from facturacion.models import DGIICertificationDocument, DGIICertificationPlan


class Command(BaseCommand):
    help = 'Valida contra XSD local los XML firmados de un grupo de certificacion DGII.'

    def add_arguments(self, parser):
        parser.add_argument('--plan-id', type=int, required=True)
        parser.add_argument('--group', type=int, default=1)

    def handle(self, *args, **options):
        plan_id = options['plan_id']
        group_number = options['group']
        try:
            plan = DGIICertificationPlan.objects.get(id=plan_id)
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CommandError(f'No existe plan DGII con id={plan_id}.') from exc

        documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company, item__dgii_group=group_number)
            .order_by('item__source_row', 'id')
        )
        if not documents:
            self.stdout.write(self.style.WARNING(f'No hay documentos para plan={plan_id}, grupo={group_number}.'))
            return

        validator = ECFXSDValidator()
        ok = failed = 0
        self.stdout.write(f'Validacion XSD | plan={plan_id} | grupo={group_number} | documentos={len(documents)}')
        for document in documents:
            try:
                if not document.signed_xml_path:
                    raise ValueError('El documento no tiene signed_xml_path.')
                if not default_storage.exists(document.signed_xml_path):
                    raise ValueError(f'No existe XML firmado en storage: {document.signed_xml_path}')
                with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
                    signed_xml = signed_file.read().decode('utf-8')
                validator.validate(document.ecf_type, signed_xml)
            except Exception as exc:  # noqa: BLE001 - reporta el error exacto por eNCF.
                failed += 1
                self.stdout.write(self.style.ERROR(f'FAIL {document.encf} tipo={document.ecf_type}: {exc}'))
                continue
            ok += 1
            self.stdout.write(self.style.SUCCESS(f'OK   {document.encf} tipo={document.ecf_type}'))

        self.stdout.write(f'Resumen XSD: OK={ok} FAIL={failed}')
