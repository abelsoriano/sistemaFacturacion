import hashlib
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from facturacion.models import (
    Company,
    DGIICertificationCommercialApprovalEvent,
    DGIICertificationCommercialApprovalItem,
    DGIICertificationCommercialApprovalPlan,
    DGIICertificationDocument,
    ElectronicFiscalDocument,
)


class DGIICertificationCommercialApprovalImportError(ValueError):
    pass


class DGIICertificationCommercialApprovalImporter:
    sheet_name = 'ACEECF_Generadas'
    required_columns = [
        'Version',
        'RNCEmisor',
        'eNCF',
        'FechaEmision',
        'MontoTotal',
        'RNCComprador',
        'Estado',
        'DetalleMotivoRechazo',
        'FechaHoraAprobacionComercial',
    ]

    approved_values = {'aprobado', 'aprobada', 'aceptado', 'aceptada', '1', 'true', 'si', 'sí'}
    rejected_values = {'rechazado', 'rechazada', 'rejected', '2', 'false', 'no'}
    pending_values = {'pendiente', 'pending', '0', '3'}

    def import_workbook(self, *, uploaded_file, company: Company, user=None):
        file_bytes = uploaded_file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing = DGIICertificationCommercialApprovalPlan.objects.filter(
            company=company,
            file_sha256=file_hash,
        ).order_by('-imported_at').first()
        if existing:
            return existing, self._summary(existing, errors=[])

        try:
            workbook = load_workbook(filename=self._bytes_file(file_bytes), data_only=True, read_only=True)
        except Exception as exc:
            self._record_structure_error(company, user, 'El archivo no es un XLSX válido.', {'error': str(exc)})
            raise DGIICertificationCommercialApprovalImportError('El archivo no es un XLSX válido.') from exc

        if self.sheet_name not in workbook.sheetnames:
            message = f'El archivo no contiene la hoja {self.sheet_name}.'
            self._record_structure_error(company, user, message, {'sheets': workbook.sheetnames})
            raise DGIICertificationCommercialApprovalImportError(message)

        worksheet = workbook[self.sheet_name]
        rows = worksheet.iter_rows(values_only=True)
        try:
            headers = [self._clean_header(value) for value in next(rows)]
        except StopIteration as exc:
            message = 'La hoja ACEECF_Generadas está vacía.'
            self._record_structure_error(company, user, message, {})
            raise DGIICertificationCommercialApprovalImportError(message) from exc

        header_map = {header: index for index, header in enumerate(headers) if header}
        missing = [column for column in self.required_columns if column not in header_map]
        if missing:
            message = 'Faltan columnas obligatorias.'
            self._record_structure_error(company, user, message, {'missing_columns': missing})
            raise DGIICertificationCommercialApprovalImportError(f'{message} {", ".join(missing)}')

        company_rnc = self._digits(company.rnc)
        parsed_rows = []
        errors = []
        for row_number, row in enumerate(rows, start=2):
            raw = {
                column: self._json_value(row[header_map[column]] if header_map[column] < len(row) else None)
                for column in self.required_columns
            }
            if not any(value not in (None, '') for value in raw.values()):
                continue
            encf = str(raw.get('eNCF') or '').strip()
            issuer_rnc = self._digits(raw.get('RNCEmisor'))
            buyer_rnc = self._digits(raw.get('RNCComprador'))
            if not encf:
                errors.append(f'Fila {row_number}: eNCF no puede estar vacío.')
                continue
            if buyer_rnc != company_rnc:
                errors.append(f'Fila {row_number}: RNCComprador {buyer_rnc or "vacío"} no coincide con el RNC de la empresa activa.')
                continue
            try:
                issue_date = self._parse_date(raw.get('FechaEmision'))
                approval_at = self._parse_datetime(raw.get('FechaHoraAprobacionComercial'))
                amount = self._parse_decimal(raw.get('MontoTotal'))
            except DGIICertificationCommercialApprovalImportError as exc:
                errors.append(f'Fila {row_number}: {exc}')
                continue
            parsed_rows.append({
                'row_number': row_number,
                'raw': raw,
                'version': str(raw.get('Version') or '').strip(),
                'issuer_rnc': issuer_rnc,
                'encf': encf,
                'issue_date': issue_date,
                'total_amount': amount,
                'buyer_rnc': buyer_rnc,
                'approval_receiver_rnc': buyer_rnc,
                'source_approval_status': self.normalize_status(raw.get('Estado')),
                'rejection_reason': str(raw.get('DetalleMotivoRechazo') or '').strip(),
                'commercial_approval_at': approval_at,
            })

        if errors:
            self._record_structure_error(company, user, 'No se pudo importar el Excel DGII.', {'errors': errors})
            raise DGIICertificationCommercialApprovalImportError(errors[0])

        with transaction.atomic():
            previous_exists = DGIICertificationCommercialApprovalPlan.objects.filter(company=company).exists()
            plan = DGIICertificationCommercialApprovalPlan.objects.create(
                company=company,
                source_filename=getattr(uploaded_file, 'name', 'aprobaciones-comerciales.xlsx'),
                file_sha256=file_hash,
                imported_by=user,
                status=DGIICertificationCommercialApprovalPlan.STATUS_PROCESSED,
            )
            counts = {
                'approved': 0,
                'rejected': 0,
                'pending': 0,
                'matched': 0,
                'not_found': 0,
                'ambiguous': 0,
            }
            for parsed in parsed_rows:
                match = self._match_local_document(company, parsed)
                item = DGIICertificationCommercialApprovalItem.objects.create(
                    plan=plan,
                    company=company,
                    version=parsed['version'],
                    issuer_rnc=parsed['issuer_rnc'],
                    encf=parsed['encf'],
                    issue_date=parsed['issue_date'],
                    total_amount=parsed['total_amount'],
                    buyer_rnc=parsed['buyer_rnc'],
                    approval_receiver_rnc=parsed['approval_receiver_rnc'],
                    dgii_status=self._legacy_status(parsed['source_approval_status']),
                    source_approval_status=parsed['source_approval_status'],
                    submission_status=DGIICertificationCommercialApprovalItem.SUBMISSION_PENDING,
                    rejection_reason=parsed['rejection_reason'],
                    commercial_approval_at=parsed['commercial_approval_at'],
                    raw_data=parsed['raw'],
                    matched_document_type=match['document_type'],
                    matched_document_id=match['document_id'],
                    match_status=match['status'],
                    match_observations=match['observations'],
                    source_row=parsed['row_number'],
                )
                self._record_item_events(plan, item, match, user)
                if item.source_approval_status == DGIICertificationCommercialApprovalItem.SOURCE_APPROVED:
                    counts['approved'] += 1
                elif item.source_approval_status == DGIICertificationCommercialApprovalItem.SOURCE_REJECTED:
                    counts['rejected'] += 1
                else:
                    counts['pending'] += 1
                if item.match_status == DGIICertificationCommercialApprovalItem.MATCH_MATCHED:
                    counts['matched'] += 1
                elif item.match_status == DGIICertificationCommercialApprovalItem.MATCH_AMBIGUOUS:
                    counts['ambiguous'] += 1
                elif item.match_status == DGIICertificationCommercialApprovalItem.MATCH_NOT_FOUND:
                    counts['not_found'] += 1

            plan.total_records = len(parsed_rows)
            plan.approved_count = counts['approved']
            plan.rejected_count = counts['rejected']
            plan.pending_count = counts['pending']
            plan.raw_summary = {
                **counts,
                'errors': [],
                'sheet': self.sheet_name,
                'replaced_previous': previous_exists,
            }
            plan.save(update_fields=[
                'total_records',
                'approved_count',
                'rejected_count',
                'pending_count',
                'raw_summary',
                'updated_at',
            ])
            DGIICertificationCommercialApprovalEvent.objects.create(
                company=company,
                plan=plan,
                event_type=(
                    DGIICertificationCommercialApprovalEvent.EVENT_REPLACED
                    if previous_exists
                    else DGIICertificationCommercialApprovalEvent.EVENT_IMPORTED
                ),
                message='Aprobaciones comerciales DGII importadas correctamente.',
                payload=self._summary(plan, errors=[]),
                created_by=user,
            )
        return plan, self._summary(plan, errors=[])

    def normalize_status(self, value):
        normalized = self._normalize_text(value)
        if normalized in self.approved_values:
            return DGIICertificationCommercialApprovalItem.SOURCE_APPROVED
        if normalized in self.rejected_values:
            return DGIICertificationCommercialApprovalItem.SOURCE_REJECTED
        if normalized in self.pending_values:
            return DGIICertificationCommercialApprovalItem.SOURCE_PENDING
        return DGIICertificationCommercialApprovalItem.SOURCE_UNKNOWN

    def _legacy_status(self, source_status):
        return {
            DGIICertificationCommercialApprovalItem.SOURCE_APPROVED: DGIICertificationCommercialApprovalItem.STATUS_APPROVED,
            DGIICertificationCommercialApprovalItem.SOURCE_REJECTED: DGIICertificationCommercialApprovalItem.STATUS_REJECTED,
            DGIICertificationCommercialApprovalItem.SOURCE_PENDING: DGIICertificationCommercialApprovalItem.STATUS_PENDING,
        }.get(source_status, DGIICertificationCommercialApprovalItem.STATUS_UNKNOWN)

    def _match_local_document(self, company, parsed):
        encf = parsed['encf']
        matches = []
        certification_documents = list(
            DGIICertificationDocument.objects
            .select_related('item', 'plan')
            .filter(company=company, encf=encf)
            .order_by('-plan__imported_at', '-id')[:2]
        )
        if len(certification_documents) == 1:
            document = certification_documents[0]
            return self._match_result(
                'dgii_certification_document',
                document.id,
                document.item.amount,
                document.item.receiver_rnc,
                parsed,
                local_issuer_rnc=(document.item.raw_data or {}).get('RNCEmisor'),
            )
        if len(certification_documents) > 1:
            return {
                'status': DGIICertificationCommercialApprovalItem.MATCH_AMBIGUOUS,
                'document_type': 'dgii_certification_document',
                'document_id': None,
                'observations': 'Más de un documento de certificación local usa este e-NCF.',
            }

        fiscal_documents = list(
            ElectronicFiscalDocument.objects
            .select_related('invoice__client', 'credit_note__origin_invoice__client')
            .filter(company=company, encf=encf)
            .order_by('-id')[:2]
        )
        matches.extend(fiscal_documents)
        if len(matches) == 1:
            document = matches[0]
            amount = document.invoice.total if document.invoice_id else document.credit_note.total
            buyer_rnc = ''
            if document.invoice_id and document.invoice.client_id:
                buyer_rnc = document.invoice.client.ruc_ci or ''
            elif document.credit_note_id and document.credit_note.origin_invoice.client_id:
                buyer_rnc = document.credit_note.origin_invoice.client.ruc_ci or ''
            return self._match_result(
                'electronic_fiscal_document',
                document.id,
                amount,
                buyer_rnc,
                parsed,
                local_issuer_rnc=getattr(document.issuer, 'rnc', ''),
            )
        if len(matches) > 1:
            return {
                'status': DGIICertificationCommercialApprovalItem.MATCH_AMBIGUOUS,
                'document_type': 'electronic_fiscal_document',
                'document_id': None,
                'observations': 'Más de un documento productivo usa este e-NCF.',
            }
        return {
            'status': DGIICertificationCommercialApprovalItem.MATCH_NOT_FOUND,
            'document_type': '',
            'document_id': None,
            'observations': 'No se encontró documento local con este e-NCF.',
        }

    def _match_result(self, document_type, document_id, local_amount, local_buyer_rnc, parsed, local_issuer_rnc=''):
        observations = []
        local_issuer = self._digits(local_issuer_rnc)
        if local_issuer and parsed['issuer_rnc'] and local_issuer != parsed['issuer_rnc']:
            observations.append(f'RNC emisor local {local_issuer} difiere de DGII {parsed["issuer_rnc"]}.')
        if local_amount is not None and parsed['total_amount'] is not None:
            if Decimal(str(local_amount)).quantize(Decimal('0.01')) != parsed['total_amount'].quantize(Decimal('0.01')):
                observations.append(f'Monto local {local_amount} difiere de DGII {parsed["total_amount"]}.')
        local_rnc = self._digits(local_buyer_rnc)
        if local_rnc and parsed['approval_receiver_rnc'] and local_rnc != parsed['approval_receiver_rnc']:
            observations.append(f'RNC comprador local {local_rnc} difiere de DGII {parsed["approval_receiver_rnc"]}.')
        return {
            'status': DGIICertificationCommercialApprovalItem.MATCH_MATCHED,
            'document_type': document_type,
            'document_id': document_id,
            'observations': ' '.join(observations),
        }

    def _record_item_events(self, plan, item, match, user):
        if item.match_status == DGIICertificationCommercialApprovalItem.MATCH_NOT_FOUND:
            DGIICertificationCommercialApprovalEvent.objects.create(
                company=plan.company,
                plan=plan,
                item=item,
                event_type=DGIICertificationCommercialApprovalEvent.EVENT_NOT_FOUND,
                message='Registro DGII sin coincidencia local.',
                payload={'encf': item.encf},
                created_by=user,
            )
        if 'Monto local' in match['observations']:
            DGIICertificationCommercialApprovalEvent.objects.create(
                company=plan.company,
                plan=plan,
                item=item,
                event_type=DGIICertificationCommercialApprovalEvent.EVENT_AMOUNT_MISMATCH,
                message='Diferencia entre monto local y monto DGII.',
                payload={'encf': item.encf, 'observations': match['observations']},
                created_by=user,
            )
        if 'RNC comprador local' in match['observations'] or 'RNC emisor local' in match['observations']:
            DGIICertificationCommercialApprovalEvent.objects.create(
                company=plan.company,
                plan=plan,
                item=item,
                event_type=DGIICertificationCommercialApprovalEvent.EVENT_RNC_MISMATCH,
                message='Diferencia entre RNC local y RNC DGII.',
                payload={'encf': item.encf, 'observations': match['observations']},
                created_by=user,
            )

    def _record_structure_error(self, company, user, message, payload):
        DGIICertificationCommercialApprovalEvent.objects.create(
            company=company,
            event_type=DGIICertificationCommercialApprovalEvent.EVENT_STRUCTURE_ERROR,
            message=message,
            payload=payload,
            created_by=user,
        )

    def _summary(self, plan, errors):
        raw_summary = plan.raw_summary or {}
        return {
            'plan_id': plan.id,
            'source_filename': plan.source_filename,
            'total': plan.total_records,
            'approved': plan.approved_count,
            'rejected': plan.rejected_count,
            'pending': plan.pending_count,
            'matched': raw_summary.get('matched', 0),
            'not_found': raw_summary.get('not_found', 0),
            'ambiguous': raw_summary.get('ambiguous', 0),
            'errors': errors,
        }

    def _parse_decimal(self, value):
        if value in (None, ''):
            return None
        try:
            return Decimal(str(value).replace(',', '')).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError) as exc:
            raise DGIICertificationCommercialApprovalImportError(f'MontoTotal inválido: {value}') from exc

    def _parse_date(self, value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(str(value).strip(), fmt).date()
            except ValueError:
                continue
        raise DGIICertificationCommercialApprovalImportError(f'FechaEmision inválida: {value}')

    def _parse_datetime(self, value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, date):
            parsed = datetime.combine(value, time.min)
        else:
            parsed = None
            for fmt in ('%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y'):
                try:
                    parsed = datetime.strptime(str(value).strip(), fmt)
                    break
                except ValueError:
                    continue
            if parsed is None:
                raise DGIICertificationCommercialApprovalImportError(f'FechaHoraAprobacionComercial inválida: {value}')
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _json_value(self, value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        return value

    def _clean_header(self, value):
        return str(value or '').strip()

    def _normalize_text(self, value):
        return str(value or '').strip().lower()

    def _digits(self, value):
        return ''.join(ch for ch in str(value or '') if ch.isdigit())

    def _bytes_file(self, data):
        from io import BytesIO

        return BytesIO(data)


class DGIICertificationCommercialApprovalSubmitter:
    """Prepare and submit commercial approvals only when the official contract exists locally."""

    contract_dir = Path(__file__).resolve().parents[1] / 'ecf' / 'schemas' / 'commercial_approval'
    xsd_filename = 'AprobacionComercial.xsd'

    def run(self, *, plan: DGIICertificationCommercialApprovalPlan, user=None) -> dict:
        missing_contract = self._missing_contract_message()
        if missing_contract:
            self._mark_pending_items_failed(plan, missing_contract)
            DGIICertificationCommercialApprovalEvent.objects.create(
                company=plan.company,
                plan=plan,
                event_type=DGIICertificationCommercialApprovalEvent.EVENT_STRUCTURE_ERROR,
                message=missing_contract,
                payload={'contract_dir': str(self.contract_dir), 'xsd': self.xsd_filename},
                created_by=user,
            )
            return {
                'failed': True,
                'detail': missing_contract,
                'generated': 0,
                'signed': 0,
                'submitted': 0,
                'accepted': 0,
                'rejected': 0,
            }
        return {
            'failed': True,
            'detail': 'Contrato oficial encontrado, pero el generador de Aprobación Comercial queda pendiente de implementación controlada.',
            'generated': 0,
            'signed': 0,
            'submitted': 0,
            'accepted': 0,
            'rejected': 0,
        }

    def _missing_contract_message(self):
        xsd_path = self.contract_dir / self.xsd_filename
        examples = list(self.contract_dir.glob('*.xml')) if self.contract_dir.exists() else []
        if not xsd_path.exists() and not examples:
            return 'No se puede enviar Aprobación Comercial hasta cargar XSD/ejemplo oficial de DGII.'
        return ''

    def _mark_pending_items_failed(self, plan, message):
        plan.items.filter(
            source_approval_status=DGIICertificationCommercialApprovalItem.SOURCE_APPROVED,
            submission_status__in=[
                DGIICertificationCommercialApprovalItem.SUBMISSION_PENDING,
                DGIICertificationCommercialApprovalItem.SUBMISSION_GENERATED,
                DGIICertificationCommercialApprovalItem.SUBMISSION_SIGNED,
                DGIICertificationCommercialApprovalItem.SUBMISSION_FAILED,
            ],
        ).update(
            submission_status=DGIICertificationCommercialApprovalItem.SUBMISSION_FAILED,
            submission_error=message,
            updated_at=timezone.now(),
        )
