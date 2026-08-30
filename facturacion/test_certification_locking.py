from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from facturacion.models import (
    Company,
    DGIICertificationDocument,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_locking import (
    CertificationDocumentNotFound,
    CertificationItemNotFound,
    CertificationLockProtocolError,
    CertificationLockScopeIncomplete,
    CertificationLockService,
    CertificationTenantMismatch,
)


class CertificationLockServiceTests(TransactionTestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Locks", rnc="101000001")
        self.plan = self._create_plan(self.company, "plan-locks.xlsx", "1" * 64)
        self.item_a, self.document_a = self._create_item_document(self.plan, 1, "E310000000001")
        self.item_b, self.document_b = self._create_item_document(self.plan, 2, "E320000000001")
        self.service = CertificationLockService()

    @staticmethod
    def _create_plan(company, filename, digest):
        return DGIICertificationPlan.objects.create(
            company=company,
            source_filename=filename,
            file_sha256=digest,
        )

    @staticmethod
    def _create_item_document(plan, row, encf):
        item = DGIICertificationItem.objects.create(
            plan=plan,
            company=plan.company,
            ecf_type=encf[1:3],
            dgii_group=1,
            encf=encf,
            source_sheet="ECF",
            source_row=row,
        )
        document = DGIICertificationDocument.objects.create(
            plan=plan,
            company=plan.company,
            item=item,
            ecf_type=item.ecf_type,
            encf=encf,
        )
        return item, document

    def test_lock_scope_requires_atomic_transaction(self):
        with self.assertRaises(CertificationLockProtocolError):
            self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[self.item_a.pk],
                document_ids=[self.document_a.pk],
            )

    def test_lock_suite_requires_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    @skipUnlessDBFeature("has_select_for_update")
    def test_lock_scope_queries_plan_then_items_then_documents_in_ascending_order(self):
        with CaptureQueriesContext(connection) as queries:
            with transaction.atomic():
                scope = self.service.lock_scope(
                    plan_id=self.plan.pk,
                    item_ids=[self.item_b.pk, self.item_a.pk, self.item_b.pk],
                    document_ids=[self.document_b.pk, self.document_a.pk],
                )

        lock_queries = [query["sql"] for query in queries if "FOR UPDATE" in query["sql"].upper()]
        self.assertEqual(len(lock_queries), 3)
        self.assertIn('"facturacion_dgiicertificationplan"', lock_queries[0])
        self.assertIn('"facturacion_dgiicertificationitem"', lock_queries[1])
        self.assertIn('ORDER BY "facturacion_dgiicertificationitem"."id" ASC', lock_queries[1])
        self.assertIn('"facturacion_dgiicertificationdocument"', lock_queries[2])
        self.assertIn('ORDER BY "facturacion_dgiicertificationdocument"."id" ASC', lock_queries[2])
        self.assertEqual(list(scope.items_by_id), [self.item_a.pk, self.item_b.pk])
        self.assertEqual(list(scope.documents_by_id), [self.document_a.pk, self.document_b.pk])

    def test_scope_helpers_and_mappings_are_immutable(self):
        with transaction.atomic():
            scope = self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[self.item_a.pk],
                document_ids=[self.document_a.pk],
            )
            self.assertEqual(scope.item(self.item_a.pk).pk, self.item_a.pk)
            self.assertEqual(scope.document(self.document_a.pk).pk, self.document_a.pk)
            self.assertEqual(scope.document_for_item(self.item_a.pk).pk, self.document_a.pk)
            scope.assert_complete(
                item_ids=[self.item_a.pk],
                document_ids=[self.document_a.pk],
            )
            with self.assertRaises(CertificationLockScopeIncomplete):
                scope.assert_complete(
                    item_ids=[self.item_a.pk, self.item_b.pk],
                    document_ids=[self.document_a.pk],
                )
            with self.assertRaises(TypeError):
                scope.items_by_id[self.item_b.pk] = self.item_b

    def test_missing_item_is_not_silently_ignored(self):
        with transaction.atomic(), self.assertRaises(CertificationItemNotFound):
            self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[999999],
                document_ids=[],
            )

    def test_missing_document_is_not_silently_ignored(self):
        with transaction.atomic(), self.assertRaises(CertificationDocumentNotFound):
            self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[],
                document_ids=[999999],
            )

    def test_item_from_another_plan_is_rejected_as_tenant_mismatch(self):
        other_company = Company.objects.create(name="Otra Empresa", rnc="101000002")
        other_plan = self._create_plan(other_company, "other.xlsx", "2" * 64)
        other_item, _document = self._create_item_document(other_plan, 1, "E310000000002")

        with transaction.atomic(), self.assertRaises(CertificationTenantMismatch):
            self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[other_item.pk],
                document_ids=[],
            )

    def test_document_requires_its_item_in_scope(self):
        with transaction.atomic(), self.assertRaises(CertificationLockScopeIncomplete):
            self.service.lock_scope(
                plan_id=self.plan.pk,
                item_ids=[],
                document_ids=[self.document_a.pk],
            )

    def test_scope_does_not_use_storage_or_remote_clients(self):
        with CaptureQueriesContext(connection) as queries:
            with transaction.atomic():
                self.service.lock_scope(
                    plan_id=self.plan.pk,
                    item_ids=[self.item_a.pk],
                    document_ids=[self.document_a.pk],
                )
        self.assertTrue(queries)
        self.assertTrue(all(query["sql"].lstrip().upper().startswith(("SELECT", "BEGIN", "COMMIT")) for query in queries))

    @skipUnlessDBFeature("has_select_for_update")
    def test_same_plan_scopes_serialize_and_lock_releases_at_commit(self):
        first_acquired = threading.Event()
        allow_first_commit = threading.Event()
        second_attempted = threading.Event()
        second_acquired = threading.Event()

        def first_worker():
            close_old_connections()
            try:
                with transaction.atomic():
                    CertificationLockService().lock_scope(
                        plan_id=self.plan.pk,
                        item_ids=[self.item_a.pk],
                        document_ids=[self.document_a.pk],
                    )
                    first_acquired.set()
                    allow_first_commit.wait(timeout=5)
            finally:
                close_old_connections()

        def second_worker():
            close_old_connections()
            try:
                first_acquired.wait(timeout=5)
                second_attempted.set()
                with transaction.atomic():
                    CertificationLockService().lock_scope(
                        plan_id=self.plan.pk,
                        item_ids=[self.item_b.pk],
                        document_ids=[self.document_b.pk],
                    )
                    second_acquired.set()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(first_worker)
            second_future = pool.submit(second_worker)
            self.assertTrue(first_acquired.wait(timeout=5))
            self.assertTrue(second_attempted.wait(timeout=5))
            time.sleep(0.2)
            self.assertFalse(second_acquired.is_set())
            allow_first_commit.set()
            first_future.result(timeout=5)
            second_future.result(timeout=5)

        self.assertTrue(second_acquired.is_set())

    @skipUnlessDBFeature("has_select_for_update")
    def test_inverse_input_order_has_no_cross_deadlock(self):
        barrier = threading.Barrier(2)

        def worker(item_ids, document_ids):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                with transaction.atomic():
                    scope = CertificationLockService().lock_scope(
                        plan_id=self.plan.pk,
                        item_ids=item_ids,
                        document_ids=document_ids,
                    )
                    return list(scope.items_by_id), list(scope.documents_by_id)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(
                worker,
                [self.item_a.pk, self.item_b.pk],
                [self.document_a.pk, self.document_b.pk],
            )
            second = pool.submit(
                worker,
                [self.item_b.pk, self.item_a.pk],
                [self.document_b.pk, self.document_a.pk],
            )
            results = [first.result(timeout=10), second.result(timeout=10)]

        expected = ([self.item_a.pk, self.item_b.pk], [self.document_a.pk, self.document_b.pk])
        self.assertEqual(results, [expected, expected])

    @skipUnlessDBFeature("has_select_for_update")
    def test_different_plans_can_hold_scopes_concurrently(self):
        other_plan = self._create_plan(self.company, "parallel.xlsx", "3" * 64)
        other_item, other_document = self._create_item_document(other_plan, 1, "E310000000003")
        both_acquired = threading.Barrier(2)

        def worker(plan_id, item_id, document_id):
            close_old_connections()
            try:
                with transaction.atomic():
                    CertificationLockService().lock_scope(
                        plan_id=plan_id,
                        item_ids=[item_id],
                        document_ids=[document_id],
                    )
                    both_acquired.wait(timeout=5)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(worker, self.plan.pk, self.item_a.pk, self.document_a.pk),
                pool.submit(worker, other_plan.pk, other_item.pk, other_document.pk),
            ]
            for future in futures:
                future.result(timeout=10)
