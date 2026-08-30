from django.test import TestCase

from facturacion.models import (
    Company,
    DGIICertificationDocument,
    DGIICertificationItem,
    DGIICertificationPlan,
)
from facturacion.services.certification_references import (
    ModifiedReferenceClassification,
    classify_modified_reference,
)


class ModifiedReferenceClassificationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Empresa Referencias", rnc="101000001")
        self.plan = DGIICertificationPlan.objects.create(
            company=self.company,
            source_filename="referencias.xlsx",
            file_sha256="4" * 64,
        )

    def _create_document(self, encf, *, raw_data=None, source_row=None):
        row = source_row or self.plan.items.count() + 1
        item = DGIICertificationItem.objects.create(
            plan=self.plan,
            company=self.company,
            ecf_type=encf[1:3],
            dgii_group=2 if encf[1:3] in {"33", "34"} else 1,
            encf=encf,
            source_sheet="ECF",
            source_row=row,
            raw_data=raw_data,
        )
        document = DGIICertificationDocument.objects.create(
            plan=self.plan,
            company=self.company,
            item=item,
            ecf_type=item.ecf_type,
            encf=encf,
        )
        return item, document

    def _assert_internal_pair(self, dependent_encf, original_encf):
        _original_item, original = self._create_document(original_encf)
        _dependent_item, dependent = self._create_document(
            dependent_encf,
            raw_data={
                "NCFModificado": original_encf,
                "RNCOtroContribuyente": "#e",
            },
        )

        result = classify_modified_reference(dependent, original_encf)

        self.assertEqual(result.classification, ModifiedReferenceClassification.INTERNAL)
        self.assertEqual(result.document_id, original.pk)

    def test_real_e33_reference_is_internal(self):
        self._assert_internal_pair("E330000000001", "E320000000006")

    def test_real_e34_credit_note_reference_is_internal(self):
        self._assert_internal_pair("E340000000002", "E310000000034")

    def test_real_e34_export_reference_is_internal(self):
        self._assert_internal_pair("E340000000018", "E460000000009")

    def test_item_without_document_is_missing_internal(self):
        DGIICertificationItem.objects.create(
            plan=self.plan,
            company=self.company,
            ecf_type="31",
            dgii_group=1,
            encf="E310000000099",
            source_sheet="ECF",
            source_row=1,
        )
        _item, dependent = self._create_document(
            "E340000000099",
            raw_data={"NCFModificado": "E310000000099"},
            source_row=2,
        )

        result = classify_modified_reference(dependent, "E310000000099")

        self.assertEqual(result.classification, ModifiedReferenceClassification.MISSING_INTERNAL)
        self.assertIsNone(result.document_id)

    def test_different_other_taxpayer_rnc_is_external(self):
        _item, dependent = self._create_document(
            "E340000000098",
            raw_data={
                "NCFModificado": "E310000000098",
                "RNCOtroContribuyente": "202-00000-2",
            },
        )

        result = classify_modified_reference(dependent, "E310000000098")

        self.assertEqual(result.classification, ModifiedReferenceClassification.EXTERNAL)
        self.assertIsNone(result.document_id)

    def test_duplicate_documents_are_ambiguous(self):
        self._create_document("E310000000097", source_row=1)
        self._create_document("E310000000097", source_row=2)
        _item, dependent = self._create_document(
            "E340000000097",
            raw_data={"NCFModificado": "E310000000097"},
            source_row=3,
        )

        result = classify_modified_reference(dependent, "E310000000097")

        self.assertEqual(result.classification, ModifiedReferenceClassification.AMBIGUOUS)
        self.assertEqual(result.evidence, "duplicate_documents_in_same_plan_and_company")

    def test_self_reference_is_ambiguous(self):
        _item, document = self._create_document(
            "E340000000096",
            raw_data={"NCFModificado": "E340000000096"},
        )

        result = classify_modified_reference(document, document.encf)

        self.assertEqual(result.classification, ModifiedReferenceClassification.AMBIGUOUS)
        self.assertEqual(result.evidence, "self_reference")

    def test_no_match_without_external_evidence_is_missing_internal(self):
        _item, dependent = self._create_document(
            "E340000000095",
            raw_data={"NCFModificado": "E310000000095"},
        )

        result = classify_modified_reference(dependent, "E310000000095")

        self.assertEqual(result.classification, ModifiedReferenceClassification.MISSING_INTERNAL)
        self.assertEqual(result.evidence, "no_internal_match_and_no_external_evidence")
