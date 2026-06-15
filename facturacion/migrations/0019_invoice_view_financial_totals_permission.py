from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0018_creditnote_reconciliation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={
                'ordering': ['-created_at'],
                'permissions': [
                    ('reverse_invoice', 'Can create fiscal invoice reversals'),
                    ('view_financial_totals', 'Can view financial totals'),
                ],
                'verbose_name': 'Factura',
                'verbose_name_plural': 'Facturas',
            },
        ),
    ]
