from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('facturacion', '0011_ecf_async_processing'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoice',
            options={
                'ordering': ['-created_at'],
                'permissions': [('reverse_invoice', 'Can create fiscal invoice reversals')],
                'verbose_name': 'Factura',
                'verbose_name_plural': 'Facturas',
            },
        ),
        migrations.AddField(
            model_name='ecfissuerconfig',
            name='auto_ecf_rules_enabled',
            field=models.BooleanField(default=True, verbose_name='Reglas automáticas E31/E32'),
        ),
        migrations.AddField(
            model_name='ecfissuerconfig',
            name='certificate_password',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Clave Certificado'),
        ),
        migrations.AddField(
            model_name='ecfissuerconfig',
            name='certificate_path',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Ruta Certificado P12'),
        ),
        migrations.AddField(
            model_name='ecfissuerconfig',
            name='default_ecf_type',
            field=models.CharField(choices=[('31', 'Factura de Crédito Fiscal Electrónica'), ('32', 'Factura de Consumo Electrónica')], default='32', max_length=2, verbose_name='Tipo e-CF por defecto'),
        ),
        migrations.CreateModel(
            name='CreditNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credit_note_number', models.CharField(blank=True, max_length=20, unique=True, verbose_name='N° Nota de Crédito')),
                ('reversal_type', models.CharField(choices=[('partial', 'Parcial'), ('total', 'Total')], default='partial', max_length=20)),
                ('reason', models.TextField(verbose_name='Motivo fiscal')),
                ('subtotal', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('tax', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('discount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('status', models.CharField(choices=[('draft', 'Borrador'), ('issued', 'Emitida'), ('cancelled', 'Anulada')], default='issued', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('origin_invoice', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='credit_notes', to='facturacion.invoice', verbose_name='Factura origen')),
            ],
            options={
                'verbose_name': 'Nota de Crédito',
                'verbose_name_plural': 'Notas de Crédito',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CreditNoteDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('credit_note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='facturacion.creditnote')),
                ('origin_detail', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='credit_note_details', to='facturacion.invoicedetail')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='facturacion.product')),
            ],
        ),
        migrations.AlterField(
            model_name='electronicfiscaldocument',
            name='invoice',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='electronic_document', to='facturacion.invoice', verbose_name='Factura'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='credit_note',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='electronic_document', to='facturacion.creditnote', verbose_name='Nota de Crédito'),
        ),
    ]
