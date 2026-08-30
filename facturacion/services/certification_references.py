"""Classification of modified e-CF references within a certification plan."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from facturacion.models import DGIICertificationDocument, DGIICertificationItem


class ModifiedReferenceClassification(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    MISSING_INTERNAL = "missing_internal"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ModifiedReferenceResult:
    classification: ModifiedReferenceClassification
    modified_encf: str
    document_id: int | None = None
    evidence: str = ""


def _normalized_encf(value: str) -> str:
    return str(value or "").strip().upper()


def _digits(value: object) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def classify_modified_reference(
    document: DGIICertificationDocument,
    modified_encf: str,
    *,
    other_taxpayer_rnc: str | None = None,
    allow_raw_data_external_evidence: bool = True,
) -> ModifiedReferenceResult:
    """Classify one signed reference without granting submission authority."""

    normalized_encf = _normalized_encf(modified_encf)
    if not normalized_encf:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.AMBIGUOUS,
            normalized_encf,
            evidence="empty_modified_encf",
        )

    candidates = list(
        DGIICertificationDocument.objects.filter(
            plan_id=document.plan_id,
            company_id=document.company_id,
            encf__iexact=normalized_encf,
        )
        .order_by("pk")
        .values_list("pk", flat=True)[:2]
    )
    if document.pk in candidates:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.AMBIGUOUS,
            normalized_encf,
            evidence="self_reference",
        )
    if len(candidates) == 1:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.INTERNAL,
            normalized_encf,
            document_id=candidates[0],
            evidence="single_document_in_same_plan_and_company",
        )
    if len(candidates) > 1:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.AMBIGUOUS,
            normalized_encf,
            evidence="duplicate_documents_in_same_plan_and_company",
        )

    expected_items = DGIICertificationItem.objects.filter(
        plan_id=document.plan_id,
        company_id=document.company_id,
        encf__iexact=normalized_encf,
    ).count()
    if expected_items == 1:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.MISSING_INTERNAL,
            normalized_encf,
            evidence="item_exists_but_document_is_missing",
        )
    if expected_items > 1:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.AMBIGUOUS,
            normalized_encf,
            evidence="duplicate_items_in_same_plan_and_company",
        )

    if allow_raw_data_external_evidence and other_taxpayer_rnc is None:
        raw_data = document.item.raw_data if isinstance(document.item.raw_data, dict) else {}
        other_taxpayer_rnc = raw_data.get("RNCOtroContribuyente")
    other_taxpayer_rnc = _digits(other_taxpayer_rnc)
    issuer_rnc = _digits(document.company.rnc)
    if other_taxpayer_rnc and other_taxpayer_rnc != issuer_rnc:
        return ModifiedReferenceResult(
            ModifiedReferenceClassification.EXTERNAL,
            normalized_encf,
            evidence="different_rnc_in_rnc_otro_contribuyente",
        )

    return ModifiedReferenceResult(
        ModifiedReferenceClassification.MISSING_INTERNAL,
        normalized_encf,
        evidence="no_internal_match_and_no_external_evidence",
    )
