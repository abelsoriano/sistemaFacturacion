from django.db import migrations, models


def backfill_and_validate_electronic_document_company(apps, schema_editor):
    ElectronicFiscalDocument = apps.get_model('facturacion', 'ElectronicFiscalDocument')

    unresolved_document_ids = []
    for document in (
        ElectronicFiscalDocument.objects.filter(company__isnull=True)
        .select_related('invoice', 'credit_note', 'issuer', 'sequence')
    ):
        company_id = None
        if document.invoice_id and document.invoice.company_id:
            company_id = document.invoice.company_id
        elif document.credit_note_id and document.credit_note.company_id:
            company_id = document.credit_note.company_id
        elif document.issuer_id and document.issuer.company_id:
            company_id = document.issuer.company_id
        elif document.sequence_id and document.sequence.company_id:
            company_id = document.sequence.company_id

        if company_id:
            ElectronicFiscalDocument.objects.filter(pk=document.pk).update(company_id=company_id)
        else:
            unresolved_document_ids.append(document.pk)

    null_count = ElectronicFiscalDocument.objects.filter(company__isnull=True).count()
    invoice_mismatch_ids = list(
        ElectronicFiscalDocument.objects.exclude(invoice__isnull=True)
        .exclude(company_id=models.F('invoice__company_id'))
        .values_list('id', flat=True)
    )
    credit_note_mismatch_ids = list(
        ElectronicFiscalDocument.objects.exclude(credit_note__isnull=True)
        .exclude(company_id=models.F('credit_note__company_id'))
        .values_list('id', flat=True)
    )
    issuer_mismatch_ids = list(
        ElectronicFiscalDocument.objects.exclude(issuer__isnull=True)
        .exclude(company_id=models.F('issuer__company_id'))
        .values_list('id', flat=True)
    )
    sequence_mismatch_ids = list(
        ElectronicFiscalDocument.objects.exclude(sequence__isnull=True)
        .exclude(company_id=models.F('sequence__company_id'))
        .values_list('id', flat=True)
    )

    if (
        null_count
        or unresolved_document_ids
        or invoice_mismatch_ids
        or credit_note_mismatch_ids
        or issuer_mismatch_ids
        or sequence_mismatch_ids
    ):
        raise RuntimeError(
            "No se puede hacer obligatorio company en ElectronicFiscalDocument. "
            f"documentos_sin_company={null_count}, "
            f"documentos_no_resueltos={unresolved_document_ids}, "
            f"invoice_cross_company={invoice_mismatch_ids}, "
            f"credit_note_cross_company={credit_note_mismatch_ids}, "
            f"issuer_cross_company={issuer_mismatch_ids}, "
            f"sequence_cross_company={sequence_mismatch_ids}."
        )


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0030_ecf_config_company_not_null'),
    ]

    operations = [
        migrations.RunPython(backfill_and_validate_electronic_document_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='electronicfiscaldocument',
            name='company',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='electronic_fiscal_documents',
                to='facturacion.company',
            ),
        ),
    ]
