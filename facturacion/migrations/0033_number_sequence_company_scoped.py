import re

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Count


SEQUENCE_DEFINITIONS = {
    'invoice': {
        'sequence_kind': 'commercial',
        'document_type': 'invoice',
        'prefix': 'FAC-',
        'suffix': '',
        'padding': 8,
        'model': 'Invoice',
        'field': 'invoice_number',
        'pattern': r'^FAC-(\d+)$',
    },
    'quotation': {
        'sequence_kind': 'commercial',
        'document_type': 'quotation',
        'prefix': 'COT-',
        'suffix': '',
        'padding': 8,
        'model': 'Quotation',
        'field': 'quotation_number',
        'pattern': r'^COT-(\d+)$',
    },
    'credit_note': {
        'sequence_kind': 'commercial',
        'document_type': 'credit_note',
        'prefix': 'NC-',
        'suffix': '',
        'padding': 8,
        'model': 'CreditNote',
        'field': 'credit_note_number',
        'pattern': r'^NC-(\d+)$',
    },
    'product_internal_code': {
        'sequence_kind': 'internal',
        'document_type': 'product_internal_code',
        'prefix': 'PRD-',
        'suffix': '',
        'padding': 8,
        'model': 'Product',
        'field': 'barcode',
        'pattern': r'^PRD-(\d+)$',
    },
}


def _next_number_for_company(apps, *, company, definition):
    model = apps.get_model('facturacion', definition['model'])
    pattern = re.compile(definition['pattern'])
    max_number = 0
    for value in (
        model.objects.filter(company=company)
        .exclude(**{definition['field']: ''})
        .values_list(definition['field'], flat=True)
    ):
        if value is None:
            continue
        match = pattern.match(str(value))
        if match:
            max_number = max(max_number, int(match.group(1)))
    return max_number + 1


def seed_company_number_sequences(apps, schema_editor):
    Company = apps.get_model('facturacion', 'Company')
    NumberSequence = apps.get_model('facturacion', 'NumberSequence')

    for sequence in NumberSequence.objects.filter(issuer__isnull=False, company__isnull=True).select_related('issuer'):
        if sequence.issuer.company_id:
            NumberSequence.objects.filter(pk=sequence.pk).update(company_id=sequence.issuer.company_id)

    companies = list(Company.objects.filter(is_active=True).order_by('id'))
    if not companies:
        companies = list(Company.objects.order_by('id'))

    for code, definition in SEQUENCE_DEFINITIONS.items():
        global_sequence = NumberSequence.objects.filter(
            code=code,
            scope_key='default',
            branch_code='',
            issuer__isnull=True,
            company__isnull=True,
        ).order_by('id').first()

        for company in companies:
            next_number = _next_number_for_company(apps, company=company, definition=definition)
            defaults = {
                'sequence_kind': global_sequence.sequence_kind if global_sequence else definition['sequence_kind'],
                'document_type': global_sequence.document_type if global_sequence else definition['document_type'],
                'prefix': global_sequence.prefix if global_sequence else definition['prefix'],
                'suffix': global_sequence.suffix if global_sequence else definition['suffix'],
                'padding': global_sequence.padding if global_sequence else definition['padding'],
                'next_number': next_number,
                'is_active': global_sequence.is_active if global_sequence else True,
            }
            existing = NumberSequence.objects.filter(
                company=company,
                code=code,
                scope_key='default',
                branch_code='',
                issuer__isnull=True,
            ).order_by('id').first()
            if existing:
                NumberSequence.objects.filter(pk=existing.pk).update(**defaults)
                continue
            NumberSequence.objects.create(
                company=company,
                code=code,
                scope_key='default',
                branch_code='',
                issuer=None,
                **defaults,
            )

        if global_sequence:
            global_sequence.delete()

    null_sequences = list(NumberSequence.objects.filter(company__isnull=True).values_list('id', flat=True))
    duplicate_default_scopes = list(
        NumberSequence.objects.filter(company__isnull=False, issuer__isnull=True)
        .values('company_id', 'code', 'scope_key', 'branch_code')
        .annotate(count=Count('id'))
        .filter(count__gt=1)[:20]
    )
    duplicate_issuer_scopes = list(
        NumberSequence.objects.filter(company__isnull=False, issuer__isnull=False)
        .values('company_id', 'code', 'scope_key', 'issuer_id', 'branch_code')
        .annotate(count=Count('id'))
        .filter(count__gt=1)[:20]
    )
    cross_company_issuers = list(
        NumberSequence.objects.filter(company__isnull=False, issuer__isnull=False)
        .exclude(company_id=models.F('issuer__company_id'))
        .values_list('id', flat=True)
    )

    if null_sequences or duplicate_default_scopes or duplicate_issuer_scopes or cross_company_issuers:
        raise RuntimeError(
            "No se puede aplicar NumberSequence por empresa. "
            f"secuencias_sin_company={null_sequences}, "
            f"duplicados_default={duplicate_default_scopes}, "
            f"duplicados_issuer={duplicate_issuer_scopes}, "
            f"issuer_cross_company={cross_company_issuers}."
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('facturacion', '0032_company_scoped_commercial_document_numbers'),
    ]

    operations = [
        migrations.AddField(
            model_name='numbersequence',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='number_sequences',
                to='facturacion.company',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='numbersequence',
            name='unique_number_sequence_default_scope',
        ),
        migrations.RemoveConstraint(
            model_name='numbersequence',
            name='unique_number_sequence_issuer_scope',
        ),
        migrations.RunPython(seed_company_number_sequences, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='numbersequence',
            constraint=models.UniqueConstraint(
                condition=models.Q(('company__isnull', False), ('issuer__isnull', True)),
                fields=('company', 'code', 'scope_key', 'branch_code'),
                name='unique_number_sequence_company_default_scope',
            ),
        ),
        migrations.AddConstraint(
            model_name='numbersequence',
            constraint=models.UniqueConstraint(
                condition=models.Q(('company__isnull', False), ('issuer__isnull', False)),
                fields=('company', 'code', 'scope_key', 'issuer', 'branch_code'),
                name='unique_number_sequence_company_issuer_scope',
            ),
        ),
    ]
