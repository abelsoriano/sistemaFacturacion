from datetime import timedelta
import uuid

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class CertificationSubmissionCrashSafetyMigrationTests(TransactionTestCase):
    migrate_from = [("facturacion", "0056_dgii_certification_submission_reconciliation")]
    migrate_to = [("facturacion", "0057_certification_submission_crash_safety")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        self.Company = old_apps.get_model("facturacion", "Company")
        self.Plan = old_apps.get_model("facturacion", "DGIICertificationPlan")
        self.Item = old_apps.get_model("facturacion", "DGIICertificationItem")
        self.Document = old_apps.get_model("facturacion", "DGIICertificationDocument")
        self.company = self.Company.objects.create(name="Migration Company", rnc="101000001")
        self.plan = self.Plan.objects.create(
            company=self.company,
            source_filename="migration.xlsx",
            file_sha256="a" * 64,
        )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        super().tearDown()

    def _document(self, outcome, row, *, fingerprint="", started_at=None):
        item = self.Item.objects.create(
            plan=self.plan,
            company=self.company,
            ecf_type="31",
            dgii_group=1,
            encf=f"E31000000{row:04d}",
            source_sheet="ECF",
            source_row=row,
            raw_data={},
        )
        return self.Document.objects.create(
            plan=self.plan,
            company=self.company,
            item=item,
            ecf_type="31",
            encf=item.encf,
            status="signed",
            submission_outcome=outcome,
            submission_fingerprint=fingerprint,
            submission_started_at=started_at,
        )

    def _migrate_forward(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        return self.executor.loader.project_state(self.migrate_to).apps.get_model(
            "facturacion", "DGIICertificationDocument"
        )

    def test_backfill_preserves_outcomes_and_fences_only_uncertain_attempts(self):
        started_at = timezone.now() - timedelta(hours=1)
        rows = {
            "not_started": self._document("not_started", 1),
            "in_flight": self._document("in_flight", 2, fingerprint="a" * 64, started_at=started_at),
            "unknown": self._document("unknown", 3, fingerprint="b" * 64),
            "confirmed": self._document("confirmed", 4),
            "manual_review": self._document("manual_review", 5),
        }

        Document = self._migrate_forward()
        migrated = {name: Document.objects.get(pk=row.pk) for name, row in rows.items()}

        self.assertEqual(migrated["in_flight"].submission_outcome, "in_flight")
        self.assertEqual(migrated["unknown"].submission_outcome, "unknown")
        self.assertIsNotNone(migrated["in_flight"].submission_attempt_token)
        self.assertIsNotNone(migrated["unknown"].submission_attempt_token)
        self.assertEqual(migrated["in_flight"].submission_dispatch_started_at, started_at)
        self.assertEqual(
            migrated["unknown"].submission_dispatch_started_at,
            migrated["unknown"].submission_started_at,
        )
        self.assertIsNone(migrated["not_started"].submission_attempt_token)
        self.assertIsNone(migrated["confirmed"].submission_attempt_token)
        self.assertIsNone(migrated["manual_review"].submission_attempt_token)

    def test_backfill_stops_if_uncertain_attempt_lacks_fingerprint(self):
        document = self._document("unknown", 1)

        with self.assertRaisesMessage(RuntimeError, "lack a verifiable submission_fingerprint"):
            self._migrate_forward()

        self.Document.objects.filter(pk=document.pk).update(submission_fingerprint="c" * 64)
        Document = self._migrate_forward()
        self.assertIsNotNone(Document.objects.get(pk=document.pk).submission_attempt_token)

    def test_constraints_reject_invalid_active_transport_states(self):
        base = self._document("not_started", 1)
        Document = self._migrate_forward()
        document = Document.objects.get(pk=base.pk)

        invalid_updates = (
            {"submission_attempt_token": uuid.uuid4()},
            {"submission_outcome": "claimed"},
            {
                "submission_outcome": "in_flight",
                "submission_attempt_token": None,
                "submission_fingerprint": "d" * 64,
                "submission_started_at": timezone.now(),
                "submission_dispatch_started_at": timezone.now(),
            },
            {
                "submission_outcome": "unknown",
                "submission_attempt_token": None,
                "submission_fingerprint": "e" * 64,
                "submission_started_at": timezone.now(),
                "submission_dispatch_started_at": timezone.now(),
            },
        )
        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises((IntegrityError, TypeError, ValueError)):
                with transaction.atomic():
                    Document.objects.filter(pk=document.pk).update(**updates)
