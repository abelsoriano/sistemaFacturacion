from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Count


def validate_number_sequence_company_integrity(apps, schema_editor):
    NumberSequence = apps.get_model('facturacion', 'NumberSequence')

    null_sequence_ids = list(
        NumberSequence.objects.filter(company__isnull=True).values_list('id', flat=True)
    )
    duplicate_default_scopes = list(
        NumberSequence.objects.filter(issuer__isnull=True)
        .values('company_id', 'code', 'scope_key', 'branch_code')
        .annotate(count=Count('id'))
        .filter(count__gt=1)[:20]
    )
    duplicate_issuer_scopes = list(
        NumberSequence.objects.filter(issuer__isnull=False)
        .values('company_id', 'code', 'scope_key', 'issuer_id', 'branch_code')
        .annotate(count=Count('id'))
        .filter(count__gt=1)[:20]
    )
    cross_company_issuer_ids = list(
        NumberSequence.objects.filter(issuer__isnull=False)
        .exclude(company_id=models.F('issuer__company_id'))
        .values_list('id', flat=True)
    )

    if (
        null_sequence_ids
        or duplicate_default_scopes
        or duplicate_issuer_scopes
        or cross_company_issuer_ids
    ):
        raise RuntimeError(
            "No se puede hacer obligatorio NumberSequence.company. "
            f"secuencias_sin_company={null_sequence_ids}, "
            f"duplicados_default={duplicate_default_scopes}, "
            f"duplicados_issuer={duplicate_issuer_scopes}, "
            f"issuer_cross_company={cross_company_issuer_ids}."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0033_number_sequence_company_scoped'),
    ]

    operations = [
        migrations.RunPython(validate_number_sequence_company_integrity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='numbersequence',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='number_sequences',
                to='facturacion.company',
            ),
        ),
    ]
