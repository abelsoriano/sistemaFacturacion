from django.db import connection, transaction
from django.test import TransactionTestCase

from facturacion.models import (
    Company,
    DGIICertificationDocument,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_dependency_graph import (
    CertificationDependencyGraphPreflight,
    CertificationDependencyIssueKind,
)
from facturacion.services.certification_locking import CertificationLockService


class CertificationDependencyGraphPreflightTests(TransactionTestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Grafo", rnc="101000001")
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company,
            source_filename="grafo.xlsx",
            file_sha256="5" * 64,
        )
        self.lock_service = CertificationLockService()
        self.preflight = CertificationDependencyGraphPreflight(lock_service=self.lock_service)

    def _create_document(self, encf, *, modified_encf="", source_row=None, with_document=True):
        row = source_row or self.plan.items.count() + 1
        raw_data = {"NCFModificado": modified_encf, "RNCOtroContribuyente": "#e"}
        item = DGIICertificationItem.objects.create(
            plan=self.plan,
            company=self.company,
            ecf_type=encf[1:3],
            dgii_group=2 if modified_encf else 1,
            encf=encf,
            source_sheet="ECF",
            source_row=row,
            raw_data=raw_data,
        )
        if not with_document:
            return item, None
        document = DGIICertificationDocument.objects.create(
            plan=self.plan,
            company=self.company,
            item=item,
            ecf_type=item.ecf_type,
            encf=encf,
        )
        return item, document

    def _validate(self):
        with transaction.atomic():
            locked_plan = self.lock_service.lock_plan(plan_id=self.plan.pk)
            return self.preflight.validate_locked_plan(locked_plan)

    def test_suite_runs_against_postgresql(self):
        self.assertEqual(connection.vendor, "postgresql")

    def test_three_real_dataset_references_form_valid_acyclic_graph(self):
        pairs = (
            ("E330000000001", "E320000000006"),
            ("E340000000002", "E310000000034"),
            ("E340000000018", "E460000000009"),
        )
        originals = {}
        dependents = {}
        for dependent_encf, original_encf in pairs:
            _item, originals[original_encf] = self._create_document(original_encf)
            _item, dependents[dependent_encf] = self._create_document(
                dependent_encf,
                modified_encf=original_encf,
            )

        result = self._validate()

        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, ())
        self.assertEqual(
            [(edge.dependent_document_id, edge.original_document_id) for edge in result.edges],
            sorted(
                (dependents[dependent].pk, originals[original].pk)
                for dependent, original in pairs
            ),
        )

    def test_chain_a_to_b_to_c_is_valid(self):
        _item, document_c = self._create_document("E310000000001")
        _item, document_b = self._create_document("E330000000002", modified_encf=document_c.encf)
        _item, document_a = self._create_document("E340000000003", modified_encf=document_b.encf)

        result = self._validate()

        self.assertTrue(result.is_valid)
        self.assertEqual(
            [(edge.dependent_document_id, edge.original_document_id) for edge in result.edges],
            [(document_b.pk, document_c.pk), (document_a.pk, document_b.pk)],
        )

    def test_cycle_a_to_b_to_c_to_a_invalidates_preflight(self):
        _item, document_a = self._create_document("E340000000001", modified_encf="E330000000002")
        _item, document_b = self._create_document("E330000000002", modified_encf="E310000000003")
        _item, document_c = self._create_document("E310000000003", modified_encf=document_a.encf)

        result = self._validate()

        self.assertFalse(result.is_valid)
        cycle_issues = [issue for issue in result.issues if issue.kind == CertificationDependencyIssueKind.CYCLE]
        self.assertEqual([issue.document_id for issue in cycle_issues], [document_a.pk, document_b.pk, document_c.pk])
        self.assertTrue(all(issue.related_document_ids == (document_a.pk, document_b.pk, document_c.pk) for issue in cycle_issues))

    def test_self_reference_is_reported_as_cycle(self):
        _item, document = self._create_document("E340000000001", modified_encf="E340000000001")

        result = self._validate()

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].kind, CertificationDependencyIssueKind.CYCLE)
        self.assertEqual(result.issues[0].reason, "self_reference")
        self.assertEqual(result.issues[0].related_document_ids, (document.pk,))

    def test_two_dependents_can_share_one_original(self):
        _item, original = self._create_document("E310000000001")
        _item, dependent_b = self._create_document("E330000000002", modified_encf=original.encf)
        _item, dependent_c = self._create_document("E340000000003", modified_encf=original.encf)

        result = self._validate()

        self.assertTrue(result.is_valid)
        self.assertEqual(
            [(edge.dependent_document_id, edge.original_document_id) for edge in result.edges],
            [(dependent_b.pk, original.pk), (dependent_c.pk, original.pk)],
        )

    def test_missing_internal_invalidates_complete_plan_preflight(self):
        self._create_document("E310000000001", with_document=False)
        _item, dependent = self._create_document("E340000000002", modified_encf="E310000000001")
        _item, independent = self._create_document("E310000000003")

        result = self._validate()

        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_document_ids, (independent.pk,))
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].document_id, dependent.pk)
        self.assertEqual(result.issues[0].kind, CertificationDependencyIssueKind.MISSING_INTERNAL)

    def test_duplicate_original_is_ambiguous_and_invalidates_preflight(self):
        self._create_document("E310000000001", source_row=1)
        self._create_document("E310000000001", source_row=2)
        _item, dependent = self._create_document(
            "E340000000002",
            modified_encf="E310000000001",
            source_row=3,
        )

        result = self._validate()

        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].document_id, dependent.pk)
        self.assertEqual(result.issues[0].kind, CertificationDependencyIssueKind.AMBIGUOUS)
        self.assertEqual(result.issues[0].reason, "duplicate_documents_in_same_plan_and_company")
