import uuid

from django.db import migrations, models
from django.db.models import F, Q
from django.utils import timezone


UNCERTAIN_OUTCOMES = ("in_flight", "unknown")


def backfill_crash_safe_attempts(apps, schema_editor):
    """Attach conservative fences to legacy attempts that may have reached DGII."""
    Document = apps.get_model("facturacion", "DGIICertificationDocument")
    migration_marker_at = timezone.now()

    missing_fingerprint = Document.objects.filter(
        submission_outcome__in=UNCERTAIN_OUTCOMES,
    ).filter(Q(submission_fingerprint="") | Q(submission_fingerprint__isnull=True))
    if missing_fingerprint.exists():
        ids = list(missing_fingerprint.order_by("pk").values_list("pk", flat=True)[:20])
        raise RuntimeError(
            "Crash-safe certification migration stopped: legacy in_flight/unknown "
            f"documents lack a verifiable submission_fingerprint: {ids}."
        )

    for document in Document.objects.filter(
        submission_outcome__in=UNCERTAIN_OUTCOMES,
    ).order_by("pk").iterator():
        original_started_at = document.submission_started_at
        conservative_marker = original_started_at or migration_marker_at
        document.submission_attempt_token = uuid.uuid4()
        document.submission_started_at = conservative_marker
        document.submission_dispatch_started_at = conservative_marker
        document.save(update_fields=[
            "submission_attempt_token",
            "submission_started_at",
            "submission_dispatch_started_at",
        ])

    unsafe = Document.objects.filter(submission_outcome__in=UNCERTAIN_OUTCOMES).filter(
        Q(submission_attempt_token__isnull=True)
        | Q(submission_fingerprint="")
        | Q(submission_started_at__isnull=True)
        | Q(submission_dispatch_started_at__isnull=True)
    )
    if unsafe.exists():
        raise RuntimeError(
            "Crash-safe certification migration validation failed for uncertain attempts."
        )


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("facturacion", "0056_dgii_certification_submission_reconciliation"),
    ]

    operations = [
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="submission_attempt_token",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="dgiicertificationdocument",
            name="submission_dispatch_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="dgiicertificationdocument",
            name="submission_outcome",
            field=models.CharField(
                choices=[
                    ("not_started", "No iniciado"),
                    ("claimed", "Reclamado para envío"),
                    ("in_flight", "Envío en curso"),
                    ("confirmed", "Envío confirmado"),
                    ("unknown", "Resultado desconocido"),
                    ("manual_review", "Revisión manual"),
                ],
                default="not_started",
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_crash_safe_attempts, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="dgiicertificationdocument",
            name="cert_inflight_has_metadata",
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(submission_outcome="not_started")
                    | (
                        Q(submission_attempt_token__isnull=True)
                        & Q(submission_dispatch_started_at__isnull=True)
                    )
                ),
                name="cert_not_started_no_dispatch",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(submission_outcome="claimed")
                    | (
                        Q(submission_attempt_token__isnull=False)
                        & ~Q(submission_fingerprint="")
                        & Q(submission_started_at__isnull=False)
                        & Q(submission_dispatch_started_at__isnull=True)
                    )
                ),
                name="cert_claimed_has_metadata",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(submission_outcome__in=UNCERTAIN_OUTCOMES)
                    | (
                        Q(submission_attempt_token__isnull=False)
                        & ~Q(submission_fingerprint="")
                        & Q(submission_started_at__isnull=False)
                        & Q(submission_dispatch_started_at__isnull=False)
                    )
                ),
                name="cert_uncertain_has_metadata",
            ),
        ),
        migrations.AddConstraint(
            model_name="dgiicertificationdocument",
            constraint=models.CheckConstraint(
                condition=(
                    Q(submission_dispatch_started_at__isnull=True)
                    | Q(submission_dispatch_started_at__gte=F("submission_started_at"))
                ),
                name="cert_dispatch_after_claim",
            ),
        ),
    ]
