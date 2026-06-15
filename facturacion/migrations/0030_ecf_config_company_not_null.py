from django.db import migrations, models


def _get_default_company(apps):
    Company = apps.get_model('facturacion', 'Company')
    company = Company.objects.filter(is_active=True).order_by('id').first()
    if company:
        return company
    company = Company.objects.order_by('id').first()
    if company:
        return company
    raise RuntimeError(
        "No existe una empresa default para asignar configuracion fiscal e-CF."
    )


def backfill_and_validate_ecf_config_company(apps, schema_editor):
    ECFIssuerConfig = apps.get_model('facturacion', 'ECFIssuerConfig')
    ECFSequence = apps.get_model('facturacion', 'ECFSequence')
    default_company = _get_default_company(apps)

    ECFIssuerConfig.objects.filter(company__isnull=True).update(company=default_company)

    unresolved_sequence_ids = []
    for sequence in ECFSequence.objects.filter(company__isnull=True).select_related('issuer'):
        company_id = sequence.issuer.company_id if sequence.issuer_id else default_company.id
        if company_id:
            ECFSequence.objects.filter(pk=sequence.pk).update(company_id=company_id)
        else:
            unresolved_sequence_ids.append(sequence.pk)

    issuer_nulls = ECFIssuerConfig.objects.filter(company__isnull=True).count()
    sequence_nulls = ECFSequence.objects.filter(company__isnull=True).count()
    mismatched_sequence_ids = list(
        ECFSequence.objects.exclude(issuer__isnull=True)
        .exclude(company_id=models.F('issuer__company_id'))
        .values_list('id', flat=True)
    )

    if issuer_nulls or sequence_nulls or unresolved_sequence_ids or mismatched_sequence_ids:
        raise RuntimeError(
            "No se puede hacer obligatorio company en configuracion e-CF. "
            f"issuers_sin_company={issuer_nulls}, sequences_sin_company={sequence_nulls}, "
            f"sequences_no_resueltas={unresolved_sequence_ids}, "
            f"sequences_cross_company={mismatched_sequence_ids}."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0029_creditnote_company_not_null'),
    ]

    operations = [
        migrations.RunPython(backfill_and_validate_ecf_config_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ecfissuerconfig',
            name='company',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='ecf_issuers',
                to='facturacion.company',
            ),
        ),
        migrations.AlterField(
            model_name='ecfsequence',
            name='company',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='ecf_sequences',
                to='facturacion.company',
            ),
        ),
    ]
