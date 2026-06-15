from django.db import migrations, models
from django.db.models import Count


def validate_commercial_document_number_duplicates(apps, schema_editor):
    checks = [
        ('Invoice', 'invoice_number'),
        ('Quotation', 'quotation_number'),
        ('CreditNote', 'credit_note_number'),
    ]
    errors = []
    for model_name, field_name in checks:
        model = apps.get_model('facturacion', model_name)
        duplicates = list(
            model.objects.values('company_id', field_name)
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .values('company_id', field_name, 'count')[:20]
        )
        if duplicates:
            errors.append(f"{model_name}.{field_name}: {duplicates}")

    if errors:
        raise RuntimeError(
            "No se puede aplicar unicidad por empresa en documentos comerciales. "
            "Existen numeros duplicados dentro de la misma empresa: "
            + " | ".join(errors)
        )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0031_electronic_fiscal_document_company_not_null'),
    ]

    operations = [
        migrations.RunPython(validate_commercial_document_number_duplicates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='creditnote',
            name='credit_note_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='N° Nota de Crédito'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='invoice_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='N° Factura'),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='quotation_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='N° Cotización'),
        ),
        migrations.AddConstraint(
            model_name='creditnote',
            constraint=models.UniqueConstraint(
                fields=('company', 'credit_note_number'),
                name='unique_credit_note_number_per_company',
            ),
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(
                fields=('company', 'invoice_number'),
                name='unique_invoice_number_per_company',
            ),
        ),
        migrations.AddConstraint(
            model_name='quotation',
            constraint=models.UniqueConstraint(
                fields=('company', 'quotation_number'),
                name='unique_quotation_number_per_company',
            ),
        ),
    ]
