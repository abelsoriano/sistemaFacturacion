from django.db import migrations, models
from django.db.models import Q


CONFIRMED_STATUSES = {
    "accepted",
    "rejected",
    "submit_conflict",
    "ready_for_portal_upload",
    "uploaded_to_portal",
    "accepted_by_portal",
}

AMBIGUOUS_STATUSES = {
    "submitted",
    "submit_error",
}


def backfill_submission_state(apps, schema_editor):
    Document = apps.get_model(
        "facturacion",
        "DGIICertificationDocument",
    )

    queryset = Document.objects.all().only(
        "pk",
        "status",
        "dgii_track_id",
        "submitted_at",
        "submit_error",
    )

    confirmed_ids = []
    manual_review_ids = []
    not_started_ids = []

    for document in queryset.iterator(chunk_size=500):
        has_track_id = bool((document.dgii_track_id or "").strip())

        if has_track_id or document.status in CONFIRMED_STATUSES:
            confirmed_ids.append(document.pk)
        elif (
            document.status in AMBIGUOUS_STATUSES
            or document.submitted_at is not None
        ):
            manual_review_ids.append(document.pk)
        else:
            not_started_ids.append(document.pk)

    if confirmed_ids:
        Document.objects.filter(pk__in=confirmed_ids).update(
            submission_outcome="confirmed",
            reconciliation_attempts=0,
            next_retry_at=None,
            reconciliation_lease_until=None,
            reconciliation_lease_token="",
            last_error="",
        )

    if manual_review_ids:
        for document in (
            Document.objects
            .filter(pk__in=manual_review_ids)
            .only("pk", "submit_error")
            .iterator(chunk_size=500)
        ):
            Document.objects.filter(pk=document.pk).update(
                submission_outcome="manual_review",
                reconciliation_attempts=0,
                next_retry_at=None,
                reconciliation_lease_until=None,
                reconciliation_lease_token="",
                last_error=(
                    document.submit_error
                    or "Documento histórico con evidencia de intento DGII "
                    "sin confirmación suficiente; requiere revisión manual."
                ),
            )

    if not_started_ids:
        Document.objects.filter(pk__in=not_started_ids).update(
            submission_outcome="not_started",
            reconciliation_attempts=0,
            next_retry_at=None,
            reconciliation_lease_until=None,
            reconciliation_lease_token="",
            last_error="",
        )

    if Document.objects.filter(submission_outcome__isnull=True).exists():
        raise RuntimeError(
            "Backfill DGII incompleto: existen documentos de certificación "
            "sin submission_outcome."
        )

    unsafe = Document.objects.filter(
        Q(dgii_track_id__gt="")
        | Q(status__in=CONFIRMED_STATUSES)
        | Q(status__in=AMBIGUOUS_STATUSES)
        | Q(submitted_at__isnull=False),
        submission_outcome="not_started",
    )
    if unsafe.exists():
        raise RuntimeError(
            "Backfill DGII inseguro: existen documentos históricos enviados "
            "clasificados como not_started."
        )


def reverse_backfill(apps, schema_editor):
    # Los campos se eliminan al revertir la migración.
    pass


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        (
            "facturacion",
            "0055_electronicfiscaldocument_reconciliation_lease",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="submission_outcome",
            field=models.CharField(
                blank=True,
                choices=[
                    ("not_started", "No iniciado"),
                    ("in_flight", "Envío en curso"),
                    ("confirmed", "Envío confirmado"),
                    ("unknown", "Resultado desconocido"),
                    ("manual_review", "Revisión manual"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="submission_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="submission_fingerprint",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="reconciliation_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="next_retry_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="reconciliation_lease_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="reconciliation_lease_token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="last_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(
            backfill_submission_state,
            reverse_code=reverse_backfill,
        ),
        migrations.AlterField(
            model_name="dgiicertificationdocument",
            name="submission_outcome",
            field=models.CharField(
                choices=[
                    ("not_started", "No iniciado"),
                    ("in_flight", "Envío en curso"),
                    ("confirmed", "Envío confirmado"),
                    ("unknown", "Resultado desconocido"),
                    ("manual_review", "Revisión manual"),
                ],
                default="not_started",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="dgiicertificationdocument",
            index=models.Index(
                fields=["submission_outcome", "next_retry_at"],
                name="cert_sub_out_retry_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dgiicertificationdocument",
            index=models.Index(
                fields=["submission_outcome", "submission_started_at"],
                name="cert_sub_out_start_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="dgiicertificationdocument",
            index=models.Index(
                fields=["plan", "submission_outcome", "next_retry_at"],
                name="cert_plan_out_retry_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(submission_outcome="in_flight")
                    | (
                        Q(submission_started_at__isnull=False)
                        & ~Q(submission_fingerprint="")
                    )
                ),
                name="cert_inflight_has_metadata",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    (
                        Q(reconciliation_lease_until__isnull=True)
                        & Q(reconciliation_lease_token="")
                    )
                    | (
                        Q(reconciliation_lease_until__isnull=False)
                        & ~Q(reconciliation_lease_token="")
                    )
                ),
                name="cert_lease_fields_consistent",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(submission_outcome="manual_review")
                    | (
                        Q(next_retry_at__isnull=True)
                        & Q(reconciliation_lease_until__isnull=True)
                        & Q(reconciliation_lease_token="")
                    )
                ),
                name="cert_manual_review_not_queued",
            ),
        ),
    ]
