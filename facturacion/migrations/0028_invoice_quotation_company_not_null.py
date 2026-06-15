from django.db import migrations, models
import django.db.models.deletion


def _single_company_from_products(detail_model, parent_field: str, parent_id: int):
    company_ids = set(
        detail_model.objects.filter(**{f"{parent_field}_id": parent_id})
        .exclude(product__company__isnull=True)
        .values_list("product__company_id", flat=True)
        .distinct()
    )
    return company_ids.pop() if len(company_ids) == 1 else None


def backfill_and_validate_company(apps, schema_editor):
    Invoice = apps.get_model("facturacion", "Invoice")
    InvoiceDetail = apps.get_model("facturacion", "InvoiceDetail")
    Quotation = apps.get_model("facturacion", "Quotation")
    QuotationDetail = apps.get_model("facturacion", "QuotationDetail")

    unresolved_invoices = []
    for invoice in Invoice.objects.filter(company__isnull=True).select_related("client", "origin_quotation"):
        company_id = None
        if invoice.client_id and invoice.client.company_id:
            company_id = invoice.client.company_id
        elif invoice.origin_quotation_id and invoice.origin_quotation.company_id:
            company_id = invoice.origin_quotation.company_id
        else:
            company_id = _single_company_from_products(InvoiceDetail, "invoice", invoice.id)

        if company_id:
            Invoice.objects.filter(pk=invoice.pk).update(company_id=company_id)
        else:
            unresolved_invoices.append(invoice.pk)

    unresolved_quotations = []
    for quotation in Quotation.objects.filter(company__isnull=True).select_related("client"):
        company_id = None
        if quotation.client_id and quotation.client.company_id:
            company_id = quotation.client.company_id
        else:
            company_id = _single_company_from_products(QuotationDetail, "quotation", quotation.id)

        if company_id:
            Quotation.objects.filter(pk=quotation.pk).update(company_id=company_id)
        else:
            unresolved_quotations.append(quotation.pk)

    remaining_invoice_nulls = Invoice.objects.filter(company__isnull=True).count()
    remaining_quotation_nulls = Quotation.objects.filter(company__isnull=True).count()
    errors = []
    if unresolved_invoices or remaining_invoice_nulls:
        errors.append(
            f"Invoice unresolved_ids={unresolved_invoices} remaining_nulls={remaining_invoice_nulls}"
        )
    if unresolved_quotations or remaining_quotation_nulls:
        errors.append(
            f"Quotation unresolved_ids={unresolved_quotations} remaining_nulls={remaining_quotation_nulls}"
        )
    if errors:
        raise RuntimeError(
            "No se puede aplicar company NOT NULL en Invoice/Quotation. "
            + " | ".join(errors)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0027_low_risk_company_not_null"),
    ]

    operations = [
        migrations.RunPython(backfill_and_validate_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="invoice",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="invoices",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="quotation",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="quotations",
                to="facturacion.company",
            ),
        ),
    ]
