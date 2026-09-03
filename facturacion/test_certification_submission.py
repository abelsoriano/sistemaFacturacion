import hashlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from facturacion.models import Company, DGIICertificationDocument, DGIICertificationItem, DGIICertificationPlan
from facturacion.ecf.services.dgii_submission import DGIISubmissionService
from facturacion.ecf.utils.fingerprint import submission_fingerprint
from facturacion.services.certification_submission import (
    CertificationRemoteSubmissionResponse,
    CertificationSubmissionBlocked,
    CertificationSubmissionFencingConflict,
    CertificationSubmissionService,
    CertificationSubmissionUnknown,
)


class CountingRemoteSubmitter:
    def __init__(self, *, error=None):
        self.calls = 0
        self.error = error
        self.lock = threading.Lock()

    def __call__(self, prepared):
        with self.lock:
            self.calls += 1
        if self.error:
            raise self.error
        return CertificationRemoteSubmissionResponse(
            track_id=f"TRACK-{prepared.document_id}",
            raw={"track_id": f"TRACK-{prepared.document_id}"},
        )


class CertificationSubmissionServiceTests(TransactionTestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Submit", rnc="101000001")
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company,
            source_filename="submit.xlsx",
            file_sha256="6" * 64,
        )
        self.paths = []

    def tearDown(self):
        for path in self.paths:
            if default_storage.exists(path):
                default_storage.delete(path)

    def _create_document(self, encf, *, modified_encf="", status="signed", with_document=True):
        item = DGIICertificationItem.objects.create(
            plan=self.plan,
            company=self.company,
            ecf_type=encf[1:3],
            dgii_group=2 if modified_encf else 1,
            encf=encf,
            source_sheet="ECF",
            source_row=self.plan.items.count() + 1,
            raw_data={"NCFModificado": "WRONG-RAW-DATA"},
        )
        if not with_document:
            return item, None
        reference = (
            f"<InformacionReferencia><NCFModificado>{modified_encf}</NCFModificado>"
            "<FechaNCFModificado>01-01-2020</FechaNCFModificado>"
            "<CodigoModificacion>1</CodigoModificacion></InformacionReferencia>"
            if modified_encf else ""
        )
        xml = f"<ECF><Encabezado><Emisor><RNCEmisor>{self.company.rnc}</RNCEmisor>" \
              f"<eNCF>{encf}</eNCF></Emisor></Encabezado>{reference}</ECF>"
        path = default_storage.save(
            f"tests/certification-submission/{self.plan.pk}-{encf}-{item.pk}.xml",
            ContentFile(xml.encode()),
        )
        self.paths.append(path)
        document = DGIICertificationDocument.objects.create(
            plan=self.plan,
            company=self.company,
            item=item,
            ecf_type=item.ecf_type,
            encf=encf,
            status=status,
            signed_xml_path=path,
            signed_xml_hash=hashlib.sha256(xml.encode()).hexdigest(),
        )
        return item, document

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    def test_productive_service_uses_the_shared_fingerprint_algorithm(self):
        document = SimpleNamespace(
            issuer=SimpleNamespace(rnc="101-00000-1"),
            encf="E310000000001",
            signed_xml_content="<ECF>firmado</ECF>",
        )
        expected = submission_fingerprint(
            issuer_rnc=document.issuer.rnc,
            encf=document.encf,
            signed_xml=document.signed_xml_content,
        )
        self.assertEqual(DGIISubmissionService()._submission_fingerprint(document), expected)

    def test_successful_submission_without_dependency_is_confirmed(self):
        _item, document = self._create_document("E310000000001")
        remote = CountingRemoteSubmitter()

        result = CertificationSubmissionService(remote_submitter=remote).submit(
            plan_id=self.plan.pk, document_id=document.pk
        )

        self.assertEqual(remote.calls, 1)
        self.assertEqual(result.submission_outcome, "confirmed")
        self.assertEqual(result.dgii_track_id, f"TRACK-{document.pk}")
        self.assertIsNotNone(result.submission_attempt_token)
        self.assertIsNotNone(result.submission_dispatch_started_at)

    def test_internal_dependency_with_accepted_original_is_submitted(self):
        _item, original = self._create_document("E310000000001", status="accepted")
        _item, dependent = self._create_document("E340000000002", modified_encf=original.encf)
        remote = CountingRemoteSubmitter()

        result = CertificationSubmissionService(remote_submitter=remote).submit(
            plan_id=self.plan.pk, document_id=dependent.pk
        )

        self.assertEqual(remote.calls, 1)
        self.assertEqual(result.submission_outcome, "confirmed")

    def test_internal_dependency_without_accepted_original_does_not_post(self):
        _item, original = self._create_document("E310000000001")
        _item, dependent = self._create_document("E340000000002", modified_encf=original.encf)
        remote = CountingRemoteSubmitter()

        with self.assertRaises(CertificationSubmissionBlocked):
            CertificationSubmissionService(remote_submitter=remote).submit(
                plan_id=self.plan.pk, document_id=dependent.pk
            )
        self.assertEqual(remote.calls, 0)

    def test_missing_internal_does_not_post(self):
        self._create_document("E310000000001", with_document=False)
        _item, dependent = self._create_document("E340000000002", modified_encf="E310000000001")
        remote = CountingRemoteSubmitter()

        with self.assertRaises(CertificationSubmissionBlocked):
            CertificationSubmissionService(remote_submitter=remote).submit(
                plan_id=self.plan.pk, document_id=dependent.pk
            )
        self.assertEqual(remote.calls, 0)

    def test_ambiguous_duplicate_does_not_post(self):
        self._create_document("E310000000001")
        self._create_document("E310000000001")
        _item, dependent = self._create_document("E340000000002", modified_encf="E310000000001")
        remote = CountingRemoteSubmitter()

        with self.assertRaises(CertificationSubmissionBlocked):
            CertificationSubmissionService(remote_submitter=remote).submit(
                plan_id=self.plan.pk, document_id=dependent.pk
            )
        self.assertEqual(remote.calls, 0)

    def test_remote_timeout_marks_outcome_unknown(self):
        _item, document = self._create_document("E310000000001")
        remote = CountingRemoteSubmitter(error=TimeoutError("timeout"))

        with self.assertRaises(CertificationSubmissionUnknown):
            CertificationSubmissionService(remote_submitter=remote).submit(
                plan_id=self.plan.pk, document_id=document.pk
            )

        document.refresh_from_db()
        self.assertEqual(remote.calls, 1)
        self.assertEqual(document.submission_outcome, "unknown")
        self.assertTrue(document.submission_fingerprint)
        self.assertIn("timeout", document.last_error)

    def test_two_concurrent_attempts_only_one_posts(self):
        _item, document = self._create_document("E310000000001")
        remote = CountingRemoteSubmitter()
        barrier = threading.Barrier(2)

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    return CertificationSubmissionService(remote_submitter=remote).submit(
                        plan_id=self.plan.pk, document_id=document.pk
                    ).submission_outcome
                except CertificationSubmissionBlocked:
                    return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=15) for future in (pool.submit(worker), pool.submit(worker))]

        self.assertEqual(remote.calls, 1)
        self.assertEqual(sorted(results), ["blocked", "confirmed"])

    def test_fingerprint_mismatch_records_conflict_without_overwrite(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService(remote_submitter=CountingRemoteSubmitter())
        snapshots = service._snapshot_plan(self.plan.pk)
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk, document_id=document.pk, snapshots=snapshots
        )

        document.refresh_from_db()
        self.assertEqual(document.submission_outcome, "claimed")
        self.assertEqual(document.submission_attempt_token, prepared.attempt_token)
        self.assertIsNone(document.submission_dispatch_started_at)
        service.mark_in_flight(prepared)

        with self.assertRaises(CertificationSubmissionFencingConflict):
            service.persist_submission_response(
                document.pk,
                "different-fingerprint",
                prepared.attempt_token,
                CertificationRemoteSubmissionResponse(track_id="ORPHAN-TRACK"),
                None,
            )

        document.refresh_from_db()
        self.assertEqual(document.submission_outcome, "in_flight")
        self.assertEqual(document.submission_fingerprint, prepared.fingerprint)
        self.assertEqual(document.dgii_track_id, "")
        self.assertTrue(
            self.plan.events.filter(item=document.item, payload__stage="persist_response").exists()
        )

    def test_claim_generates_unique_token_without_dispatch(self):
        _item, first = self._create_document("E310000000001")
        _item, second = self._create_document("E320000000002")
        service = CertificationSubmissionService()

        first_prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=first.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        first.refresh_from_db()
        self.assertEqual(first.submission_outcome, "claimed")
        self.assertEqual(first.submission_attempt_token, first_prepared.attempt_token)
        self.assertIsNone(first.submission_dispatch_started_at)

        service.recover_abandoned_claim(
            document_id=first.pk,
            attempt_token=first_prepared.attempt_token,
            now=first.submission_started_at + service.claim_timeout + timedelta(seconds=1),
        )
        second_prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=second.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        self.assertNotEqual(first_prepared.attempt_token, second_prepared.attempt_token)

    def test_claimed_to_in_flight_is_fenced_by_token_and_fingerprint(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )

        wrong_token = type(prepared)(
            prepared.document_id,
            prepared.fingerprint,
            uuid.uuid4(),
            prepared.snapshot,
        )
        with self.assertRaises(CertificationSubmissionFencingConflict):
            service.mark_in_flight(wrong_token)

        service.mark_in_flight(prepared)
        document.refresh_from_db()
        self.assertEqual(document.submission_outcome, "in_flight")
        self.assertIsNotNone(document.submission_dispatch_started_at)

    def test_dispatch_is_committed_before_remote_client_runs(self):
        _item, document = self._create_document("E310000000001")

        def assert_committed(prepared):
            close_old_connections()
            persisted = DGIICertificationDocument.objects.get(pk=prepared.document_id)
            self.assertEqual(persisted.submission_outcome, "in_flight")
            self.assertEqual(persisted.submission_attempt_token, prepared.attempt_token)
            self.assertIsNotNone(persisted.submission_dispatch_started_at)
            return CertificationRemoteSubmissionResponse(track_id="TRACK-COMMITTED")

        result = CertificationSubmissionService(remote_submitter=assert_committed).submit(
            plan_id=self.plan.pk,
            document_id=document.pk,
        )
        self.assertEqual(result.dgii_track_id, "TRACK-COMMITTED")

    def test_expired_claim_without_dispatch_is_recoverable(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        document.refresh_from_db()

        recovered = service.recover_abandoned_claim(
            document_id=document.pk,
            attempt_token=prepared.attempt_token,
            now=document.submission_started_at + service.claim_timeout + timedelta(seconds=1),
        )

        self.assertTrue(recovered)
        document.refresh_from_db()
        self.assertEqual(document.submission_outcome, "not_started")
        self.assertIsNone(document.submission_attempt_token)
        self.assertEqual(document.submission_fingerprint, "")

    def test_old_token_cannot_recover_or_dispatch_new_claim(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        first = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        document.refresh_from_db()
        service.recover_abandoned_claim(
            document_id=document.pk,
            attempt_token=first.attempt_token,
            now=document.submission_started_at + service.claim_timeout + timedelta(seconds=1),
        )
        second = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )

        self.assertFalse(service.recover_abandoned_claim(
            document_id=document.pk,
            attempt_token=first.attempt_token,
            now=timezone.now() + service.claim_timeout + timedelta(seconds=1),
        ))
        with self.assertRaises(CertificationSubmissionFencingConflict):
            service.mark_in_flight(first)
        service.mark_in_flight(second)

    def test_in_flight_is_never_recovered_for_resend(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        service.mark_in_flight(prepared)
        self.assertFalse(service.recover_abandoned_claim(
            document_id=document.pk,
            attempt_token=prepared.attempt_token,
            now=timezone.now() + service.claim_timeout + timedelta(seconds=1),
        ))

    def test_claim_with_dgii_evidence_is_not_recovered(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        document.refresh_from_db()
        document.dgii_response = {"unexpected": True}
        document.save(update_fields=["dgii_response", "updated_at"])

        with self.assertRaises(CertificationSubmissionBlocked):
            service.recover_abandoned_claim(
                document_id=document.pk,
                attempt_token=prepared.attempt_token,
                now=document.submission_started_at + service.claim_timeout + timedelta(seconds=1),
            )
        document.refresh_from_db()
        self.assertEqual(document.submission_outcome, "claimed")

    def test_correct_fingerprint_with_old_token_cannot_persist_response(self):
        _item, document = self._create_document("E310000000001")
        service = CertificationSubmissionService()
        prepared = service.prepare_certification_submission(
            plan_id=self.plan.pk,
            document_id=document.pk,
            snapshots=service._snapshot_plan(self.plan.pk),
        )
        service.mark_in_flight(prepared)

        with self.assertRaises(CertificationSubmissionFencingConflict):
            service.persist_submission_response(
                document.pk,
                prepared.fingerprint,
                uuid.uuid4(),
                CertificationRemoteSubmissionResponse(track_id="ORPHAN"),
                None,
            )
        document.refresh_from_db()
        self.assertEqual(document.dgii_track_id, "")

    def test_stale_snapshot_of_non_candidate_invalidates_whole_preflight(self):
        _item, candidate = self._create_document("E310000000001")
        _item, other = self._create_document("E320000000002")
        remote = CountingRemoteSubmitter()
        service = CertificationSubmissionService(remote_submitter=remote)
        snapshots = service._snapshot_plan(self.plan.pk)
        other.signed_xml_hash = "0" * 64
        other.save(update_fields=["signed_xml_hash", "updated_at"])

        with self.assertRaises(CertificationSubmissionBlocked):
            service.prepare_certification_submission(
                plan_id=self.plan.pk,
                document_id=candidate.pk,
                snapshots=snapshots,
            )
        self.assertEqual(remote.calls, 0)

    def test_missing_non_candidate_snapshot_invalidates_without_raw_data_fallback(self):
        _item, candidate = self._create_document("E310000000001")
        _item, other = self._create_document("E320000000002")
        service = CertificationSubmissionService(remote_submitter=CountingRemoteSubmitter())
        snapshots = service._snapshot_plan(self.plan.pk)
        snapshots.pop(other.pk)

        with self.assertRaises(CertificationSubmissionBlocked) as raised:
            service.prepare_certification_submission(
                plan_id=self.plan.pk,
                document_id=candidate.pk,
                snapshots=snapshots,
            )
        self.assertIn("artifact_missing", str(raised.exception))
