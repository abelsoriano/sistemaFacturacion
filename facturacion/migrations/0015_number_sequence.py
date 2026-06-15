import re

from django.db import migrations, models
import django.db.models.deletion


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


def seed_number_sequences(apps, schema_editor):
    NumberSequence = apps.get_model('facturacion', 'NumberSequence')

    for code, definition in SEQUENCE_DEFINITIONS.items():
        model = apps.get_model('facturacion', definition['model'])
        regex = re.compile(definition['pattern'])
        max_number = 0

        values = (
            model.objects
            .exclude(**{f"{definition['field']}__isnull": True})
            .exclude(**{definition['field']: ''})
            .values_list(definition['field'], flat=True)
        )
        for value in values:
            match = regex.match(str(value))
            if match:
                max_number = max(max_number, int(match.group(1)))

        NumberSequence.objects.update_or_create(
            code=code,
            defaults={
                'sequence_kind': definition['sequence_kind'],
                'document_type': definition['document_type'],
                'prefix': definition['prefix'],
                'suffix': definition['suffix'],
                'padding': definition['padding'],
                'next_number': max_number + 1,
                'scope_key': 'default',
                'is_active': True,
            },
        )


def unseed_number_sequences(apps, schema_editor):
    NumberSequence = apps.get_model('facturacion', 'NumberSequence')
    NumberSequence.objects.filter(code__in=SEQUENCE_DEFINITIONS.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0014_quotation_module'),
    ]

    operations = [
        migrations.CreateModel(
            name='NumberSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=80)),
                ('sequence_kind', models.CharField(choices=[('commercial', 'Comercial'), ('internal', 'Interna')], max_length=20)),
                ('document_type', models.CharField(choices=[('invoice', 'Factura'), ('quotation', 'Cotizacion'), ('credit_note', 'Nota de Credito'), ('product_internal_code', 'Codigo interno producto')], max_length=40)),
                ('prefix', models.CharField(blank=True, default='', max_length=20)),
                ('suffix', models.CharField(blank=True, default='', max_length=20)),
                ('next_number', models.PositiveBigIntegerField(default=1)),
                ('padding', models.PositiveSmallIntegerField(default=8)),
                ('scope_key', models.CharField(default='default', max_length=80)),
                ('branch_code', models.CharField(blank=True, default='', max_length=40)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('issuer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='number_sequences', to='facturacion.ecfissuerconfig')),
            ],
            options={
                'verbose_name': 'Secuencia numerica',
                'verbose_name_plural': 'Secuencias numericas',
                'ordering': ['code'],
            },
        ),
        migrations.AddConstraint(
            model_name='numbersequence',
            constraint=models.UniqueConstraint(condition=models.Q(('issuer__isnull', True)), fields=('code', 'scope_key', 'branch_code'), name='unique_number_sequence_default_scope'),
        ),
        migrations.AddConstraint(
            model_name='numbersequence',
            constraint=models.UniqueConstraint(condition=models.Q(('issuer__isnull', False)), fields=('code', 'scope_key', 'issuer', 'branch_code'), name='unique_number_sequence_issuer_scope'),
        ),
        migrations.RunPython(seed_number_sequences, unseed_number_sequences),
    ]
