"""Transactional numbering service for commercial and internal sequences."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from facturacion.models import Company, NumberSequence


@dataclass(frozen=True)
class SequenceDefinition:
    sequence_kind: str
    document_type: str
    prefix: str
    suffix: str
    padding: int


DEFAULT_SEQUENCES = {
    'invoice': SequenceDefinition('commercial', 'invoice', 'FAC-', '', 8),
    'quotation': SequenceDefinition('commercial', 'quotation', 'COT-', '', 8),
    'credit_note': SequenceDefinition('commercial', 'credit_note', 'NC-', '', 8),
    'product_internal_code': SequenceDefinition('internal', 'product_internal_code', 'PRD-', '', 8),
}


class NumberingService:
    """Allocate visible commercial numbers with row-level locking."""

    max_retries = 3
    max_collision_skips = 100

    def allocate_unique(self, *, code: str, model_class, field_name: str, company: Company) -> str:
        """Return the next unused formatted number for the given model field."""
        if not company or not getattr(company, 'pk', None):
            raise ValidationError(f"La secuencia {code} requiere una empresa activa.")
        last_error = None
        for _attempt in range(self.max_retries):
            try:
                return self._allocate_unique_atomic(
                    code=code,
                    model_class=model_class,
                    field_name=field_name,
                    company=company,
                )
            except IntegrityError as exc:
                last_error = exc
        raise ValidationError(f"No fue posible asignar una secuencia unica para {code}: {last_error}")

    @transaction.atomic
    def _allocate_unique_atomic(self, *, code: str, model_class, field_name: str, company: Company) -> str:
        sequence = self._locked_sequence(code, company=company)

        for _ in range(self.max_collision_skips):
            assigned = sequence.next_number
            formatted = sequence.format_number(assigned)
            sequence.next_number = assigned + 1
            sequence.save(update_fields=['next_number', 'updated_at'])

            lookup = {field_name: formatted}
            if not model_class.objects.filter(company=company, **lookup).exists():
                return formatted

        raise ValidationError(f"La secuencia {code} encontro demasiadas colisiones consecutivas.")

    def _locked_sequence(self, code: str, *, company: Company) -> NumberSequence:
        sequence = (
            NumberSequence.objects
            .select_for_update()
            .filter(
                company=company,
                code=code,
                scope_key='default',
                branch_code='',
                issuer__isnull=True,
                is_active=True,
            )
            .first()
        )
        if sequence:
            return sequence
        self._create_default_sequence(code, company=company)
        return (
            NumberSequence.objects
            .select_for_update()
            .get(
                company=company,
                code=code,
                scope_key='default',
                branch_code='',
                issuer__isnull=True,
                is_active=True,
            )
        )

    def _create_default_sequence(self, code: str, *, company: Company) -> None:
        definition = DEFAULT_SEQUENCES.get(code)
        if not definition:
            raise ValidationError(f"No existe definicion de secuencia para {code}.")
        NumberSequence.objects.get_or_create(
            company=company,
            code=code,
            scope_key='default',
            branch_code='',
            issuer=None,
            defaults={
                'sequence_kind': definition.sequence_kind,
                'document_type': definition.document_type,
                'prefix': definition.prefix,
                'suffix': definition.suffix,
                'padding': definition.padding,
                'next_number': 1,
                'is_active': True,
            },
        )
