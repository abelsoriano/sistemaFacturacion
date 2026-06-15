from django.db import migrations, models
from django.db.models import Count


def validate_encf_duplicates_per_issuer(apps, schema_editor):
    ElectronicFiscalDocument = apps.get_model('facturacion', 'ElectronicFiscalDocument')

    duplicates = list(
        ElectronicFiscalDocument.objects
        .exclude(encf__isnull=True)
        .exclude(encf='')
        .values('issuer_id', 'encf')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .values('issuer_id', 'encf', 'count')[:20]
    )
    if duplicates:
        raise RuntimeError(
            "No se puede aplicar unicidad e-NCF por emisor. "
            f"Existen documentos duplicados dentro del mismo emisor: {duplicates}."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0035_ecfissuerconfig_certificate_fingerprint_and_more'),
    ]

    operations = [
        migrations.RunPython(validate_encf_duplicates_per_issuer, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='electronicfiscaldocument',
            name='encf',
            field=models.CharField(max_length=13, verbose_name='e-NCF'),
        ),
        migrations.AddConstraint(
            model_name='electronicfiscaldocument',
            constraint=models.UniqueConstraint(
                fields=('issuer', 'encf'),
                name='unique_ecf_document_encf_per_issuer',
            ),
        ),
    ]
