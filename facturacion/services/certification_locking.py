"""Canonical PostgreSQL row locking for DGII certification plans."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from django.db import connection

from facturacion.models import (
    DGIICertificationDocument,
    DGIICertificationItem,
    DGIICertificationPlan,
)


class CertificationLockError(Exception):
    """Base exception for certification lock protocol failures."""


class CertificationLockProtocolError(CertificationLockError):
    """Raised when canonical locks are requested outside a transaction."""


class CertificationLockScopeIncomplete(CertificationLockError):
    """Raised when a requested scope omits a required related row."""


class CertificationTenantMismatch(CertificationLockError):
    """Raised when a row does not belong to the locked plan and company."""


class CertificationArtifactChanged(CertificationLockError):
    """Reserved for publishing an artifact prepared from a stale snapshot."""


class CertificationMutationBlocked(CertificationLockError):
    """Reserved for mutations forbidden by the current submission outcome."""


class CertificationPlanNotFound(CertificationLockError):
    """Raised when the requested certification plan does not exist."""


class CertificationItemNotFound(CertificationLockError):
    """Raised when a requested certification item does not exist."""


class CertificationDocumentNotFound(CertificationLockError):
    """Raised when a requested certification document does not exist."""


@dataclass(frozen=True)
class CertificationLockedScope:
    """Rows locked under one plan, exposed through immutable mappings."""

    plan: DGIICertificationPlan
    items_by_id: Mapping[int, DGIICertificationItem]
    documents_by_id: Mapping[int, DGIICertificationDocument]

    @classmethod
    def build(
        cls,
        *,
        plan: DGIICertificationPlan,
        items: Iterable[DGIICertificationItem],
        documents: Iterable[DGIICertificationDocument],
    ) -> "CertificationLockedScope":
        return cls(
            plan=plan,
            items_by_id=MappingProxyType({item.pk: item for item in items}),
            documents_by_id=MappingProxyType({document.pk: document for document in documents}),
        )

    def item(self, item_id: int) -> DGIICertificationItem:
        try:
            return self.items_by_id[int(item_id)]
        except (KeyError, TypeError, ValueError) as exc:
            raise CertificationItemNotFound(f"Item de certificación no bloqueado: {item_id}.") from exc

    def document(self, document_id: int) -> DGIICertificationDocument:
        try:
            return self.documents_by_id[int(document_id)]
        except (KeyError, TypeError, ValueError) as exc:
            raise CertificationDocumentNotFound(
                f"Documento de certificación no bloqueado: {document_id}."
            ) from exc

    def document_for_item(self, item_id: int) -> DGIICertificationDocument:
        normalized_id = int(item_id)
        for document in self.documents_by_id.values():
            if document.item_id == normalized_id:
                return document
        raise CertificationDocumentNotFound(
            f"No hay documento bloqueado para el item de certificación {normalized_id}."
        )

    def assert_company_consistency(self) -> None:
        for item in self.items_by_id.values():
            if item.plan_id != self.plan.pk or item.company_id != self.plan.company_id:
                raise CertificationTenantMismatch(
                    f"El item {item.pk} no pertenece al plan/empresa bloqueados."
                )
        for document in self.documents_by_id.values():
            if (
                document.plan_id != self.plan.pk
                or document.company_id != self.plan.company_id
                or document.item_id not in self.items_by_id
            ):
                raise CertificationTenantMismatch(
                    f"El documento {document.pk} no pertenece al scope bloqueado."
                )

    def assert_complete(
        self,
        *,
        item_ids: Iterable[int],
        document_ids: Iterable[int],
    ) -> None:
        expected_item_ids = {int(item_id) for item_id in item_ids}
        expected_document_ids = {int(document_id) for document_id in document_ids}
        actual_item_ids = set(self.items_by_id)
        actual_document_ids = set(self.documents_by_id)
        if expected_item_ids != actual_item_ids or expected_document_ids != actual_document_ids:
            raise CertificationLockScopeIncomplete(
                "El scope bloqueado no coincide con los items/documentos requeridos."
            )


class CertificationLockService:
    """Acquire certification locks in the only supported cross-model order."""

    @staticmethod
    def _assert_transaction() -> None:
        if not connection.in_atomic_block:
            raise CertificationLockProtocolError(
                "Los locks de certificación requieren transaction.atomic()."
            )

    @staticmethod
    def _normalize_ids(values: Iterable[int]) -> list[int]:
        return sorted({int(value) for value in values})

    def lock_plan(self, *, plan_id: int) -> DGIICertificationPlan:
        self._assert_transaction()
        try:
            return DGIICertificationPlan.objects.select_for_update(of=("self",)).get(pk=plan_id)
        except DGIICertificationPlan.DoesNotExist as exc:
            raise CertificationPlanNotFound(f"Plan de certificación inexistente: {plan_id}.") from exc

    def lock_items(
        self,
        *,
        plan: DGIICertificationPlan,
        item_ids: Iterable[int],
    ) -> list[DGIICertificationItem]:
        self._assert_transaction()
        ids = self._normalize_ids(item_ids)
        if not ids:
            return []

        items = list(
            DGIICertificationItem.objects
            .select_for_update(of=("self",))
            .filter(plan_id=plan.pk, company_id=plan.company_id, pk__in=ids)
            .order_by("pk")
        )
        self._raise_for_missing_or_mismatched(
            model=DGIICertificationItem,
            expected_ids=ids,
            actual_ids=[item.pk for item in items],
            plan=plan,
            missing_exception=CertificationItemNotFound,
            entity="item",
        )
        return items

    def lock_documents(
        self,
        *,
        plan: DGIICertificationPlan,
        document_ids: Iterable[int],
        locked_item_ids: Iterable[int],
    ) -> list[DGIICertificationDocument]:
        self._assert_transaction()
        ids = self._normalize_ids(document_ids)
        item_ids = set(self._normalize_ids(locked_item_ids))
        if not ids:
            return []

        documents = list(
            DGIICertificationDocument.objects
            .select_for_update(of=("self",))
            .filter(plan_id=plan.pk, company_id=plan.company_id, pk__in=ids)
            .order_by("pk")
        )
        self._raise_for_missing_or_mismatched(
            model=DGIICertificationDocument,
            expected_ids=ids,
            actual_ids=[document.pk for document in documents],
            plan=plan,
            missing_exception=CertificationDocumentNotFound,
            entity="documento",
        )

        omitted_item_ids = sorted({document.item_id for document in documents} - item_ids)
        if omitted_item_ids:
            raise CertificationLockScopeIncomplete(
                "El scope documental omite items requeridos: "
                + ", ".join(str(item_id) for item_id in omitted_item_ids)
                + "."
            )
        return documents

    def lock_scope(
        self,
        *,
        plan_id: int,
        item_ids: Iterable[int],
        document_ids: Iterable[int],
    ) -> CertificationLockedScope:
        self._assert_transaction()
        requested_item_ids = self._normalize_ids(item_ids)
        requested_document_ids = self._normalize_ids(document_ids)
        plan = self.lock_plan(plan_id=plan_id)
        items = self.lock_items(plan=plan, item_ids=requested_item_ids)
        documents = self.lock_documents(
            plan=plan,
            document_ids=requested_document_ids,
            locked_item_ids=[item.pk for item in items],
        )
        scope = CertificationLockedScope.build(plan=plan, items=items, documents=documents)
        scope.assert_company_consistency()
        scope.assert_complete(
            item_ids=requested_item_ids,
            document_ids=requested_document_ids,
        )
        return scope

    @staticmethod
    def _raise_for_missing_or_mismatched(
        *,
        model,
        expected_ids: list[int],
        actual_ids: list[int],
        plan: DGIICertificationPlan,
        missing_exception,
        entity: str,
    ) -> None:
        missing_ids = sorted(set(expected_ids) - set(actual_ids))
        if not missing_ids:
            return

        existing = list(
            model.objects
            .filter(pk__in=missing_ids)
            .values("pk", "plan_id", "company_id")
            .order_by("pk")
        )
        mismatched_ids = [
            row["pk"]
            for row in existing
            if row["plan_id"] != plan.pk or row["company_id"] != plan.company_id
        ]
        if mismatched_ids:
            raise CertificationTenantMismatch(
                f"{entity.capitalize()} fuera del plan/empresa bloqueados: "
                + ", ".join(str(row_id) for row_id in mismatched_ids)
                + "."
            )

        nonexistent_ids = sorted(set(missing_ids) - {row["pk"] for row in existing})
        raise missing_exception(
            f"{entity.capitalize()} de certificación inexistente: "
            + ", ".join(str(row_id) for row_id in nonexistent_ids)
            + "."
        )
