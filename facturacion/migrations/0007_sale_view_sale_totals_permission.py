from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0006_alter_invoice_payment_method_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sale',
            options={
                'permissions': [
                    ('view_sale_totals', 'Can view sale totals'),
                ],
            },
        ),
    ]
