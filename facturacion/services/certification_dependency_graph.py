"""Locked, deterministic dependency-graph preflight for DGII certification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from facturacion.models import DGIICertificationDocument, DGIICertificationPlan
from facturacion.services.certification_locking import CertificationLockService
from facturacion.services.certification_references import (
    ModifiedReferenceClassification,
    classify_modified_reference,
)


class CertificationDependencyIssueKind(str, Enum):
    MISSING_INTERNAL = "missing_internal"
    AMBIGUOUS = "ambiguous"
    CYCLE = "cycle"
    ARTIFACT_MISSING = "artifact_missing"
    ARTIFACT_CHANGED = "artifact_changed"


@dataclass(frozen=True)
class CertificationSignedArtifactSnapshot:
    document_id: int
    signed_xml_path: str
    sha256: str
    signed_xml: str
    modified_encf: str = ""
    other_taxpayer_rnc: str = ""
    issuer_rnc: str = ""


@dataclass(frozen=True)
class CertificationDependencyEdge:
    dependent_document_id: int
    original_document_id: int


@dataclass(frozen=True)
class CertificationDependencyIssue:
    kind: CertificationDependencyIssueKind
    document_id: int
    modified_encf: str
    reason: str
    related_document_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class CertificationDependencyGraphDiagnostic:
    plan_id: int
    is_valid: bool
    valid_document_ids: tuple[int, ...]
    edges: tuple[CertificationDependencyEdge, ...]
    issues: tuple[CertificationDependencyIssue, ...]


class CertificationDependencyGraphPreflight:
    """Validate the full graph while the plan and all of its rows are locked."""

    EMPTY_MARKERS = {"", "#E", "E", "N/A", "NA", "NULL", "NONE", "NO APLICA"}

    def __init__(self, *, lock_service: CertificationLockService | None = None):
        self.lock_service = lock_service or CertificationLockService()

    def validate_locked_plan(
        self,
        plan: DGIICertificationPlan,
        *,
        signed_artifact_snapshots: dict[int, CertificationSignedArtifactSnapshot] | None = None,
    ) -> CertificationDependencyGraphDiagnostic:
        item_ids = list(plan.items.order_by("pk").values_list("pk", flat=True))
        document_ids = list(
            plan.certification_documents.order_by("pk").values_list("pk", flat=True)
        )
        scope = self.lock_service.lock_scope(
            plan_id=plan.pk,
            item_ids=item_ids,
            document_ids=document_ids,
        )

        edges: list[CertificationDependencyEdge] = []
        issues: list[CertificationDependencyIssue] = []
        modified_encfs: dict[int, str] = {}
        strict_snapshots = signed_artifact_snapshots is not None
        snapshots = signed_artifact_snapshots or {}

        for document in scope.documents_by_id.values():
            snapshot = snapshots.get(document.pk)
            if strict_snapshots and snapshot is None:
                issues.append(CertificationDependencyIssue(
                    kind=CertificationDependencyIssueKind.ARTIFACT_MISSING,
                    document_id=document.pk,
                    modified_encf="",
                    reason="signed_artifact_snapshot_missing",
                ))
                continue
            if strict_snapshots and (
                snapshot.document_id != document.pk
                or snapshot.signed_xml_path != document.signed_xml_path
                or snapshot.sha256 != document.signed_xml_hash
            ):
                issues.append(CertificationDependencyIssue(
                    kind=CertificationDependencyIssueKind.ARTIFACT_CHANGED,
                    document_id=document.pk,
                    modified_encf=snapshot.modified_encf,
                    reason="signed_artifact_snapshot_changed",
                ))
                continue
            modified_encf = snapshot.modified_encf.strip().upper() if snapshot else self._modified_encf(document)
            if not modified_encf:
                continue
            modified_encfs[document.pk] = modified_encf
            result = classify_modified_reference(
                document,
                modified_encf,
                other_taxpayer_rnc=snapshot.other_taxpayer_rnc if snapshot else None,
                allow_raw_data_external_evidence=not strict_snapshots,
            )
            if result.classification == ModifiedReferenceClassification.INTERNAL:
                edges.append(
                    CertificationDependencyEdge(
                        dependent_document_id=document.pk,
                        original_document_id=result.document_id,
                    )
                )
            elif result.evidence == "self_reference":
                edges.append(
                    CertificationDependencyEdge(
                        dependent_document_id=document.pk,
                        original_document_id=document.pk,
                    )
                )
            elif result.classification == ModifiedReferenceClassification.MISSING_INTERNAL:
                issues.append(
                    CertificationDependencyIssue(
                        kind=CertificationDependencyIssueKind.MISSING_INTERNAL,
                        document_id=document.pk,
                        modified_encf=modified_encf,
                        reason=result.evidence,
                    )
                )
            elif result.classification == ModifiedReferenceClassification.AMBIGUOUS:
                issues.append(
                    CertificationDependencyIssue(
                        kind=CertificationDependencyIssueKind.AMBIGUOUS,
                        document_id=document.pk,
                        modified_encf=modified_encf,
                        reason=result.evidence,
                    )
                )

        sorted_edges = tuple(
            sorted(edges, key=lambda edge: (edge.dependent_document_id, edge.original_document_id))
        )
        issues.extend(self._cycle_issues(sorted_edges, modified_encfs))
        sorted_issues = tuple(
            sorted(
                issues,
                key=lambda issue: (
                    issue.document_id,
                    issue.kind.value,
                    issue.related_document_ids,
                    issue.reason,
                ),
            )
        )
        invalid_document_ids = {issue.document_id for issue in sorted_issues}
        valid_document_ids = tuple(
            document_id
            for document_id in sorted(scope.documents_by_id)
            if document_id not in invalid_document_ids
        )
        return CertificationDependencyGraphDiagnostic(
            plan_id=scope.plan.pk,
            is_valid=not sorted_issues,
            valid_document_ids=valid_document_ids,
            edges=sorted_edges,
            issues=sorted_issues,
        )

    @classmethod
    def _modified_encf(cls, document: DGIICertificationDocument) -> str:
        raw_data = document.item.raw_data if isinstance(document.item.raw_data, dict) else {}
        value = str(raw_data.get("NCFModificado") or "").strip().upper()
        return "" if value in cls.EMPTY_MARKERS else value

    @staticmethod
    def _cycle_issues(
        edges: tuple[CertificationDependencyEdge, ...],
        modified_encfs: dict[int, str],
    ) -> list[CertificationDependencyIssue]:
        adjacency = {edge.dependent_document_id: edge.original_document_id for edge in edges}
        color: dict[int, int] = {}
        stack: list[int] = []
        stack_positions: dict[int, int] = {}
        cycle_components: set[tuple[int, ...]] = set()

        def visit(node: int) -> None:
            color[node] = 1
            stack_positions[node] = len(stack)
            stack.append(node)
            target = adjacency.get(node)
            if target is not None:
                if color.get(target, 0) == 0:
                    visit(target)
                elif color.get(target) == 1:
                    cycle_components.add(tuple(sorted(stack[stack_positions[target] :])))
            stack.pop()
            stack_positions.pop(node, None)
            color[node] = 2

        for node in sorted(set(adjacency) | set(adjacency.values())):
            if color.get(node, 0) == 0:
                visit(node)

        issues: list[CertificationDependencyIssue] = []
        for component in sorted(cycle_components):
            reason = "self_reference" if len(component) == 1 else "dependency_cycle"
            for document_id in component:
                issues.append(
                    CertificationDependencyIssue(
                        kind=CertificationDependencyIssueKind.CYCLE,
                        document_id=document_id,
                        modified_encf=modified_encfs.get(document_id, ""),
                        reason=reason,
                        related_document_ids=component,
                    )
                )
        return issues
