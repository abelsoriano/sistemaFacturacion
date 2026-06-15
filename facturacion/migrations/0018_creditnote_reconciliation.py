from django.db import migrations, models
from django.utils import timezone


def seed_credit_note_reconciliation(apps, schema_editor):
    CreditNote = apps.get_model('facturacion', 'CreditNote')
    now = timezone.now()

    for note in CreditNote.objects.select_related('electronic_document').all():
        document = getattr(note, 'electronic_document', None)
        fiscal_status = getattr(document, 'fiscal_status', None) or getattr(document, 'status', None)
        updates = {}

        if fiscal_status == 'accepted':
            updates = {
                'fiscal_resolution_status': 'confirmed',
                'inventory_reconciliation_status': 'confirmed',
                'inventory_reconciled_at': getattr(document, 'accepted_at', None) or now,
                'requires_manual_review': False,
            }
        elif fiscal_status == 'rejected':
            updates = {
                'fiscal_resolution_status': 'rejected',
                'inventory_reconciliation_status': 'compensation_required',
                'requires_manual_review': True,
            }
        else:
            updates = {
                'fiscal_resolution_status': 'pending',
                'inventory_reconciliation_status': 'restored_pending' if note.inventory_restored_at else 'confirmed',
                'requires_manual_review': False,
            }

        CreditNote.objects.filter(pk=note.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0017_creditnote_inventory_restored_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditnote',
            name='fiscal_resolution_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('confirmed', 'Confirmada'),
                    ('rejected', 'Rechazada'),
                    ('resolved', 'Resuelta'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='inventory_reconciliation_status',
            field=models.CharField(
                choices=[
                    ('restored_pending', 'Restaurado Pendiente'),
                    ('confirmed', 'Confirmado'),
                    ('compensation_required', 'Compensacion Requerida'),
                    ('compensated', 'Compensado'),
                ],
                default='restored_pending',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='inventory_reconciled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='inventory_compensated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='requires_manual_review',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='manual_reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ecfeventlog',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('created', 'Creado'),
                    ('queued', 'Encolado'),
                    ('xml_generated', 'XML Generado'),
                    ('signed', 'Firmado'),
                    ('submitted', 'Enviado'),
                    ('status_checked', 'Estado Consultado'),
                    ('retry_scheduled', 'Reintento Programado'),
                    ('skipped', 'Omitido'),
                    ('inventory_restored', 'Inventario Restaurado'),
                    ('inventory_compensated', 'Inventario Compensado'),
                    ('manual_review', 'Revision Manual'),
                    ('accepted', 'Aceptado'),
                    ('rejected', 'Rechazado'),
                    ('cancelled', 'Anulado'),
                    ('error', 'Error'),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(seed_credit_note_reconciliation, migrations.RunPython.noop),
    ]
