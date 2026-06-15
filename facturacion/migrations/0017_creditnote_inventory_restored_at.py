from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0016_ecf_status_split_compat'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditnote',
            name='inventory_restored_at',
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
                    ('accepted', 'Aceptado'),
                    ('rejected', 'Rechazado'),
                    ('cancelled', 'Anulado'),
                    ('error', 'Error'),
                ],
                max_length=30,
            ),
        ),
    ]
