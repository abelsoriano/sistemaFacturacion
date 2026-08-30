import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
from lxml import etree

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from facturacion.api.views.dgii_certification import DGIICertificationPlanViewSet
from facturacion.models import Company, CompanyMembership, DGIICertificationDocument, DGIICertificationEvent, DGIICertificationItem, DGIICertificationPlan
from facturacion.services.certification_locking import CertificationMutationBlocked
from facturacion.services.dgii_certification import (
    CertificationDocumentImmutableError,
    CertificationGenerationAttemptFailed,
    DGIICertificationDocumentGenerator,
    DGIICertificationDataTestsRunner,
    DGIICertificationRFCERebuilder,
)


class TestBuilder:
    def __init__(self, *, fail=False, barrier=None, marker="generated"):
        self.fail = fail
        self.barrier = barrier
        self.marker = marker
        self.calls = 0
        self._lock = threading.Lock()

    def build(self, payload):
        with self._lock:
            self.calls += 1
            call = self.calls
        if self.barrier and call <= 2:
            self.barrier.wait(timeout=5)
        if self.fail:
            raise ValueError("controlled generation failure")
        root = etree.Element("ECF")
        etree.SubElement(root, "Version").text = f"{self.marker}-{call}"
        return root


class TestBuilderFactory:
    def __init__(self, builder):
        self.builder = builder

    def get(self, ecf_type):
        return self.builder


class CertificationGenerationLockingTests(TransactionTestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Generación", rnc="101000001")
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company, source_filename="generation.xlsx", file_sha256="7" * 64,
        )

    def _item(self, encf="E310000000001", *, row=None):
        return DGIICertificationItem.objects.create(
            plan=self.plan, company=self.company, ecf_type=encf[1:3], dgii_group=1,
            encf=encf, source_sheet="ECF", source_row=row or self.plan.items.count() + 1,
        )

    def _document(self, item, *, status="generated", outcome="not_started", xml="<old/>"):
        submission_fields = {}
        if outcome == "in_flight":
            submission_fields = {
                "submission_started_at": timezone.now(),
                "submission_fingerprint": "f" * 64,
            }
        return DGIICertificationDocument.objects.create(
            plan=self.plan, company=self.company, item=item, ecf_type=item.ecf_type,
            encf=item.encf, status=status, submission_outcome=outcome,
            xml_content=xml, xml_hash=hashlib.sha256(xml.encode()).hexdigest() if xml else "",
            generated_at=timezone.now() if xml else None,
            **submission_fields,
        )

    def _generator(self, builder):
        generator = DGIICertificationDocumentGenerator(builder_factory=TestBuilderFactory(builder))
        generator._resolve_issuer = lambda company: object()
        generator._build_payload = lambda **kwargs: object()
        return generator

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    def test_initial_generation_is_atomic_and_publishes_hash_and_event(self):
        item = self._item()
        document = self._generator(TestBuilder()).generate_item(item=item)
        item.refresh_from_db()
        self.assertEqual(document.status, "generated")
        self.assertEqual(document.xml_hash, hashlib.sha256(document.xml_content.encode()).hexdigest())
        self.assertEqual(item.status, "generated")
        self.assertTrue(self.plan.events.filter(item=item, event_type="xml_generated").exists())

    def test_initial_controlled_failure_recreates_empty_error_document(self):
        item = self._item()
        document = self._generator(TestBuilder(fail=True)).generate_item(item=item)
        item.refresh_from_db()
        self.assertEqual(document.status, "generation_error")
        self.assertEqual(document.xml_content, "")
        self.assertEqual(document.xml_hash, "")
        self.assertEqual(item.status, "generation_error")
        self.assertTrue(self.plan.events.filter(item=item, event_type="xml_generation_error").exists())

    def test_mutable_regeneration_publishes_a_new_version(self):
        item = self._item()
        document = self._document(item)
        old_hash = document.xml_hash
        result = self._generator(TestBuilder()).generate_item(item=item)
        self.assertNotEqual(result.xml_hash, old_hash)
        self.assertEqual(result.status, "generated")

    def test_failed_regeneration_preserves_previous_version_and_raises(self):
        item = self._item()
        document = self._document(item)
        before = (document.xml_content, document.xml_hash, document.generated_at, document.status, item.status)
        with self.assertRaises(CertificationGenerationAttemptFailed):
            self._generator(TestBuilder(fail=True)).generate_item(item=item)
        document.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(
            (document.xml_content, document.xml_hash, document.generated_at, document.status, item.status),
            before,
        )
        self.assertTrue(self.plan.events.filter(item=item, payload__stage="certification_document_regeneration_failed").exists())

    def test_signed_not_started_is_immutable_before_builder(self):
        item = self._item()
        document = self._document(item, status="signed")
        builder = TestBuilder()
        with self.assertRaises(CertificationDocumentImmutableError):
            self._generator(builder).generate_item(item=item)
        document.refresh_from_db()
        self.assertEqual(builder.calls, 0)
        self.assertEqual(document.status, "signed")

    def test_signing_error_without_signed_artifact_can_regenerate(self):
        item = self._item()
        document = self._document(item, status="signing_error")
        document.signing_error = "certificate failure"
        document.save(update_fields=["signing_error", "updated_at"])
        result = self._generator(TestBuilder()).generate_item(item=item)
        self.assertEqual(result.status, "generated")
        self.assertEqual(result.signing_error, "")

    def test_signing_error_failed_regeneration_preserves_previous_xml(self):
        item = self._item()
        document = self._document(item, status="signing_error")
        before = (document.xml_content, document.xml_hash, document.generated_at, document.status)
        with self.assertRaises(CertificationGenerationAttemptFailed):
            self._generator(TestBuilder(fail=True)).generate_item(item=item)
        document.refresh_from_db()
        self.assertEqual((document.xml_content, document.xml_hash, document.generated_at, document.status), before)

    def test_each_signed_artifact_field_blocks_signing_error(self):
        for index, field in enumerate(("signed_xml_path", "signed_xml_hash", "signed_at"), start=1):
            with self.subTest(field=field):
                item = self._item(f"E31{index:010d}")
                document = self._document(item, status="signing_error")
                value = timezone.now() if field == "signed_at" else "evidence"
                setattr(document, field, value)
                document.save(update_fields=[field, "updated_at"])
                builder = TestBuilder()
                with self.assertRaises(CertificationDocumentImmutableError):
                    self._generator(builder).generate_item(item=item)
                self.assertEqual(builder.calls, 0)

    def test_blocking_outcomes_preserve_all_evidence(self):
        for index, outcome in enumerate(("in_flight", "unknown", "confirmed", "manual_review"), start=1):
            with self.subTest(outcome=outcome):
                item = self._item(f"E31{index + 10:010d}")
                document = self._document(item, outcome=outcome)
                document.submission_fingerprint = f"{index}" * 64
                document.dgii_track_id = f"TRACK-{index}"
                document.save(update_fields=["submission_fingerprint", "dgii_track_id", "updated_at"])
                before = (document.xml_content, document.xml_hash, document.submission_fingerprint, document.dgii_track_id)
                builder = TestBuilder()
                with self.assertRaises(CertificationMutationBlocked):
                    self._generator(builder).generate_item(item=item)
                document.refresh_from_db()
                self.assertEqual((document.xml_content, document.xml_hash, document.submission_fingerprint, document.dgii_track_id), before)
                self.assertEqual(builder.calls, 0)

    def test_remote_delivery_evidence_blocks_but_local_diagnostics_do_not(self):
        item = self._item()
        document = self._document(item)
        generator = self._generator(TestBuilder())
        document.dgii_response = {"stage": "local_xsd_preflight", "error": "local"}
        document.dgii_response_message = "local validation"
        document.save(update_fields=["dgii_response", "dgii_response_message", "updated_at"])
        self.assertFalse(generator.has_dgii_delivery_evidence(document))
        document.dgii_track_id = "TRACK-REMOTE"
        self.assertTrue(generator.has_dgii_delivery_evidence(document))

    def test_dgii_timestamp_evidence_blocks_inconsistent_generated_document(self):
        item = self._item()
        document = self._document(item)
        document.submitted_at = timezone.now()
        document.save(update_fields=["submitted_at", "updated_at"])
        with self.assertRaises(CertificationDocumentImmutableError):
            self._generator(TestBuilder()).generate_item(item=item)

    def test_two_initial_generations_create_only_one_document(self):
        item = self._item()
        barrier = threading.Barrier(2)
        builder = TestBuilder()

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return self._generator(builder).generate_item(item=item).pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = [future.result(timeout=15) for future in (pool.submit(worker), pool.submit(worker))]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(DGIICertificationDocument.objects.filter(item=item).count(), 1)

    def test_two_mutable_regenerations_are_serialized(self):
        item = self._item()
        self._document(item)
        barrier = threading.Barrier(2)
        builder = TestBuilder()

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return self._generator(builder).generate_item(item=item).xml_hash
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            hashes = [future.result(timeout=15) for future in (pool.submit(worker), pool.submit(worker))]
        self.assertEqual(builder.calls, 2)
        self.assertNotEqual(hashes[0], hashes[1])

    def test_two_concurrent_attempts_reject_each_blocking_outcome(self):
        for index, outcome in enumerate(("in_flight", "unknown", "confirmed", "manual_review"), start=1):
            with self.subTest(outcome=outcome):
                item = self._item(f"E32{index:010d}")
                document = self._document(item, outcome=outcome)
                before = (document.xml_content, document.xml_hash, document.submission_fingerprint)
                barrier = threading.Barrier(2)
                builder = TestBuilder()

                def worker():
                    close_old_connections()
                    try:
                        barrier.wait(timeout=5)
                        with self.assertRaises(CertificationMutationBlocked):
                            self._generator(builder).generate_item(item=item)
                    finally:
                        close_old_connections()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = (pool.submit(worker), pool.submit(worker))
                    for future in futures:
                        future.result(timeout=15)
                document.refresh_from_db()
                self.assertEqual(
                    (document.xml_content, document.xml_hash, document.submission_fingerprint),
                    before,
                )
                self.assertEqual(builder.calls, 0)

    def test_two_concurrent_attempts_reject_signed_not_started(self):
        item = self._item()
        document = self._document(item, status="signed")
        before = (document.xml_content, document.xml_hash, document.submission_fingerprint)
        barrier = threading.Barrier(2)
        builder = TestBuilder()

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                with self.assertRaises(CertificationDocumentImmutableError):
                    self._generator(builder).generate_item(item=item)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = (pool.submit(worker), pool.submit(worker))
            for future in futures:
                future.result(timeout=15)
        document.refresh_from_db()
        self.assertEqual(
            (document.xml_content, document.xml_hash, document.submission_fingerprint),
            before,
        )
        self.assertEqual(builder.calls, 0)

    def test_group_success_uses_one_scope_and_generates_all_items(self):
        self._item("E310000000001", row=1)
        self._item("E310000000002", row=2)
        generator = self._generator(TestBuilder())
        with patch.object(
            generator.lock_service,
            "lock_scope",
            wraps=generator.lock_service.lock_scope,
        ) as lock_scope:
            summary = generator.generate_group(plan=self.plan, group_number=1)
        self.assertEqual(summary, {"generated": 2, "failed": 0, "errors": []})
        self.assertEqual(lock_scope.call_count, 1)
        self.assertEqual(DGIICertificationDocument.objects.filter(plan=self.plan).count(), 2)

    def test_group_failure_rolls_back_all_publications_and_success_events(self):
        first = self._item("E310000000001", row=1)
        second = self._item("E310000000002", row=2)

        class FailSecondBuilder(TestBuilder):
            def build(inner_self, payload):
                if inner_self.calls == 1:
                    inner_self.fail = True
                return super(FailSecondBuilder, inner_self).build(payload)

        summary = self._generator(FailSecondBuilder()).generate_group(plan=self.plan, group_number=1)
        self.assertEqual(summary["generated"], 0)
        self.assertEqual(summary["failed"], 1)
        self.assertTrue(summary["errors"][0]["rolled_back"])
        self.assertFalse(self.plan.events.filter(event_type="xml_generated").exists())
        self.assertFalse(DGIICertificationDocument.objects.filter(item=first).exists())
        self.assertEqual(DGIICertificationDocument.objects.get(item=second).status, "generation_error")

    def test_event_failure_rolls_back_document_publication(self):
        item = self._item()
        with patch.object(DGIICertificationEvent.objects, "create", side_effect=RuntimeError("event failure")):
            with self.assertRaises(RuntimeError):
                self._generator(TestBuilder()).generate_item(item=item)
        self.assertFalse(DGIICertificationDocument.objects.filter(item=item).exists())

    def test_endpoint_returns_409_for_signed_document(self):
        user = get_user_model().objects.create_superuser("generation-admin", "g@example.com", "pass")
        CompanyMembership.objects.create(
            user=user, company=self.company, role=CompanyMembership.ROLE_OWNER,
        )
        item = self._item()
        self._document(item, status="signed")
        request = APIRequestFactory().post(
            f"/ecf/certification-plans/{self.plan.pk}/items/{item.pk}/generate-document/"
        )
        request.session = {"active_company_id": self.company.pk}
        force_authenticate(request, user=user)
        with patch.object(DGIICertificationPlanViewSet, "_manager_permission_response", return_value=None):
            response = DGIICertificationPlanViewSet.as_view({"post": "generate_item_document"})(
                request, pk=self.plan.pk, item_id=item.pk,
            )
        self.assertEqual(response.status_code, 409)

    def test_endpoint_preserves_initial_generation_error_400_contract(self):
        user = get_user_model().objects.create_superuser("initial-error-admin", "i@example.com", "pass")
        CompanyMembership.objects.create(
            user=user, company=self.company, role=CompanyMembership.ROLE_OWNER,
        )
        item = self._item()
        document = self._document(item, status="generation_error", xml="")
        document.generation_error = "controlled generation failure"
        document.save(update_fields=["generation_error", "updated_at"])
        item.status = "generation_error"
        item.generation_error = document.generation_error
        item.save(update_fields=["status", "generation_error", "updated_at"])
        request = APIRequestFactory().post(
            f"/ecf/certification-plans/{self.plan.pk}/items/{item.pk}/generate-document/"
        )
        force_authenticate(request, user=user)
        fake_generator = SimpleNamespace(generate_item=lambda **kwargs: document)
        with patch.object(DGIICertificationPlanViewSet, "_manager_permission_response", return_value=None), patch(
            "facturacion.api.views.dgii_certification.DGIICertificationDocumentGenerator",
            return_value=fake_generator,
        ):
            response = DGIICertificationPlanViewSet.as_view({"post": "generate_item_document"})(
                request, pk=self.plan.pk, item_id=item.pk,
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["certification_document"]["generation_error"], document.generation_error)

    def test_endpoint_converts_failed_regeneration_to_detail_400(self):
        user = get_user_model().objects.create_superuser("regen-error-admin", "r@example.com", "pass")
        CompanyMembership.objects.create(
            user=user, company=self.company, role=CompanyMembership.ROLE_OWNER,
        )
        item = self._item()
        self._document(item)
        request = APIRequestFactory().post(
            f"/ecf/certification-plans/{self.plan.pk}/items/{item.pk}/generate-document/"
        )
        force_authenticate(request, user=user)
        fake_generator = SimpleNamespace(
            generate_item=lambda **kwargs: (_ for _ in ()).throw(
                CertificationGenerationAttemptFailed("controlled regeneration failure")
            )
        )
        with patch.object(DGIICertificationPlanViewSet, "_manager_permission_response", return_value=None), patch(
            "facturacion.api.views.dgii_certification.DGIICertificationDocumentGenerator",
            return_value=fake_generator,
        ):
            response = DGIICertificationPlanViewSet.as_view({"post": "generate_item_document"})(
                request, pk=self.plan.pk, item_id=item.pk,
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "controlled regeneration failure"})

    def test_rfce_rebuilder_stops_after_failed_generation_summary(self):
        item = self._item()
        item.dgii_group = 4
        item.save(update_fields=["dgii_group", "updated_at"])
        generator = SimpleNamespace(
            document_fence=DGIICertificationDocumentGenerator.document_fence,
            prepare_item=lambda **kwargs: (_ for _ in ()).throw(ValueError("controlled generation failure")),
        )
        signer = SimpleNamespace(prepare_document=lambda **kwargs: self.fail("signer must not run"))
        result = DGIICertificationRFCERebuilder(generator=generator, signer=signer).rebuild(
            plan=self.plan,
        )
        self.assertTrue(result["failed"])
        self.assertEqual(result["signed_integral"]["signed"], 0)

    def test_data_runner_stops_before_signing_and_submission_on_generation_failure(self):
        generator = SimpleNamespace(generate_group=lambda **kwargs: {
            "generated": 0, "failed": 1, "errors": [{"rolled_back": True}],
        })
        signer = SimpleNamespace(sign_group=lambda **kwargs: self.fail("signer must not run"))
        submitter = SimpleNamespace(submit_data_ecf=lambda **kwargs: self.fail("submitter must not run"))
        rfce_rebuilder = SimpleNamespace(rebuild=lambda **kwargs: self.fail("RFCE must not run"))
        result = DGIICertificationDataTestsRunner(
            generator=generator,
            signer=signer,
            submitter=submitter,
            rfce_rebuilder=rfce_rebuilder,
        ).run(plan=self.plan)
        self.assertTrue(result["failed"])
        self.assertIn("error generando", result["message"])
