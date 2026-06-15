from django.db import migrations, models
import django.db.models.deletion


def backfill_and_validate_credit_note_company(apps, schema_editor):
    CreditNote = apps.get_model("facturacion", "CreditNote")

    unresolved = []
    for note in CreditNote.objects.filter(company__isnull=True).select_related("origin_invoice"):
        company_id = getattr(note.origin_invoice, "company_id", None)
        if company_id:
            CreditNote.objects.filter(pk=note.pk).update(company_id=company_id)
        else:
            unresolved.append(note.pk)

    remaining_nulls = CreditNote.objects.filter(company__isnull=True).count()
    if unresolved or remaining_nulls:
        raise RuntimeError(
            "No se puede aplicar company NOT NULL en CreditNote. "
            f"unresolved_ids={unresolved} remaining_nulls={remaining_nulls}"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0028_invoice_quotation_company_not_null"),
    ]

    operations = [
        migrations.RunPython(backfill_and_validate_credit_note_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="creditnote",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="credit_notes",
                to="facturacion.company",
            ),
        ),
    ]
