from django.db import migrations, models
import django.db.models.deletion


FISCAL_STATUSES = {"draft", "xml_generated", "signed", "submitted", "accepted", "rejected"}


def infer_fiscal_status(document):
    legacy_status = document.status
    if legacy_status in {"accepted", "rejected"}:
        return legacy_status
    if legacy_status in {"pending", "processing", "submitted"} or document.track_id:
        return "submitted"
    if legacy_status in {"draft", "xml_generated", "signed"}:
        return legacy_status
    if document.signed_xml_content:
        return "signed"
    if document.xml_content:
        return "xml_generated"
    return "draft"


def infer_job_status(document):
    if document.status == "queued":
        return "queued"
    if document.status in {"error", "cancelled"}:
        return "failed"
    return "idle"


def migration_reason(document, fiscal_status, job_status):
    legacy_status = document.status
    markers = [f"legacy_status={legacy_status}", f"inferred_fiscal_status={fiscal_status}", f"inferred_job_status={job_status}"]
    if document.track_id:
        markers.append("track_id_present=true")
    if document.signed_xml_content:
        markers.append("signed_xml_present=true")
    if document.xml_content:
        markers.append("xml_present=true")
    if legacy_status in {"queued", "error", "processing", "pending", "cancelled"}:
        markers.append("legacy_ambiguous=true")
    if legacy_status == "cancelled":
        markers.append("requires_manual_review=true")
    return "; ".join(markers)


def migrate_statuses(apps, schema_editor):
    ElectronicFiscalDocument = apps.get_model("facturacion", "ElectronicFiscalDocument")
    ECFStatusEvent = apps.get_model("facturacion", "ECFStatusEvent")

    for document in ElectronicFiscalDocument.objects.all().iterator():
        fiscal_status = infer_fiscal_status(document)
        job_status = infer_job_status(document)
        document.fiscal_status = fiscal_status
        document.job_status = job_status
        document.save(update_fields=["fiscal_status", "job_status", "updated_at"])
        ECFStatusEvent.objects.create(
            document=document,
            previous_fiscal_status=None,
            new_fiscal_status=fiscal_status,
            previous_job_status=None,
            new_job_status=job_status,
            source="migration_0016_ecf_status_split",
            reason=migration_reason(document, fiscal_status, job_status),
            task_id=document.async_task_id or None,
        )


def rollback_status_events(apps, schema_editor):
    ECFStatusEvent = apps.get_model("facturacion", "ECFStatusEvent")
    ECFStatusEvent.objects.filter(source="migration_0016_ecf_status_split").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0015_number_sequence"),
    ]

    operations = [
        migrations.AddField(
            model_name="electronicfiscaldocument",
            name="fiscal_status",
            field=models.CharField(
                choices=[
                    ("draft", "Borrador"),
                    ("xml_generated", "XML Generado"),
                    ("signed", "Firmado"),
                    ("submitted", "Enviado a DGII"),
                    ("accepted", "Aceptado"),
                    ("rejected", "Rechazado"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
                verbose_name="Estado Fiscal",
            ),
        ),
        migrations.AddField(
            model_name="electronicfiscaldocument",
            name="job_status",
            field=models.CharField(
                choices=[
                    ("idle", "Inactivo"),
                    ("queued", "En Cola"),
                    ("running", "Ejecutando"),
                    ("retrying", "Reintentando"),
                    ("failed", "Fallido"),
                ],
                db_index=True,
                default="idle",
                max_length=20,
                verbose_name="Estado Técnico",
            ),
        ),
        migrations.CreateModel(
            name="ECFStatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_fiscal_status", models.CharField(blank=True, max_length=20, null=True)),
                ("new_fiscal_status", models.CharField(blank=True, max_length=20, null=True)),
                ("previous_job_status", models.CharField(blank=True, max_length=20, null=True)),
                ("new_job_status", models.CharField(blank=True, max_length=20, null=True)),
                ("source", models.CharField(max_length=80)),
                ("reason", models.TextField(blank=True, null=True)),
                ("task_id", models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_events",
                        to="facturacion.electronicfiscaldocument",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de Estado e-CF",
                "verbose_name_plural": "Eventos de Estado e-CF",
                "ordering": ["-created_at"],
            },
        ),
        migrations.RunPython(migrate_statuses, rollback_status_events),
    ]
