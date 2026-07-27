from django.core.management.base import BaseCommand, CommandError

from facturacion.models import DGIICertificationDocument, DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationDGIISubmitter


class Command(BaseCommand):
    help = 'Reporta la ultima respuesta DGII guardada por documento de certificacion.'

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

        submitter = DGIICertificationDGIISubmitter()
        self.stdout.write(f'Plan {plan_id} | Grupo {group_number} | Documentos {len(documents)}')
        counts = self._counts(documents)
        self.stdout.write(
            'Conteo: '
            f'accepted_current={counts["accepted_current"]} | '
            f'accepted_stale={counts["accepted_stale"]} | '
            f'pending_resend={counts["pending_resend"]} | '
            f'rejected={counts["rejected"]} | '
            f'pending={counts["pending"]} | '
            f'sequence_already_used={counts["sequence_already_used"]} | '
            f'rfce_accepted={counts["rfce_accepted"]}'
        )
        self.stdout.write('eNCF | tipo | filename | hash | TrackID | status DGII | mensaje DGII')
        self.stdout.write('-' * 180)

        descuento = []
        recargo = []
        monto_gravado = []
        comprador = []

        for document in documents:
            message = self._message_for(document)
            status = self._status_for(document)
            diagnostic = self._diagnostic_for(submitter, document)
            self.stdout.write(
                f'{document.encf or "-"} | '
                f'{document.ecf_type or "-"} | '
                f'{diagnostic.get("multipart_filename") or "-"} | '
                f'{diagnostic.get("sha256") or document.signed_xml_hash or "-"} | '
                f'{document.dgii_track_id or "-"} | '
                f'{status or "-"} | '
                f'{message or "-"}'
            )
            normalized = message.lower()
            if 'descuentomonto' in normalized or 'tablasubdescuento' in normalized:
                descuento.append(document)
            if 'recargomonto' in normalized or 'tablasubrecargo' in normalized:
                recargo.append(document)
            if 'montogravadoi1' in normalized or 'montogravadoi2' in normalized:
                monto_gravado.append(document)
            if 'comprador' in normalized and ('expected' in normalized or 'esperaba' in normalized):
                comprador.append(document)

        self.stdout.write('')
        self.stdout.write('Rechazos detectados por respuesta guardada:')
        self._write_bucket('DescuentoMonto/TablaSubDescuento', descuento)
        self._write_bucket('RecargoMonto/TablaSubRecargo', recargo)
        self._write_bucket('MontoGravadoI1/I2', monto_gravado)
        self._write_bucket('Comprador estructural', comprador)

    def _counts(self, documents):
        pending_statuses = {
            DGIICertificationDocument.STATUS_PENDING,
            DGIICertificationDocument.STATUS_GENERATED,
            DGIICertificationDocument.STATUS_SIGNED,
            DGIICertificationDocument.STATUS_SUBMITTED,
            DGIICertificationDocument.STATUS_SUBMIT_ERROR,
        }
        return {
            'accepted_current': sum(
                1 for document in documents
                if document.status == DGIICertificationDocument.STATUS_ACCEPTED and not document.accepted_stale
            ),
            'accepted_stale': sum(1 for document in documents if document.accepted_stale),
            'pending_resend': sum(1 for document in documents if document.accepted_stale),
            'rejected': sum(1 for document in documents if document.status == DGIICertificationDocument.STATUS_REJECTED),
            'pending': sum(1 for document in documents if document.status in pending_statuses),
            'sequence_already_used': sum(
                1 for document in documents
                if document.status == DGIICertificationDocument.STATUS_SUBMIT_CONFLICT
            ),
            'rfce_accepted': sum(
                1 for document in documents
                if document.ecf_type == 'RFCE'
                and document.status == DGIICertificationDocument.STATUS_ACCEPTED
                and not document.accepted_stale
            ),
        }

    def _status_for(self, document):
        if document.accepted_stale:
            return 'Aceptado obsoleto / requiere reenvio'
        if document.status == DGIICertificationDocument.STATUS_SUBMIT_CONFLICT:
            return 'Secuencia ya usada'
        if document.status == DGIICertificationDocument.STATUS_ACCEPTED:
            return 'Aceptado'
        if document.status == DGIICertificationDocument.STATUS_REJECTED:
            return 'Rechazado'
        return document.dgii_status or document.status

    def _message_for(self, document):
        parts = []
        if document.dgii_response_message:
            parts.append(document.dgii_response_message)
        if document.submit_error:
            parts.append(document.submit_error)
        if document.dgii_response:
            text = str(document.dgii_response)
            if text and text not in parts:
                parts.append(text)
        return ' | '.join(parts)

    def _diagnostic_for(self, submitter, document):
        try:
            return submitter._inspect_document_submit_payload(document)
        except Exception:
            return {}

    def _write_bucket(self, title, documents):
        if not documents:
            self.stdout.write(f'- {title}: no aparece en respuestas guardadas.')
            return
        values = ', '.join(f'{document.encf} ({document.ecf_type})' for document in documents)
        self.stdout.write(f'- {title}: {values}')
