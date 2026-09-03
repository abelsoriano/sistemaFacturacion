"""DGII certification Excel import and scenario planning."""

from __future__ import annotations

import hashlib
import copy
import json
import logging
import re
import unicodedata
from uuid import uuid4
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import DataError, transaction
from django.utils import timezone

from facturacion.ecf.constants import PAYMENT_METHOD_TO_DGII, should_include_buyer
from facturacion.ecf.certificates.loader import PKCS12CertificateLoader
from facturacion.ecf.certificates.resolver import resolve_certificate_credentials
from facturacion.ecf.exceptions import ECFError, ECFValidationError, UnsupportedECFTypeError
from facturacion.ecf.rest.clients import DGIIRESTClient, DGIIRESTHTTPError
from facturacion.ecf.rest.environments import DGIIRESTEnvironmentResolver
from facturacion.ecf.rfce_contract import RFCE_CONTRACT_MISSING_MESSAGE, has_rfce_contract
from facturacion.ecf.soap.parsers.dgii import DGIISOAPResponseParser
from facturacion.ecf.mappers.invoice_mapper import ECFPayload
from facturacion.ecf.services.certificate_policy import ECFCertificateSigningPolicy
from facturacion.ecf.utils.dates import format_dgii_date, format_dgii_datetime
from facturacion.ecf.utils.decimals import quantize_money
from facturacion.ecf.utils.text import clean_text, dgii_location_code, dgii_phone, digits_only
from facturacion.ecf.signer.xml_signer import ECFXMLSigner
from facturacion.ecf.validators.signature import ECFSignatureValidator
from facturacion.ecf.validators.xsd import ECFXSDValidator
from facturacion.ecf.xml.builders.factory import ECFBuilderFactory
from facturacion.ecf.xml.render import render_xml
from facturacion.models import (
    Company,
    CompanyMembership,
    DGIICertificationDocument,
    DGIICertificationEvent,
    DGIICertificationItem,
    DGIICertificationPlan,
    ECFIssuerConfig,
    ECFSequence,
)
from facturacion.services.certification_locking import (
    CertificationArtifactChanged,
    CertificationDocumentNotFound,
    CertificationLockService,
    CertificationLockedScope,
    CertificationMutationBlocked,
)
from facturacion.services.certification_reset import CertificationResetService


logger = logging.getLogger(__name__)
MAX_AMOUNT_ABS = Decimal('999999999999.99')
SUPPORTED_ECF_TYPES = {'31', '32', '33', '34', '41', '43', '44', '45', '46', '47', 'RFCE'}
CERTIFICATION_XML_SUPPORTED_TYPES = {'31', '32', '33', '34', '41', '43', '44', '45', '46', '47'}
CERTIFICATION_DOCUMENT_GROUP1_TYPES = {'31', '32', '41', '43', '44', '45', '46', '47'}
DGII_CERTIFICATION_DEFAULT_BUYER_RNC = '131880681'
DGII_CERTIFICATION_DEFAULT_BUYER_NAME = 'DOCUMENTOS ELECTRONICOS DE 03'
DGII_CERTIFICATION_REJECTED_INTERNAL_INVOICE = 'AA0000000100000000010000000002000000000300000000050000000006'
DGII_CERTIFICATION_RETRY_ENCFS = {
    'E320000000004',
    'E410000000010',
    'E410000000007',
    'E450000000003',
}
DGII_CERTIFICATION_ITEM_REFERENCE_TYPES = {'31', '32', '33', '34', '45'}
DGII_CERTIFICATION_ITEM_DATE_TYPES = {'31', '32', '33', '34', '41', '44', '45', '46'}
DGII_CERTIFICATION_ITEM_SUBDISCOUNT_TYPES = {'31', '32', '33', '34', '41', '44', '45', '46'}

DGII_ECF_COLUMN_ALIASES = {
    'TipoeCF': 'col_3',
    'ENCF': 'col_4',
    'FechaVencimientoSecuencia': 'col_5',
    'IndicadorNotaCredito': 'col_6',
    'IndicadorEnvioDiferido': 'col_7',
    'IndicadorMontoGravado': 'col_8',
    'TipoIngresos': 'col_9',
    'TipoPago': 'col_10',
    'FechaLimitePago': 'col_11',
    'TerminoPago': 'col_12',
    'RNCEmisor': 'col_33',
    'RazonSocialEmisor': 'col_34',
    'NombreComercial': 'col_35',
    'DireccionEmisor': 'col_37',
    'Municipio': 'col_38',
    'Provincia': 'col_39',
    'CorreoEmisor': 'col_43',
    'WebSite': 'col_44',
    'ActividadEconomica': 'col_45',
    'CodigoVendedor': 'col_45',
    'NumeroFacturaInterna': 'col_46',
    'NumeroPedidoInterno': 'col_48',
    'ZonaVenta': 'col_49',
    'RutaVenta': 'col_50',
    'FechaEmision': 'col_52',
    'RNCComprador': 'col_53',
    'RNCCompradorAlt': 'col_54',
    'RazonSocialComprador': 'col_55',
    'ContactoComprador': 'col_56',
    'CorreoComprador': 'col_57',
    'DireccionComprador': 'col_58',
    'MunicipioComprador': 'col_59',
    'ProvinciaComprador': 'col_60',
    'FechaEntrega': 'col_61',
    'ContactoEntrega': 'col_62',
    'DireccionEntrega': 'col_63',
    'TelefonoAdicional': 'col_64',
    'FechaOrdenCompra': 'col_65',
    'NumeroOrdenCompra': 'col_66',
    'CodigoInternoComprador': 'col_67',
    'MontoGravadoTotal': 'col_107',
    'MontoGravadoI1': 'col_108',
    'MontoGravadoI2': 'col_109',
    'MontoGravadoI3': 'col_110',
    'MontoExento': 'col_111',
    'ITBIS1': 'col_112',
    'ITBIS2': 'col_113',
    'ITBIS3': 'col_114',
    'TotalITBIS': 'col_115',
    'TotalITBIS1': 'col_116',
    'TotalITBIS2': 'col_117',
    'TotalITBIS3': 'col_118',
    'MontoImpuestoAdicional': 'col_119',
    'MontoTotal': 'col_140',
    'MontoPeriodo': 'col_145',
    'ValorPagar': 'col_146',
    'TotalITBISRetenido': 'col_148',
    'TotalISRRetencion': 'col_149',
}
ENCF_RE = re.compile(r'\bE(31|32|33|34|41|43|44|45|46|47)\d{6,12}\b', re.IGNORECASE)
ENCF_FRAGMENT_RE = re.compile(r'E(31|32|33|34|41|43|44|45|46|47)\d{6,12}', re.IGNORECASE)
RNC_RE = re.compile(r'\b\d{3}-?\d{5}-?\d{1}\b|\b\d{3}-?\d{7}-?\d{1}\b')


TYPE_TEXT_HINTS = {
    '31': ['factura credito fiscal', 'credito fiscal', 'e31'],
    '32': ['factura consumo', 'consumo', 'e32'],
    '33': ['nota debito', 'debito', 'e33'],
    '34': ['nota credito', 'credito', 'e34'],
    '41': ['compras', 'compra', 'e41'],
    '43': ['gastos menores', 'gasto menor', 'e43'],
    '44': ['regimenes especiales', 'regimen especial', 'e44'],
    '45': ['gubernamental', 'gobierno', 'e45'],
    '46': ['exportaciones', 'exportacion', 'e46'],
    '47': ['pagos exterior', 'pago exterior', 'e47'],
    'RFCE': ['rfce', 'resumen factura consumo', 'resumen facturas consumo'],
}

HEADER_HINTS = {
    'encf': ['encf', 'e-ncf'],
    'amount': ['monto', 'total', 'valor', 'importe'],
    'receiver_rnc': ['rnc receptor', 'rncreceptor', 'rnc comprador', 'rnccomprador', 'rnc cliente', 'rnccliente'],
    'receiver_name': ['nombre receptor', 'nombrereceptor', 'razon social receptor', 'razonsocialreceptor', 'razon social comprador', 'razonsocialcomprador', 'cliente'],
    'observations': ['observacion', 'observaciones', 'comentario', 'nota'],
    'document_type': ['tipo comprobante', 'tipocomprobante', 'tipoecf', 'tipo e-cf', 'tipo ecf'],
    'dgii_group': ['grupo dgii', 'grupo'],
}


@dataclass(frozen=True)
class DetectedCertificationItem:
    ecf_type: str
    dgii_group: int
    encf: str
    document_type: str
    amount: Decimal | None
    receiver_rnc: str
    receiver_name: str
    observations: str
    source_sheet: str
    source_row: int
    raw_data: dict


class DGIICertificationExcelImporter:
    """Import the DGII certification workbook into a tenant-scoped plan."""

    max_size_bytes = 5 * 1024 * 1024

    def import_workbook(self, *, uploaded_file, company: Company, user=None) -> DGIICertificationPlan:
        filename = uploaded_file.name or 'set-dgii.xlsx'
        suffix = Path(filename).suffix.lower()
        content = uploaded_file.read()

        if not content:
            raise ValueError('Debe cargar el Excel entregado por DGII.')
        if len(content) > self.max_size_bytes:
            raise ValueError('El Excel DGII no puede exceder 5 MB.')
        if suffix not in {'.xlsx', '.xls'}:
            raise ValueError('El archivo debe ser .xlsx o .xls.')

        try:
            detected_items = self._detect_items(content, suffix)
        except Exception as exc:
            DGIICertificationEvent.objects.create(
                company=company,
                event_type=DGIICertificationEvent.EVENT_IMPORT_ERROR,
                message='No fue posible analizar el Excel DGII.',
                payload={'filename': filename, 'error': str(exc)},
                created_by=user,
            )
            raise ValueError(f'No fue posible analizar el Excel DGII: {exc}') from exc

        if not detected_items:
            DGIICertificationEvent.objects.create(
                company=company,
                event_type=DGIICertificationEvent.EVENT_IMPORT_ERROR,
                message='No se detectaron escenarios e-CF en el Excel DGII.',
                payload={'filename': filename},
                created_by=user,
            )
            raise ValueError('No se detectaron escenarios e-CF en el Excel DGII.')

        file_hash = hashlib.sha256(content).hexdigest()
        group_counts = self._group_counts(detected_items)

        try:
            with transaction.atomic():
                plan = DGIICertificationPlan.objects.create(
                    company=company,
                    source_filename=filename,
                    file_sha256=file_hash,
                    imported_by=user,
                    total_items=len(detected_items),
                    group_counts=group_counts,
                )
                DGIICertificationEvent.objects.create(
                    company=company,
                    plan=plan,
                    event_type=DGIICertificationEvent.EVENT_EXCEL_IMPORTED,
                    message='Excel DGII importado.',
                    payload={'filename': filename, 'sha256': file_hash, 'items': len(detected_items)},
                    created_by=user,
                )
                DGIICertificationEvent.objects.create(
                    company=company,
                    plan=plan,
                    event_type=DGIICertificationEvent.EVENT_PLAN_CREATED,
                    message='Plan de certificacion DGII creado.',
                    payload={'group_counts': group_counts},
                    created_by=user,
                )

                item_objects = []
                for detected in detected_items:
                    self._validate_detected_item(detected)
                    logger.info(
                        "DGII certification item detected before persistence",
                        extra={
                            "sheet_name": detected.source_sheet,
                            "row_number": detected.source_row,
                            "document_type": detected.document_type,
                            "encf": detected.encf,
                            "amount": str(detected.amount) if detected.amount is not None else None,
                            "rnc": detected.receiver_rnc,
                            "customer_name": detected.receiver_name,
                            "group_number": detected.dgii_group,
                        },
                    )
                    item = DGIICertificationItem.objects.create(
                        plan=plan,
                        company=company,
                        ecf_type=detected.ecf_type,
                        dgii_group=detected.dgii_group,
                        encf=detected.encf,
                        document_type=detected.document_type,
                        amount=detected.amount,
                        receiver_rnc=detected.receiver_rnc,
                        receiver_name=detected.receiver_name,
                        observations=detected.observations,
                        source_sheet=detected.source_sheet,
                        source_row=detected.source_row,
                        raw_data=detected.raw_data,
                    )
                    item_objects.append(item)
                    DGIICertificationEvent.objects.create(
                        company=company,
                        plan=plan,
                        item=item,
                        event_type=DGIICertificationEvent.EVENT_ITEM_DETECTED,
                        message=f'Item DGII detectado: {detected.ecf_type}.',
                        payload={
                            'ecf_type': detected.ecf_type,
                            'dgii_group': detected.dgii_group,
                            'sheet': detected.source_sheet,
                            'row': detected.source_row,
                        },
                        created_by=user,
                    )
        except (DataError, ValueError, InvalidOperation) as exc:
            DGIICertificationEvent.objects.create(
                company=company,
                event_type=DGIICertificationEvent.EVENT_IMPORT_ERROR,
                message='No se pudo importar el Excel DGII.',
                payload={'filename': filename, 'error': str(exc)},
                created_by=user,
            )
            raise ValueError(str(exc)) from exc

        return plan

    def _validate_detected_item(self, detected: DetectedCertificationItem) -> None:
        if detected.amount is None:
            return
        if abs(detected.amount) > MAX_AMOUNT_ABS:
            raise ValueError(
                "Monto fuera de rango para plan DGII "
                f"(hoja={detected.source_sheet}, fila={detected.source_row}, "
                f"valor={detected.amount}, campo=amount)."
            )

    def _detect_items(self, content: bytes, suffix: str) -> list[DetectedCertificationItem]:
        if suffix == '.xls':
            return self._detect_xls_items(content)
        return self._detect_xlsx_items(content)

    def _detect_xlsx_items(self, content: bytes) -> list[DetectedCertificationItem]:
        from io import BytesIO

        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
        detected: list[DetectedCertificationItem] = []
        seen_sources: set[tuple[str, int]] = set()

        for worksheet in workbook.worksheets:
            header_map: dict[int, str] = {}
            header_names: list[str] = []
            for row_number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
                values = list(row or [])
                normalized_values = [_normalize_text(value) for value in values]
                maybe_headers = self._header_map(normalized_values)
                if len(maybe_headers) >= 2 and not self._row_has_ecf_signal(values, normalized_values):
                    header_map = maybe_headers
                    header_names = [str(value or '').strip() for value in values]
                    continue

                item = self._detect_row(
                    values=values,
                    normalized_values=normalized_values,
                    header_map=header_map,
                    header_names=header_names,
                    sheet_name=worksheet.title,
                    row_number=row_number,
                )
                if item and (item.source_sheet, item.source_row) not in seen_sources:
                    detected.append(item)
                    seen_sources.add((item.source_sheet, item.source_row))

        return detected

    def _detect_xls_items(self, _content: bytes) -> list[DetectedCertificationItem]:
        try:
            import xlrd  # type: ignore
        except ImportError as exc:
            raise ValueError('Los archivos .xls requieren xlrd instalado; convierta el set DGII a .xlsx.') from exc

        raise ValueError('El motor .xls legacy no esta habilitado para este importador.')

    def _detect_row(
        self,
        *,
        values: list,
        normalized_values: list[str],
        header_map: dict[int, str],
        header_names: list[str],
        sheet_name: str,
        row_number: int,
    ) -> DetectedCertificationItem | None:
        row_text = ' '.join(value for value in normalized_values if value)
        if not row_text:
            return None

        field_values = self._field_values(values, normalized_values, header_map)
        encf = field_values.get('encf') or self._extract_encf(row_text)
        ecf_type = self._detect_ecf_type(row_text, encf, sheet_name, field_values.get('document_type', ''))
        if ecf_type not in SUPPORTED_ECF_TYPES:
            return None

        amount = self._extract_amount(values, normalized_values, header_map, field_values)
        receiver_rnc = field_values.get('receiver_rnc') or self._extract_rnc(row_text, encf)
        receiver_name = _clean_receiver_name(field_values.get('receiver_name')) or self._extract_name(values, normalized_values, header_map)
        observations = field_values.get('observations') or ''
        document_type = field_values.get('document_type') or self._document_type_label(ecf_type)
        dgii_group = self._classify_group(ecf_type, amount)
        raw_data = {
            f'col_{index + 1}': self._serialize_cell(value)
            for index, value in enumerate(values)
            if value not in (None, '')
        }
        for index, field in header_map.items():
            if index >= len(values) or values[index] in (None, ''):
                continue
            raw_data[field] = self._serialize_cell(values[index])
        for index, value in enumerate(values):
            if value in (None, ''):
                continue
            if index < len(header_names):
                header = header_names[index]
                if header:
                    raw_data.setdefault(header, self._serialize_cell(value))

        return DetectedCertificationItem(
            ecf_type=ecf_type,
            dgii_group=dgii_group,
            encf=encf,
            document_type=document_type,
            amount=amount,
            receiver_rnc=receiver_rnc,
            receiver_name=receiver_name,
            observations=observations,
            source_sheet=sheet_name,
            source_row=row_number,
            raw_data=raw_data,
        )

    def _header_map(self, normalized_values: list[str]) -> dict[int, str]:
        headers: dict[int, str] = {}
        for index, value in enumerate(normalized_values):
            if not value:
                continue
            for field, hints in HEADER_HINTS.items():
                if any(hint in value for hint in hints):
                    headers[index] = field
                    break
        return headers

    def _row_has_ecf_signal(self, values: list, normalized_values: list[str]) -> bool:
        corpus = ' '.join(value for value in normalized_values if value)
        if ENCF_FRAGMENT_RE.search(corpus.upper()):
            return True
        return any(value.strip().upper() == 'RFCE' for value in normalized_values) or any(
            str(value).strip() in {'31', '32', '33', '34', '41', '43', '44', '45', '46', '47'}
            for value in values
            if value is not None
        )

    def _field_values(self, values: list, normalized_values: list[str], header_map: dict[int, str]) -> dict[str, str]:
        fields: dict[str, str] = {}
        for index, field in header_map.items():
            if index >= len(values):
                continue
            value = values[index]
            if value in (None, ''):
                continue
            text = str(value).strip()
            if field == 'receiver_rnc':
                text = _normalize_digits(text)
            elif field == 'encf':
                extracted = self._extract_encf(_normalize_text(text))
                if not extracted or field in fields:
                    continue
                text = extracted
            elif field == 'amount':
                continue
            elif field in fields:
                continue
            fields[field] = text
        return fields

    def _detect_ecf_type(self, row_text: str, encf: str, sheet_name: str, document_type: str) -> str | None:
        if self._is_rfce_context(row_text, sheet_name, document_type):
            return 'RFCE'

        if encf:
            match = ENCF_FRAGMENT_RE.search(encf)
            if match:
                return match.group(1)

        corpus = f'{row_text} {_normalize_text(sheet_name)} {_normalize_text(document_type)}'
        for ecf_type, hints in TYPE_TEXT_HINTS.items():
            if any(hint in corpus for hint in hints):
                return ecf_type
        return None

    def _extract_encf(self, text: str) -> str:
        match = ENCF_FRAGMENT_RE.search(text.upper())
        return match.group(0).upper() if match else ''

    def _extract_rnc(self, row_text: str, encf: str) -> str:
        for match in RNC_RE.finditer(row_text):
            digits = _normalize_digits(match.group(0))
            if len(digits) in {9, 11} and digits not in encf:
                return digits
        return ''

    def _extract_amount(self, values: list, normalized_values: list[str], header_map: dict[int, str], field_values: dict[str, str]) -> Decimal | None:
        amount_indexes = [index for index, field in header_map.items() if field == 'amount']
        header_candidates = []
        for index in amount_indexes:
            if index < len(values):
                parsed = _parse_decimal(values[index])
                if parsed is not None:
                    header_candidates.append(parsed)
        if header_candidates:
            return max(header_candidates)

        candidates = [
            parsed
            for value, normalized in zip(values, normalized_values)
            if not ENCF_FRAGMENT_RE.search(normalized.upper())
            for parsed in [_parse_decimal(value)]
            if parsed is not None
        ]
        return max(candidates) if candidates else None

    def _extract_name(self, values: list, normalized_values: list[str], header_map: dict[int, str]) -> str:
        used_header_indexes = set(header_map.keys())
        for index, value in enumerate(values):
            if index in used_header_indexes or value in (None, ''):
                continue
            text = str(value).strip()
            normalized = normalized_values[index]
            text = _clean_receiver_name(text)
            if not text:
                continue
            normalized = _normalize_text(text)
            if ENCF_FRAGMENT_RE.search(normalized.upper()) or RNC_RE.search(normalized):
                continue
            if _parse_decimal(value) is not None:
                continue
            if any(hint in normalized for hints in TYPE_TEXT_HINTS.values() for hint in hints):
                continue
            return text[:180]
        return ''

    def _is_rfce_context(self, row_text: str, sheet_name: str, document_type: str) -> bool:
        corpus = f'{_normalize_text(sheet_name)} {row_text} {_normalize_text(document_type)}'
        return any(hint in corpus for hint in TYPE_TEXT_HINTS['RFCE'])

    def _classify_group(self, ecf_type: str, amount: Decimal | None) -> int:
        if ecf_type in {'31', '41', '43', '44', '45', '46', '47'}:
            return 1
        if ecf_type == '32':
            if amount is not None and amount < Decimal('250000'):
                return 4
            return 1
        if ecf_type in {'33', '34'}:
            return 2
        if ecf_type == 'RFCE':
            return 3
        return 1

    def _group_counts(self, items: list[DetectedCertificationItem]) -> dict:
        counts = {'1': 0, '2': 0, '3': 0, '4': 0}
        for item in items:
            counts[str(item.dgii_group)] = counts.get(str(item.dgii_group), 0) + 1
        return counts

    def _document_type_label(self, ecf_type: str) -> str:
        return dict(DGIICertificationItem.ECF_TYPE_CHOICES).get(ecf_type, ecf_type)

    def _serialize_cell(self, value):
        if isinstance(value, Decimal):
            return str(value)
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return value


def _normalize_text(value) -> str:
    if value is None:
        return ''
    text = str(value).strip().lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', text)


def _normalize_digits(value) -> str:
    return re.sub(r'\D+', '', str(value or ''))


def _clean_receiver_name(value) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    normalized = _normalize_text(text)
    if normalized in {'#e', 'e', 'n/a', 'na', 'null', 'none', 'no aplica'}:
        return ''
    if len(normalized) < 3:
        return ''
    if not re.search(r'[A-Za-z]', text):
        return ''
    alpha_count = sum(1 for char in normalized if char.isalpha())
    if alpha_count < 3:
        return ''
    return text


def _parse_decimal(value) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            return None

    text = str(value).strip()
    if not re.search(r'\d', text):
        return None
    if re.search(r'[A-Za-z]', text):
        return None
    cleaned = re.sub(r'[^\d,.\-]', '', text)
    if cleaned.count(',') == 1 and cleaned.count('.') > 1:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif cleaned.count(',') == 1 and cleaned.count('.') == 0:
        cleaned = cleaned.replace(',', '.')
    else:
        cleaned = cleaned.replace(',', '')
    try:
        return Decimal(cleaned).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return None


class DGIICertificationXMLGenerator:
    """Build isolated DGII certification scenarios without touching productive fiscal flows."""

    unsupported_rfce_message = 'Generador RFCE pendiente de implementación'

    def generate_item(self, *, item: DGIICertificationItem, user=None) -> DGIICertificationItem:
        if item.ecf_type == 'RFCE':
            return self._mark_generation_error(item=item, user=user, error=self.unsupported_rfce_message)
        if item.ecf_type not in CERTIFICATION_XML_SUPPORTED_TYPES:
            return self._mark_generation_error(
                item=item,
                user=user,
                error=f'Generador no disponible para tipo {item.ecf_type}.',
            )

        xml_content = self._build_xml(item)
        encoded = xml_content.encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()
        filename = self._filename_for(item)
        storage_path = default_storage.save(filename, ContentFile(encoded))

        item.generated_xml_path = storage_path
        item.generated_xml_hash = digest
        item.generated_at = timezone.now()
        item.generation_error = ''
        item.status = DGIICertificationItem.STATUS_GENERATED
        item.save(update_fields=[
            'generated_xml_path',
            'generated_xml_hash',
            'generated_at',
            'generation_error',
            'status',
            'updated_at',
        ])
        DGIICertificationEvent.objects.create(
            company=item.company,
            plan=item.plan,
            item=item,
            event_type=DGIICertificationEvent.EVENT_XML_GENERATED,
            message='Escenario de certificacion DGII generado.',
            payload={
                'ecf_type': item.ecf_type,
                'dgii_group': item.dgii_group,
                'path': storage_path,
                'sha256': digest,
            },
            created_by=user,
        )
        return item

    def generate_group(self, *, plan: DGIICertificationPlan, group_number: int, user=None) -> dict:
        queryset = plan.items.filter(dgii_group=group_number, status=DGIICertificationItem.STATUS_PENDING).order_by(
            'source_sheet',
            'source_row',
        )
        generated = 0
        failed = 0
        errors = []
        for item in queryset:
            updated_item = self.generate_item(item=item, user=user)
            if updated_item.status == DGIICertificationItem.STATUS_GENERATED:
                generated += 1
            else:
                failed += 1
                errors.append({
                    'item_id': item.id,
                    'ecf_type': item.ecf_type,
                    'source_sheet': item.source_sheet,
                    'source_row': item.source_row,
                    'error': updated_item.generation_error,
                })
        return {'generated': generated, 'failed': failed, 'errors': errors}

    def _mark_generation_error(self, *, item: DGIICertificationItem, user=None, error: str) -> DGIICertificationItem:
        item.status = DGIICertificationItem.STATUS_GENERATION_ERROR
        item.generation_error = error
        item.save(update_fields=['status', 'generation_error', 'updated_at'])
        DGIICertificationEvent.objects.create(
            company=item.company,
            plan=item.plan,
            item=item,
            event_type=DGIICertificationEvent.EVENT_XML_GENERATION_ERROR,
            message=error,
            payload={'ecf_type': item.ecf_type, 'dgii_group': item.dgii_group},
            created_by=user,
        )
        return item

    def _build_xml(self, item: DGIICertificationItem) -> str:
        root = ET.Element('EscenarioCertificacionDGII')
        self._set_text(root, 'ecf_type', item.ecf_type)
        self._set_text(root, 'encf', item.encf)
        if item.amount is not None:
            self._set_text(root, 'amount', f'{item.amount:.2f}')
        self._set_text(root, 'receiver_rnc', item.receiver_rnc)
        self._set_text(root, 'receiver_name', item.receiver_name)
        self._set_text(root, 'observations', item.observations)
        self._set_text(root, 'group_number', str(item.dgii_group))
        self._set_text(root, 'source_sheet', item.source_sheet)
        self._set_text(root, 'source_row', str(item.source_row))

        ET.indent(root, space='  ')
        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    def _set_text(self, parent, tag: str, value) -> None:
        cleaned = _clean_scenario_value(value)
        if not cleaned:
            return
        element = ET.SubElement(parent, tag)
        element.text = cleaned

    def _filename_for(self, item: DGIICertificationItem) -> str:
        encf = item.encf or f'fila-{item.source_row}'
        return (
            f'dgii_certification/company-{item.company_id}/plan-{item.plan_id}/'
            f'grupo-{item.dgii_group}/{item.ecf_type}-{encf}-item-{item.id}.xml'
        )


class CertificationDocumentImmutableError(CertificationMutationBlocked):
    """Raised when a generated or signed certification artifact is immutable."""


class CertificationGenerationAttemptFailed(Exception):
    """A regeneration failed while the previously published version was preserved."""


@dataclass(frozen=True)
class CertificationDocumentFence:
    plan_id: int
    company_id: int
    item_id: int
    document_id: int | None
    expected_document_absent: bool
    status: str = ''
    xml_content: str = ''
    xml_hash: str = ''
    signed_xml_path: str = ''
    signed_xml_hash: str = ''
    signed_at: object = None
    submission_outcome: str = DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED


@dataclass(frozen=True)
class CertificationArtifactFence:
    plan_id: int
    company_id: int
    item_id: int
    document_id: int
    xml_hash: str
    signed_xml_path: str
    signed_xml_hash: str
    signed_at: object


@dataclass(frozen=True)
class PreparedCertificationDocument:
    target_fence: CertificationDocumentFence
    item_snapshot: DGIICertificationItem
    xml_content: str
    xml_hash: str
    generated_at: object
    dependency_fences: tuple[CertificationArtifactFence, ...] = ()


@dataclass(frozen=True)
class PreparedCertificationSignature:
    prepared_document: PreparedCertificationDocument
    storage_path: str
    signed_xml_hash: str
    policy_code: str
    warnings: tuple


class DGIICertificationDocumentGenerator:
    """Generate isolated e-CF XML documents for DGII certification scenarios."""

    mutable_statuses = {
        DGIICertificationDocument.STATUS_PENDING,
        DGIICertificationDocument.STATUS_GENERATED,
        DGIICertificationDocument.STATUS_GENERATION_ERROR,
        DGIICertificationDocument.STATUS_SIGNING_ERROR,
    }

    def __init__(
        self,
        builder_factory: ECFBuilderFactory | None = None,
        lock_service: CertificationLockService | None = None,
    ) -> None:
        self.builder_factory = builder_factory or ECFBuilderFactory()
        self.lock_service = lock_service or CertificationLockService()

    def generate_item(self, *, item: DGIICertificationItem, user=None) -> DGIICertificationDocument:
        item_id = item.pk
        plan_id = item.plan_id
        result = None
        pending_error = None
        try:
            with transaction.atomic():
                plan = self.lock_service.lock_plan(plan_id=plan_id)
                scope, target_item_ids = self._lock_generation_scope(plan, [item_id])
                locked_item = scope.item(item_id)
                document = self._document_for_item_or_none(scope, item_id)
                previous_version = self._published_version_snapshot(document, locked_item)
                try:
                    self.assert_generation_mutable(document)
                except (CertificationDocumentImmutableError, CertificationMutationBlocked) as exc:
                    self._record_generation_failure(
                        item=locked_item, document=document, error=str(exc), user=user,
                        stage='certification_generation_blocked', rolled_back=False,
                    )
                    pending_error = exc
                else:
                    try:
                        with transaction.atomic():
                            result = self._generate_locked_item(item=locked_item, user=user)
                    except (UnsupportedECFTypeError, ValueError) as exc:
                        result, should_raise = self._mark_generation_error(
                            item=locked_item,
                            user=user,
                            error=str(exc),
                            previous_version=previous_version,
                        )
                        if should_raise:
                            pending_error = CertificationGenerationAttemptFailed(str(exc))
        except Exception as exc:
            if pending_error is not exc:
                self._persist_unexpected_generation_failure(
                    plan_id=plan_id, item_ids=[item_id], error=exc, user=user
                )
            raise
        if pending_error is not None:
            raise pending_error
        return result

    def has_dgii_delivery_evidence(self, document: DGIICertificationDocument) -> bool:
        """Only fields written as evidence of a remote DGII exchange count here."""
        return bool(
            document.dgii_track_id
            or document.submitted_at
            or document.accepted_at
            or document.rejected_at
        )

    def assert_generation_mutable(self, document: DGIICertificationDocument | None) -> None:
        if document is None:
            return
        if document.submission_outcome != DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED:
            raise CertificationMutationBlocked(
                f'{document.encf or document.pk}: submission_outcome={document.submission_outcome} bloquea regeneración.'
            )
        if self.has_dgii_delivery_evidence(document):
            raise CertificationDocumentImmutableError(
                f'{document.encf or document.pk}: existe evidencia de entrega DGII.'
            )
        if document.signed_xml_path or document.signed_xml_hash or document.signed_at:
            raise CertificationDocumentImmutableError(
                f'{document.encf or document.pk}: existe evidencia de artefacto firmado.'
            )
        if document.status == DGIICertificationDocument.STATUS_SIGNED:
            raise CertificationDocumentImmutableError(
                f'{document.encf or document.pk}: un documento firmado no puede regenerarse.'
            )
        if document.status not in self.mutable_statuses:
            raise CertificationDocumentImmutableError(
                f'{document.encf or document.pk}: status={document.status} no permite regeneración.'
            )

    def _generate_locked_item(self, *, item: DGIICertificationItem, user=None):
        document = self._get_or_create_document(item)
        prepared = self.prepare_item(
            item_snapshot=item,
            target_fence=self.document_fence(item=item, document=document),
        )
        xml_content = prepared.xml_content
        digest = prepared.xml_hash
        document.ecf_type = item.ecf_type
        document.encf = item.encf
        document.status = DGIICertificationDocument.STATUS_GENERATED
        document.xml_content = xml_content
        document.xml_hash = digest
        document.generated_at = timezone.now()
        document.generation_error = ''
        document.signing_error = ''
        document.accepted_stale = False
        document.stale_reason = ''
        document.stale_at = None
        document.dgii_track_id = ''
        document.dgii_status = ''
        document.dgii_response_code = ''
        document.dgii_response_message = ''
        document.submitted_at = None
        document.accepted_at = None
        document.rejected_at = None
        document.submit_error = ''
        document.save(update_fields=[
            'ecf_type', 'encf', 'status', 'xml_content', 'xml_hash', 'generated_at',
            'generation_error', 'signing_error', 'accepted_stale', 'stale_reason',
            'stale_at', 'dgii_track_id', 'dgii_status', 'dgii_response_code',
            'dgii_response_message', 'submitted_at', 'accepted_at', 'rejected_at',
            'submit_error', 'updated_at',
        ])
        item.status = DGIICertificationItem.STATUS_GENERATED
        item.generation_error = ''
        item.save(update_fields=['status', 'generation_error', 'updated_at'])
        DGIICertificationEvent.objects.create(
            company=item.company, plan=item.plan, item=item,
            event_type=DGIICertificationEvent.EVENT_XML_GENERATED,
            message='Documento e-CF de certificacion DGII generado.',
            payload={
                'certification_document_id': document.id, 'ecf_type': item.ecf_type,
                'dgii_group': item.dgii_group, 'encf': item.encf, 'sha256': digest,
                'engine': 'ECFBuilderFactory',
            },
            created_by=user,
        )
        return document

    def prepare_item(
        self,
        *,
        item_snapshot: DGIICertificationItem,
        target_fence: CertificationDocumentFence,
        dependency_fences: tuple[CertificationArtifactFence, ...] = (),
        integral_signature_value: str | None = None,
    ) -> PreparedCertificationDocument:
        """Build an e-CF in memory without publishing document state or events."""
        item = copy.deepcopy(item_snapshot)
        if not item.encf:
            raise ValueError('El escenario DGII no tiene e-NCF detectado.')
        if item.ecf_type == 'RFCE':
            xml_content = self._build_rfce_xml(
                item,
                integral_signature_value=integral_signature_value,
            )
        else:
            issuer = self._resolve_issuer(item.company)
            payload = self._build_payload(item=item, issuer=issuer)
            builder = self.builder_factory.get(item.ecf_type)
            root = builder.build(payload)
            xml_content = render_xml(root)
        digest = hashlib.sha256(xml_content.encode('utf-8')).hexdigest()
        return PreparedCertificationDocument(
            target_fence=target_fence,
            item_snapshot=item,
            xml_content=xml_content,
            xml_hash=digest,
            generated_at=timezone.now(),
            dependency_fences=tuple(dependency_fences),
        )

    @staticmethod
    def document_fence(*, item, document=None):
        if document is None:
            return CertificationDocumentFence(
                plan_id=item.plan_id, company_id=item.company_id, item_id=item.pk,
                document_id=None, expected_document_absent=True,
            )
        return CertificationDocumentFence(
            plan_id=document.plan_id, company_id=document.company_id,
            item_id=item.pk, document_id=document.pk, expected_document_absent=False,
            status=document.status, xml_hash=document.xml_hash,
            xml_content=document.xml_content,
            signed_xml_path=document.signed_xml_path,
            signed_xml_hash=document.signed_xml_hash, signed_at=document.signed_at,
            submission_outcome=document.submission_outcome,
        )

    def _build_rfce_xml(
        self,
        item: DGIICertificationItem,
        *,
        integral_signature_value: str | None = None,
    ) -> str:
        raw = item.raw_data or {}
        root = ET.Element('RFCE')
        encabezado = ET.SubElement(root, 'Encabezado')
        self._append_text(encabezado, 'Version', self._rfce_raw_value(raw, 'Version') or '1.0')
        id_doc = ET.SubElement(encabezado, 'IdDoc')
        self._append_text(id_doc, 'TipoeCF', self._rfce_type(raw))
        self._append_text(id_doc, 'eNCF', item.encf or self._rfce_raw_value(raw, 'ENCF'))
        self._append_text(id_doc, 'TipoIngresos', self._rfce_raw_value(raw, 'TipoIngresos'))
        self._append_text(id_doc, 'TipoPago', self._rfce_raw_value(raw, 'TipoPago'))

        emisor = ET.SubElement(encabezado, 'Emisor')
        self._append_text(emisor, 'RNCEmisor', self._rfce_raw_value(raw, 'RNCEmisor'))
        self._append_text(emisor, 'RazonSocialEmisor', self._rfce_raw_value(raw, 'RazonSocialEmisor'))
        self._append_text(emisor, 'FechaEmision', self._rfce_raw_value(raw, 'FechaEmision'))

        comprador = ET.SubElement(encabezado, 'Comprador')
        self._append_text(comprador, 'RNCComprador', self._rfce_raw_value(raw, 'RNCComprador'))
        self._append_text(comprador, 'IdentificadorExtranjero', self._rfce_raw_value(raw, 'IdentificadorExtranjero'))
        self._append_text(comprador, 'RazonSocialComprador', self._rfce_raw_value(raw, 'RazonSocialComprador'))

        totales = ET.SubElement(encabezado, 'Totales')
        for tag in (
            'MontoGravadoTotal',
            'MontoGravadoI1',
            'MontoGravadoI2',
            'MontoGravadoI3',
            'MontoExento',
            'TotalITBIS',
            'TotalITBIS1',
            'TotalITBIS2',
            'TotalITBIS3',
            'MontoImpuestoAdicional',
            'MontoTotal',
            'MontoNoFacturable',
            'MontoPeriodo',
        ):
            self._append_text(totales, tag, self._rfce_raw_value(raw, tag))
        security_code = (
            integral_signature_value[:6]
            if integral_signature_value is not None
            else self._rfce_security_code(raw, item)
        )
        self._append_text(encabezado, 'CodigoSeguridadeCF', security_code)

        ET.indent(root, space='  ')
        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    def _rfce_raw_value(self, raw: dict, key: str):
        return _clean_scenario_value(raw.get(key))

    def _rfce_type(self, raw: dict) -> str:
        raw_type = self._rfce_raw_value(raw, 'TipoeCF')
        return raw_type if raw_type == '32' else '32'

    def _rfce_security_code(self, raw: dict, item: DGIICertificationItem) -> str:
        signature_value = self._integral_invoice_signature_value(item)
        return signature_value[:6]

    def _integral_invoice_signature_value(self, item: DGIICertificationItem) -> str:
        if not item.encf:
            raise ValueError('El RFCE no tiene e-NCF para vincular la factura íntegra firmada.')
        try:
            source_document = DGIICertificationDocument.objects.select_related('item').get(
                plan=item.plan,
                company=item.company,
                item__dgii_group=4,
                encf=item.encf,
            )
        except DGIICertificationDocument.DoesNotExist as exc:
            raise ValueError(
                f'{item.encf}: no existe XML íntegro firmado del grupo 4 para derivar CodigoSeguridadeCF.'
            ) from exc
        if not source_document.signed_xml_path or not default_storage.exists(source_document.signed_xml_path):
            raise ValueError(
                f'{item.encf}: el XML íntegro firmado del grupo 4 no está disponible para derivar CodigoSeguridadeCF.'
            )
        with default_storage.open(source_document.signed_xml_path, 'rb') as signed_file:
            signed_xml = signed_file.read()
        try:
            root = ET.fromstring(signed_xml)
        except ET.ParseError as exc:
            raise ValueError(
                f'{item.encf}: el XML íntegro firmado del grupo 4 no es XML válido.'
            ) from exc
        signature_node = root.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        if signature_node is None:
            raise ValueError(
                f'{item.encf}: el XML íntegro firmado del grupo 4 no contiene SignatureValue.'
            )
        signature_value = re.sub(r'\s+', '', ''.join(signature_node.itertext() or '').strip())
        if len(signature_value) < 6:
            raise ValueError(
                f'{item.encf}: SignatureValue del XML íntegro firmado es demasiado corto.'
            )
        return signature_value

    def _append_text(self, parent, tag: str, value) -> None:
        cleaned = _clean_scenario_value(value)
        if not cleaned:
            return
        element = ET.SubElement(parent, tag)
        element.text = cleaned

    def generate_group(self, *, plan: DGIICertificationPlan, group_number: int, user=None) -> dict:
        plan_id = plan.pk
        diagnostic = None
        try:
            with transaction.atomic():
                locked_plan = self.lock_service.lock_plan(plan_id=plan_id)
                target_item_ids = list(
                    locked_plan.items.filter(dgii_group=group_number)
                    .order_by('pk').values_list('pk', flat=True)
                )
                scope, _all_item_ids = self._lock_generation_scope(locked_plan, target_item_ids)
                target_items = sorted(
                    (scope.item(item_id) for item_id in target_item_ids),
                    key=lambda current: (current.source_sheet, current.source_row, current.pk),
                )
                previous_versions = {
                    current.pk: self._published_version_snapshot(
                        self._document_for_item_or_none(scope, current.pk), current
                    )
                    for current in target_items
                }
                for current in target_items:
                    document = self._document_for_item_or_none(scope, current.pk)
                    try:
                        self.assert_generation_mutable(document)
                    except (CertificationDocumentImmutableError, CertificationMutationBlocked) as exc:
                        diagnostic = self._group_error(current, str(exc))
                        self._record_generation_failure(
                            item=current, document=document, error=str(exc), user=user,
                            stage='certification_group_generation_blocked', rolled_back=True,
                        )
                        break
                if diagnostic is None:
                    causal_item = None
                    try:
                        with transaction.atomic():
                            for current in target_items:
                                causal_item = current
                                self._generate_locked_item(item=current, user=user)
                    except (UnsupportedECFTypeError, ValueError) as exc:
                        diagnostic = self._group_error(causal_item, str(exc))
                        self._mark_generation_error(
                            item=causal_item,
                            user=user,
                            error=str(exc),
                            previous_version=previous_versions[causal_item.pk],
                            stage='certification_group_generation_failed',
                            rolled_back=True,
                        )
                if diagnostic is None:
                    return {'generated': len(target_items), 'failed': 0, 'errors': []}
        except Exception as exc:
            self._persist_unexpected_generation_failure(
                plan_id=plan_id,
                item_ids=list(
                    DGIICertificationItem.objects.filter(
                        plan_id=plan_id, dgii_group=group_number
                    ).values_list('pk', flat=True)
                ),
                error=exc,
                user=user,
            )
            raise
        return {'generated': 0, 'failed': 1, 'errors': [diagnostic]}

    def _get_or_create_document(self, item: DGIICertificationItem) -> DGIICertificationDocument:
        document = DGIICertificationDocument.objects.filter(item_id=item.pk).first()
        if document is None:
            document = DGIICertificationDocument.objects.create(
                item=item,
                company=item.company,
                plan=item.plan,
                ecf_type=item.ecf_type,
                encf=item.encf,
            )
        return document

    def _mark_generation_error(
        self,
        *,
        item: DGIICertificationItem,
        user=None,
        error: str,
        previous_version: dict,
        stage: str = 'certification_document_generation_failed',
        rolled_back: bool = True,
    ) -> tuple[DGIICertificationDocument, bool]:
        document = DGIICertificationDocument.objects.filter(item_id=item.pk).first()
        if previous_version['published']:
            self._record_generation_failure(
                item=item, document=document, error=error, user=user,
                stage='certification_document_regeneration_failed', rolled_back=rolled_back,
                previous_xml_hash=previous_version['xml_hash'],
            )
            return document, True
        if document is None:
            document = self._get_or_create_document(item)
        self.assert_generation_mutable(document)
        document.status = DGIICertificationDocument.STATUS_GENERATION_ERROR
        document.generation_error = error
        document.xml_content = ''
        document.xml_hash = ''
        document.generated_at = None
        document.save(update_fields=[
            'status', 'generation_error', 'xml_content', 'xml_hash',
            'generated_at', 'updated_at',
        ])
        item.status = DGIICertificationItem.STATUS_GENERATION_ERROR
        item.generation_error = error
        item.save(update_fields=['status', 'generation_error', 'updated_at'])
        self._record_generation_failure(
            item=item, document=document, error=error, user=user,
            stage=stage, rolled_back=rolled_back,
        )
        return document, False

    def _lock_generation_scope(self, plan, target_item_ids):
        items = list(
            DGIICertificationItem.objects.filter(
                plan_id=plan.pk, company_id=plan.company_id, pk__in=target_item_ids
            ).order_by('pk')
        )
        all_item_ids = {current.pk for current in items}
        rfce_encfs = [current.encf for current in items if current.ecf_type == 'RFCE' and current.encf]
        if rfce_encfs:
            all_item_ids.update(
                DGIICertificationItem.objects.filter(
                    plan_id=plan.pk, company_id=plan.company_id,
                    dgii_group=4, encf__in=rfce_encfs,
                ).values_list('pk', flat=True)
            )
        document_ids = list(
            DGIICertificationDocument.objects.filter(
                plan_id=plan.pk, company_id=plan.company_id, item_id__in=all_item_ids
            ).order_by('pk').values_list('pk', flat=True)
        )
        scope = self.lock_service.lock_scope(
            plan_id=plan.pk,
            item_ids=sorted(all_item_ids),
            document_ids=document_ids,
        )
        return scope, sorted(all_item_ids)

    @staticmethod
    def _document_for_item_or_none(scope, item_id):
        try:
            return scope.document_for_item(item_id)
        except CertificationDocumentNotFound:
            return None

    @staticmethod
    def _published_version_snapshot(document, item):
        return {
            'published': bool(
                document and document.xml_content and document.xml_hash and document.generated_at
            ),
            'xml_hash': document.xml_hash if document else '',
            'document_status': document.status if document else None,
            'item_status': item.status,
        }

    @staticmethod
    def _group_error(item, error):
        return {
            'item_id': item.pk,
            'ecf_type': item.ecf_type,
            'source_sheet': item.source_sheet,
            'source_row': item.source_row,
            'error': error,
            'rolled_back': True,
        }

    def _record_generation_failure(
        self, *, item, document, error, user, stage, rolled_back,
        previous_xml_hash='',
    ):
        DGIICertificationEvent.objects.create(
            company=item.company,
            plan=item.plan,
            item=item,
            event_type=DGIICertificationEvent.EVENT_XML_GENERATION_ERROR,
            message=error,
            payload={
                'stage': stage,
                'rolled_back': rolled_back,
                'certification_document_id': document.pk if document else None,
                'ecf_type': item.ecf_type,
                'dgii_group': item.dgii_group,
                'encf': item.encf,
                'previous_xml_hash': previous_xml_hash,
            },
            created_by=user,
        )

    def _persist_unexpected_generation_failure(self, *, plan_id, item_ids, error, user):
        try:
            with transaction.atomic():
                plan = self.lock_service.lock_plan(plan_id=plan_id)
                scope, _all_ids = self._lock_generation_scope(plan, item_ids)
                item = scope.item(sorted(item_ids)[0]) if item_ids else None
                if item:
                    self._record_generation_failure(
                        item=item,
                        document=self._document_for_item_or_none(scope, item.pk),
                        error=str(error),
                        user=user,
                        stage='certification_generation_unexpected_error',
                        rolled_back=True,
                    )
        except Exception:
            logger.exception('No se pudo persistir diagnóstico inesperado de generación DGII.')

    def _resolve_issuer(self, company: Company) -> ECFIssuerConfig:
        issuers = list(ECFIssuerConfig.objects.filter(company=company, is_active=True).order_by('id')[:2])
        if not issuers:
            raise ValueError('No hay emisor e-CF activo configurado para la empresa.')
        if len(issuers) > 1:
            raise ValueError('Hay varios emisores e-CF activos; deje uno activo para generar documentos de certificacion.')
        return issuers[0]

    def _build_payload(self, *, item: DGIICertificationItem, issuer: ECFIssuerConfig) -> ECFPayload:
        totals = self._build_totals(item)
        amount = totals['amount_total']
        if amount <= 0 and totals.get('non_billable_amount', Decimal('0.00')) <= 0:
            raise ValueError('El escenario DGII no tiene monto valido para generar e-CF.')
        items = self._build_items(item, totals)
        self._validate_fiscal_consistency(totals=totals, items=items)
        payment_forms = self._build_payment_forms(item, totals)
        payment_type = self._build_payment_type(item, payment_forms)

        return ECFPayload(
            ecf_type=item.ecf_type,
            encf=item.encf,
            issue_date=self._raw_date(item, 'FechaEmision') or format_dgii_date(timezone.localdate()),
            signature_datetime=format_dgii_datetime(),
            sequence_expiration_date=self._raw_date(item, 'FechaVencimientoSecuencia'),
            income_type=self._raw_text(item, 'TipoIngresos', max_length=2),
            payment_type=payment_type,
            payment_form=self._raw_text(item, 'FormaPago[1]', max_length=1) or PAYMENT_METHOD_TO_DGII.get('cash', '1'),
            credit_note_indicator=None,
            issuer=self._map_issuer(issuer, item),
            buyer=self._map_buyer(item),
            totals=totals,
            items=items,
            internal_invoice_number=self._raw_text(item, 'NumeroFacturaInterna', max_length=60),
            include_signature_placeholder=True,
            payment_forms=payment_forms,
            discounts_or_surcharges=self._build_discounts_or_surcharges(item)
            if item.encf in DGII_CERTIFICATION_RETRY_ENCFS
            else [],
            id_doc_fields=self._build_id_doc_fields(item),
            modified_document=self._build_modified_document(item),
            use_issuer_location_emisor_tags=False,
            include_buyer=self._include_buyer(item),
        )

    def _include_buyer(self, item: DGIICertificationItem) -> bool:
        return should_include_buyer(item.ecf_type, self._has_buyer_fields(item))

    def _has_buyer_fields(self, item: DGIICertificationItem) -> bool:
        buyer_fields = (
            'RNCComprador',
            'RNCCompradorAlt',
            'IdentificadorExtranjero',
            'RazonSocialComprador',
            'ContactoComprador',
            'CorreoComprador',
            'DireccionComprador',
            'MunicipioComprador',
            'ProvinciaComprador',
            'ContactoEntrega',
            'DireccionEntrega',
            'TelefonoAdicional',
            'FechaOrdenCompra',
            'NumeroOrdenCompra',
            'CodigoInternoComprador',
        )
        return any(self._raw_text(item, field) for field in buyer_fields) or bool(item.receiver_name) or bool(item.receiver_rnc)

    def _build_id_doc_fields(self, item: DGIICertificationItem) -> dict:
        keys = [
            'IndicadorNotaCredito',
            'IndicadorEnvioDiferido',
            'IndicadorMontoGravado',
            'IndicadorServicioTodoIncluido',
            'FechaLimitePago',
            'TerminoPago',
        ]
        return {key: self._raw_text(item, key) for key in keys if self._raw_text(item, key)}

    def _build_modified_document(self, item: DGIICertificationItem) -> dict | None:
        if item.ecf_type not in {'33', '34'}:
            return None
        modified_encf = self._raw_text(item, 'NCFModificado')
        modified_date = self._raw_date(item, 'FechaNCFModificado')
        modification_code = self._raw_text(item, 'CodigoModificacion', max_length=1)
        if not modified_encf or not modified_date or not modification_code:
            return None
        return {
            'encf': modified_encf,
            'issue_date': modified_date,
            'code': modification_code,
            'reason': self._clean_optional_xml_text(self._raw_text(item, 'RazonModificacion'), max_length=90),
        }

    def _map_issuer(self, issuer: ECFIssuerConfig, item: DGIICertificationItem) -> dict:
        phones = [
            phone for phone in (
                dgii_phone(self._raw_text(item, f'TelefonoEmisor[{index}]'))
                for index in range(1, 4)
            )
            if phone
        ]
        return {
            'rnc': digits_only(self._raw_text(item, 'RNCEmisor')),
            'business_name': clean_text(self._raw_text(item, 'RazonSocialEmisor', max_length=150), 150),
            'trade_name': clean_text(self._raw_text(item, 'NombreComercial', max_length=150), 150),
            'address': clean_text(self._raw_text(item, 'DireccionEmisor', max_length=100), 100),
            'municipality': dgii_location_code(self._raw_text(item, 'Municipio')),
            'province': dgii_location_code(self._raw_text(item, 'Provincia')),
            'phone': phones[0] if phones else None,
            'phones': phones,
            'email': clean_text(self._raw_text(item, 'CorreoEmisor', max_length=80), 80),
            'website': self._clean_website(self._raw_text(item, 'WebSite')),
            'economic_activity': self._clean_optional_xml_text(self._raw_text(item, 'ActividadEconomica'), max_length=100),
            'seller_code': self._clean_optional_xml_text(self._raw_text(item, 'CodigoVendedor'), max_length=60),
            'order_number': clean_text(digits_only(self._raw_text(item, 'NumeroPedidoInterno')), 20),
            'sales_zone': self._clean_optional_xml_text(self._raw_text(item, 'ZonaVenta'), max_length=20),
            'sales_route': self._clean_optional_xml_text(self._raw_text(item, 'RutaVenta'), max_length=20),
            'additional_information': self._clean_optional_xml_text(
                self._raw_text(item, 'InformacionAdicionalEmisor'),
                max_length=250,
            ),
        }

    def _map_buyer(self, item: DGIICertificationItem) -> dict:
        issuer_rnc = digits_only(self._raw_text(item, 'RNCEmisor'))
        foreign_identifier = digits_only(self._raw_text(item, 'IdentificadorExtranjero'))
        if foreign_identifier:
            business_name = (
                clean_text(self._raw_text(item, 'RazonSocialComprador', max_length=150), 150)
                or clean_text(item.receiver_name, 150)
                or DGII_CERTIFICATION_DEFAULT_BUYER_NAME
            )
            return {
                'rnc': '',
                'foreign_identifier': foreign_identifier,
                'business_name': business_name,
                **self._map_buyer_optional_fields(item),
            }

        rnc = (
            digits_only(self._raw_text(item, 'RNCComprador'))
            or digits_only(self._raw_text(item, 'RNCCompradorAlt'))
            or digits_only(item.receiver_rnc)
        )
        if not rnc or rnc == issuer_rnc:
            rnc = DGII_CERTIFICATION_DEFAULT_BUYER_RNC

        business_name = (
            clean_text(self._raw_text(item, 'RazonSocialComprador', max_length=150), 150)
            or clean_text(item.receiver_name, 150)
        )
        issuer_name = clean_text(self._raw_text(item, 'RazonSocialEmisor', max_length=150), 150)
        if not business_name or business_name == issuer_name:
            business_name = DGII_CERTIFICATION_DEFAULT_BUYER_NAME

        return {
            'rnc': rnc,
            'foreign_identifier': '',
            'business_name': business_name,
            **self._map_buyer_optional_fields(item),
        }

    def _map_buyer_optional_fields(self, item: DGIICertificationItem) -> dict:
        return {
            'contact': self._clean_optional_xml_text(self._raw_text(item, 'ContactoComprador'), max_length=80),
            'email': clean_text(self._raw_text(item, 'CorreoComprador', max_length=80), 80),
            'address': clean_text(self._raw_text(item, 'DireccionComprador', max_length=100), 100),
            'municipality': dgii_location_code(self._raw_text(item, 'MunicipioComprador')),
            'province': dgii_location_code(self._raw_text(item, 'ProvinciaComprador')),
            'delivery_date': self._raw_date(item, 'FechaEntrega'),
            'delivery_contact': self._clean_optional_xml_text(self._raw_text(item, 'ContactoEntrega'), max_length=100),
            'delivery_address': clean_text(self._raw_text(item, 'DireccionEntrega', max_length=100), 100),
            'phone': dgii_phone(self._raw_text(item, 'TelefonoAdicional')),
            'purchase_order_date': self._raw_date(item, 'FechaOrdenCompra'),
            'purchase_order_number': clean_text(self._raw_text(item, 'NumeroOrdenCompra', max_length=20), 20),
            'internal_code': clean_text(self._raw_text(item, 'CodigoInternoComprador', max_length=20), 20),
        }

    def _build_totals(self, item: DGIICertificationItem) -> dict:
        taxable_total = self._raw_decimal(item, 'MontoGravadoTotal')
        taxable_i1 = self._raw_decimal(item, 'MontoGravadoI1')
        taxable_i2 = self._raw_decimal(item, 'MontoGravadoI2')
        taxable_i3 = self._raw_decimal(item, 'MontoGravadoI3')
        exempt_amount = self._raw_decimal(item, 'MontoExento')
        total_itbis = self._raw_decimal(item, 'TotalITBIS')
        total_itbis1 = self._raw_decimal(item, 'TotalITBIS1')
        total_itbis2 = self._raw_decimal(item, 'TotalITBIS2')
        total_itbis3 = self._raw_decimal(item, 'TotalITBIS3')
        additional_tax = self._raw_decimal(item, 'MontoImpuestoAdicional')
        amount_period = self._raw_decimal(item, 'MontoPeriodo')
        value_to_pay = self._raw_decimal(item, 'ValorPagar')
        total_itbis_retained = self._raw_decimal(item, 'TotalITBISRetenido')
        total_isr_retention = self._raw_decimal(item, 'TotalISRRetencion')
        non_billable_amount = self._raw_decimal(item, 'MontoNoFacturable')
        itbis1 = self._raw_text(item, 'ITBIS1')
        itbis2 = self._raw_text(item, 'ITBIS2')
        itbis3 = self._raw_text(item, 'ITBIS3')
        raw_amount_total = self._raw_decimal(item, 'MontoTotal')
        amount_total = raw_amount_total if raw_amount_total is not None else quantize_money(item.amount or Decimal('0.00'))

        if taxable_total is None:
            taxable_components = [value for value in (taxable_i1, taxable_i2, taxable_i3) if value is not None]
            taxable_total = quantize_money(sum(taxable_components, Decimal('0.00'))) if taxable_components else None
        totals = {
            'explicit_fiscal_totals': True,
            'amount_total': amount_total,
            'total_itbis': total_itbis or Decimal('0.00'),
            'total_itbis1': total_itbis1 or Decimal('0.00'),
            'total_itbis2': total_itbis2 or Decimal('0.00'),
            'total_itbis3': total_itbis3 or Decimal('0.00'),
            'additional_tax': additional_tax or Decimal('0.00'),
            'taxable_amount': taxable_total or Decimal('0.00'),
            'taxable_amount_i1': taxable_i1 or Decimal('0.00'),
            'taxable_amount_i2': taxable_i2 or Decimal('0.00'),
            'taxable_amount_i3': taxable_i3 or Decimal('0.00'),
            'exempt_amount': exempt_amount or Decimal('0.00'),
            'non_billable_amount': non_billable_amount or Decimal('0.00'),
            'itbis_rate': Decimal('18.00') if total_itbis and total_itbis > 0 else Decimal('0.00'),
            'itbis_rate1': itbis1 or None,
            'itbis_rate2': itbis2 or None,
            'itbis_rate3': itbis3 or None,
            'amount_period': amount_period or Decimal('0.00'),
            'value_to_pay': value_to_pay or Decimal('0.00'),
            'total_itbis_retained': total_itbis_retained or Decimal('0.00'),
            'total_isr_retention': total_isr_retention or Decimal('0.00'),
            'present_total_fields': {
                key: bool(self._raw_text(item, key))
                for key in (
                    'ITBIS2',
                    'ITBIS3',
                    'TotalITBIS',
                    'TotalITBIS1',
                    'TotalITBIS2',
                    'TotalITBIS3',
                    'MontoNoFacturable',
                    'MontoPeriodo',
                    'ValorPagar',
                    'TotalITBISRetenido',
                    'TotalISRRetencion',
                )
            },
        }
        return totals

    def _build_items(self, item: DGIICertificationItem, totals: dict) -> list[dict]:
        items = []
        for index in range(1, 81):
            amount = self._raw_decimal(item, f'MontoItem[{index}]')
            quantity = self._raw_decimal(item, f'CantidadItem[{index}]') or Decimal('1.00')
            unit_price = self._raw_decimal(item, f'PrecioUnitarioItem[{index}]')
            discount = self._raw_decimal(item, f'DescuentoMonto[{index}]') or Decimal('0.00')
            surcharge = self._raw_decimal(item, f'RecargoMonto[{index}]') or Decimal('0.00')
            if amount is None and unit_price is not None:
                amount = quantize_money(quantity * unit_price)
            if amount is None or amount <= 0:
                continue
            name = self._clean_required_xml_text(item, f'NombreItem[{index}]')
            description = self._clean_optional_xml_text(self._raw_text(item, f'DescripcionItem[{index}]'), max_length=1000)
            indicator = self._raw_text(item, f'IndicadorFacturacion[{index}]', max_length=1)
            good_or_service = self._raw_text(item, f'IndicadorBienoServicio[{index}]', max_length=1) or '1'
            if unit_price is None or unit_price <= 0:
                unit_price = amount / quantity if quantity else amount
            if indicator not in {'0', '1', '2', '3', '4'}:
                raise ValueError(f'IndicadorFacturacion[{index}] es obligatorio para generar el item DGII.')
            codes = self._build_item_codes(item, index)
            retention = self._build_item_retention(item, index)
            items.append({
                'line_number': int(self._raw_decimal(item, f'NumeroLinea[{index}]') or len(items) + 1),
                'billing_indicator': indicator,
                'retention': retention,
                'name': clean_text(name, 80),
                'description': clean_text(description, 1000),
                'is_good_or_service': good_or_service,
                'quantity': quantity,
                'quantity_text': self._raw_item_text(item, f'CantidadItem[{index}]'),
                'unit_measure': self._raw_text(item, f'UnidadMedida[{index}]', max_length=2),
                'quantity_reference': (
                    self._raw_decimal(item, f'CantidadReferencia[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else None
                ),
                'quantity_reference_text': (
                    self._raw_item_text(item, f'CantidadReferencia[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else ''
                ),
                'reference_unit': (
                    self._raw_text(item, f'UnidadReferencia[{index}]', max_length=2)
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else ''
                ),
                'alcohol_degrees': (
                    self._raw_decimal(item, f'GradosAlcohol[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else None
                ),
                'alcohol_degrees_text': (
                    self._raw_item_text(item, f'GradosAlcohol[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else ''
                ),
                'reference_unit_price': (
                    self._raw_decimal(item, f'PrecioUnitarioReferencia[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else None
                ),
                'reference_unit_price_text': (
                    self._raw_item_text(item, f'PrecioUnitarioReferencia[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_REFERENCE_TYPES
                    else ''
                ),
                'manufacturing_date': (
                    self._raw_date(item, f'FechaElaboracion[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_DATE_TYPES
                    else ''
                ),
                'item_expiration_date': (
                    self._raw_date(item, f'FechaVencimientoItem[{index}]')
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_DATE_TYPES
                    else ''
                ),
                'unit_price': unit_price,
                'unit_price_text': self._raw_item_text(item, f'PrecioUnitarioItem[{index}]'),
                'discount': discount,
                'discount_text': self._raw_text(item, f'DescuentoMonto[{index}]'),
                'sub_discounts': (
                    self._build_item_sub_discounts(item, index)
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_SUBDISCOUNT_TYPES
                    else []
                ),
                'surcharge': surcharge,
                'surcharge_text': self._raw_text(item, f'RecargoMonto[{index}]'),
                'sub_surcharges': (
                    self._build_item_sub_surcharges(item, index)
                    if item.ecf_type in DGII_CERTIFICATION_ITEM_SUBDISCOUNT_TYPES
                    else []
                ),
                'amount': amount,
                'amount_text': self._raw_item_text(item, f'MontoItem[{index}]'),
                'code': codes[0]['value'] if codes else '',
                'codes': codes,
            })

        if not items:
            raise ValueError('El escenario DGII no contiene items reales para generar el e-CF.')
        return items

    def _build_item_sub_discounts(self, item: DGIICertificationItem, item_index: int) -> list[dict]:
        sub_discounts = []
        for sub_index in range(1, 13):
            discount_type = self._raw_text(item, f'TipoSubDescuento[{item_index}][{sub_index}]', max_length=1)
            percentage = self._raw_decimal(item, f'SubDescuentoPorcentaje[{item_index}][{sub_index}]')
            amount = self._raw_decimal(item, f'MontoSubDescuento[{item_index}][{sub_index}]')
            if not discount_type and percentage is None and amount is None:
                continue
            if not discount_type:
                raise ValueError(
                    f'TipoSubDescuento[{item_index}][{sub_index}] es obligatorio cuando hay subdescuento.'
                )
            sub_discounts.append({
                'type': discount_type,
                'percentage': percentage,
                'amount': amount,
            })
        return sub_discounts

    def _build_item_sub_surcharges(self, item: DGIICertificationItem, item_index: int) -> list[dict]:
        sub_surcharges = []
        direct_surcharge = self._raw_decimal(item, f'RecargoMonto[{item_index}]')
        for sub_index in range(1, 13):
            surcharge_type = self._raw_text(item, f'TipoSubRecargo[{item_index}][{sub_index}]', max_length=1)
            percentage = self._raw_decimal(item, f'SubRecargoPorcentaje[{item_index}][{sub_index}]')
            amount = self._raw_decimal(item, f'MontoSubRecargo[{item_index}][{sub_index}]')
            if not surcharge_type and percentage is None and amount is None:
                continue
            if not surcharge_type:
                raise ValueError(
                    f'TipoSubRecargo[{item_index}][{sub_index}] es obligatorio cuando hay subrecargo.'
                )
            if amount is None and direct_surcharge is not None and sub_index == 1:
                amount = direct_surcharge
            sub_surcharges.append({
                'type': surcharge_type,
                'percentage': percentage,
                'amount': amount,
            })
        return sub_surcharges

    def _raw_item_text(self, item: DGIICertificationItem, key: str) -> str:
        return self._raw_text(item, key)

    def _build_item_retention(self, item: DGIICertificationItem, item_index: int) -> dict:
        indicator = self._raw_text(item, f'IndicadorAgenteRetencionoPercepcion[{item_index}]', max_length=1)
        itbis = self._raw_decimal(item, f'MontoITBISRetenido[{item_index}]')
        isr = self._raw_decimal(item, f'MontoISRRetenido[{item_index}]')
        if not indicator and itbis is None and isr is None:
            return {}
        return {
            'indicator': indicator,
            'itbis': itbis,
            'isr': isr,
        }

    def _validate_fiscal_consistency(self, *, totals: dict, items: list[dict]) -> None:
        taxable = totals.get('taxable_amount', Decimal('0.00'))
        exempt = totals.get('exempt_amount', Decimal('0.00'))
        itbis = totals.get('total_itbis', Decimal('0.00'))
        additional_tax = totals.get('additional_tax', Decimal('0.00'))
        non_billable = totals.get('non_billable_amount', Decimal('0.00'))
        total = totals['amount_total']
        expected_total = quantize_money(taxable + exempt + itbis + additional_tax)
        if total == 0 and non_billable > 0:
            return
        if abs(expected_total - total) > Decimal('0.02'):
            raise ValueError(
                'Totales fiscales inconsistentes: '
                'MontoGravadoTotal + MontoExento + TotalITBIS + MontoImpuestoAdicional = '
                f'{expected_total}, '
                f'pero MontoTotal = {total}.'
            )

    def _build_payment_forms(self, item: DGIICertificationItem, totals: dict) -> list[dict]:
        if item.ecf_type in {'33', '34'}:
            return []
        if not self._raw_text(item, 'TipoPago', max_length=1):
            return []
        payments = []
        for index in range(1, 8):
            form = self._raw_text(item, f'FormaPago[{index}]', max_length=1)
            amount = self._raw_decimal(item, f'MontoPago[{index}]')
            if not form and amount is None:
                continue
            if not form or amount is None:
                continue
            payments.append({'form': form, 'amount': amount})
        return payments

    def _build_payment_type(self, item: DGIICertificationItem, payment_forms: list[dict]) -> str:
        payment_type = self._raw_text(item, 'TipoPago', max_length=1)
        if not payment_type:
            return ''
        return payment_type

    def _build_item_codes(self, item: DGIICertificationItem, item_index: int) -> list[dict]:
        codes = []
        for code_index in range(1, 6):
            code_type = self._raw_text(item, f'TipoCodigo[{item_index}][{code_index}]', max_length=14)
            code_value = self._raw_text(item, f'CodigoItem[{item_index}][{code_index}]', max_length=35)
            if not code_type and not code_value:
                continue
            if not code_type or not code_value:
                raise ValueError(
                    f'TipoCodigo[{item_index}][{code_index}] y CodigoItem[{item_index}][{code_index}] '
                    'deben venir juntos en el set DGII.'
                )
            codes.append({'type': clean_text(code_type, 14), 'value': clean_text(code_value, 35)})
        return codes

    def _build_discounts_or_surcharges(self, item: DGIICertificationItem) -> list[dict]:
        adjustments = []
        for index in range(1, 21):
            line_number = self._raw_decimal(item, f'NumeroLineaDoR[{index}]')
            adjustment_type = self._raw_text(item, f'TipoAjuste[{index}]', max_length=1)
            amount = self._raw_decimal(item, f'MontoDescuentooRecargo[{index}]')
            billing_indicator = self._raw_text(item, f'IndicadorFacturacionDescuentooRecargo[{index}]', max_length=1)
            if line_number is None and not adjustment_type and amount is None:
                continue
            if line_number is None:
                line_number = Decimal(index)
            if not adjustment_type:
                raise ValueError(f'TipoAjuste[{index}] es obligatorio para descuentos/recargos.')
            adjustments.append({
                'line_number': int(line_number),
                'adjustment_type': adjustment_type,
                'description': clean_text(self._raw_text(item, f'DescripcionDescuentooRecargo[{index}]', max_length=45), 45),
                'value_type': self._raw_text(item, f'TipoValor[{index}]', max_length=1),
                'value': self._raw_decimal(item, f'ValorDescuentooRecargo[{index}]'),
                'amount': amount,
                'billing_indicator': billing_indicator,
            })
        return adjustments

    def _raw_decimal(self, item: DGIICertificationItem, key: str) -> Decimal | None:
        parsed = _parse_decimal(self._raw_value(item, key))
        return quantize_money(parsed) if parsed is not None else None

    def _raw_text(self, item: DGIICertificationItem, key: str, max_length: int | None = None) -> str:
        cleaned = _clean_scenario_value(self._raw_value(item, key))
        if not cleaned:
            return ''
        return cleaned[:max_length] if max_length else cleaned

    def _raw_value(self, item: DGIICertificationItem, key: str):
        raw_data = item.raw_data or {}
        if key == 'NumeroFacturaInterna':
            direct_value = raw_data.get(key)
            if _clean_scenario_value(direct_value):
                return direct_value
            alias = self._column_alias_for(key)
            if alias:
                return raw_data.get(alias)
        if key == 'CodigoVendedor':
            direct_value = raw_data.get(key)
            if _clean_scenario_value(direct_value):
                return direct_value
            alias = self._column_alias_for(key)
            if alias:
                return raw_data.get(alias)
        if key in {
            'NumeroPedidoInterno',
            'RNCComprador',
            'RazonSocialComprador',
        }:
            alias = self._column_alias_for(key)
            if alias in raw_data:
                alias_value = raw_data.get(alias)
                if _clean_scenario_value(alias_value):
                    return alias_value
            if key in raw_data:
                return raw_data.get(key)
        if key in raw_data:
            return raw_data.get(key)
        alias = self._column_alias_for(key)
        if alias:
            return raw_data.get(alias)
        return None

    def _column_alias_for(self, key: str) -> str | None:
        if key in DGII_ECF_COLUMN_ALIASES:
            return DGII_ECF_COLUMN_ALIASES[key]

        match = re.match(r'^(FormaPago|MontoPago)\[(\d+)\]$', key)
        if match:
            base = 13 if match.group(1) == 'FormaPago' else 14
            return f'col_{base + ((int(match.group(2)) - 1) * 2)}'

        match = re.match(r'^TelefonoEmisor\[(\d+)\]$', key)
        if match:
            return f'col_{40 + (int(match.group(1)) - 1)}'

        match = re.match(r'^(NumeroLinea|IndicadorFacturacion|NombreItem|IndicadorBienoServicio|DescripcionItem|CantidadItem|UnidadMedida|PrecioUnitarioItem|DescuentoMonto|RecargoMonto|MontoItem)\[(\d+)\]$', key)
        if match:
            offsets = {
                'NumeroLinea': 0,
                'IndicadorFacturacion': 11,
                'NombreItem': 15,
                'IndicadorBienoServicio': 16,
                'DescripcionItem': 17,
                'CantidadItem': 18,
                'UnidadMedida': 19,
                'PrecioUnitarioItem': 40,
                'DescuentoMonto': 41,
                'RecargoMonto': 57,
                'MontoItem': 79,
            }
            return f"col_{183 + ((int(match.group(2)) - 1) * 80) + offsets[match.group(1)]}"

        match = re.match(r'^(TipoCodigo|CodigoItem)\[(\d+)\]\[(\d+)\]$', key)
        if match:
            item_index = int(match.group(2))
            code_index = int(match.group(3))
            base = 184 if match.group(1) == 'TipoCodigo' else 185
            return f'col_{base + ((item_index - 1) * 80) + ((code_index - 1) * 2)}'

        match = re.match(r'^(IndicadorAgenteRetencionoPercepcion|MontoITBISRetenido|MontoISRRetenido)\[(\d+)\]$', key)
        if match:
            offsets = {
                'IndicadorAgenteRetencionoPercepcion': 12,
                'MontoITBISRetenido': 13,
                'MontoISRRetenido': 14,
            }
            return f"col_{183 + ((int(match.group(2)) - 1) * 80) + offsets[match.group(1)]}"

        match = re.match(r'^(NumeroLineaDoR|TipoAjuste|DescripcionDescuentooRecargo|TipoValor|ValorDescuentooRecargo|MontoDescuentooRecargo|IndicadorFacturacionDescuentooRecargo)\[(\d+)\]$', key)
        if match:
            offsets = {
                'NumeroLineaDoR': 0,
                'TipoAjuste': 1,
                'DescripcionDescuentooRecargo': 3,
                'TipoValor': 4,
                'ValorDescuentooRecargo': 5,
                'MontoDescuentooRecargo': 6,
                'IndicadorFacturacionDescuentooRecargo': 8,
            }
            return f"col_{5158 + ((int(match.group(2)) - 1) * 9) + offsets[match.group(1)]}"

        return None

    def _raw_date(self, item: DGIICertificationItem, key: str) -> str:
        text = self._raw_text(item, key)
        if not text:
            return ''
        if re.match(r'^\d{2}-\d{2}-\d{4}$', text):
            return text
        return ''

    def _clean_required_xml_text(self, item: DGIICertificationItem, key: str, *, max_length: int = 80) -> str:
        cleaned = self._clean_optional_xml_text(self._raw_text(item, key), max_length=max_length)
        if not cleaned:
            raise ValueError(f'{key} es obligatorio para generar el e-CF de certificacion DGII.')
        return cleaned

    def _clean_optional_xml_text(self, value: str, *, max_length: int = 80) -> str:
        cleaned = _clean_scenario_value(value)
        if not cleaned:
            return ''
        cleaned = re.sub(r'[^A-Za-z0-9ÁÉÍÓÚáéíóúÑñ .,/()"\-]+', '', cleaned).strip()
        if _clean_receiver_name(cleaned) or re.search(r'[A-Za-z]', cleaned):
            return cleaned[:max_length]
        return ''

    def _clean_website(self, value: str) -> str:
        cleaned = _clean_scenario_value(value)
        if not cleaned:
            return ''
        markdown_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', cleaned)
        if markdown_match:
            cleaned = markdown_match.group(1) or markdown_match.group(2)
        cleaned = re.sub(r'^https?://', '', cleaned.strip(), flags=re.IGNORECASE)
        cleaned = cleaned.split('/')[0]
        cleaned = re.sub(r'[^A-Za-z0-9.\-]', '', cleaned)
        return cleaned[:50]

    def _sequence_expiration_date(self, issuer: ECFIssuerConfig, ecf_type: str, encf: str) -> str | None:
        sequence = (
            ECFSequence.objects
            .filter(company=issuer.company, issuer=issuer, ecf_type=ecf_type, is_active=True)
            .order_by('start_number')
            .first()
        )
        if sequence and sequence.expiration_date:
            return format_dgii_date(sequence.expiration_date)
        return None


class CertificationDocumentImmutableForSigning(CertificationMutationBlocked):
    """The certification document cannot enter initial signing."""


class CertificationSigningAttemptFailed(Exception):
    """A controlled signing attempt failed without damaging the published artifact."""


class CertificationResignAuthorizationError(CertificationMutationBlocked):
    """The actor cannot authorize a certification re-sign operation."""


@dataclass(frozen=True)
class CertificationSigningSnapshot:
    plan_id: int
    company_id: int
    item_id: int
    document_id: int | None
    group_number: int
    encf: str
    xml_content: str
    xml_hash: str
    signed_xml_path: str
    signed_xml_hash: str
    signed_at: object
    is_resign: bool
    reason: str = ''


@dataclass(frozen=True)
class CertificationPreparedSignature:
    snapshot: CertificationSigningSnapshot
    storage_path: str
    signed_xml_hash: str
    policy_code: str
    warnings: tuple


class DGIICertificationDocumentSigner:
    """Sign certification snapshots and publish them under canonical row locks."""

    def __init__(
        self,
        certificate_policy: ECFCertificateSigningPolicy | None = None,
        certificate_loader: PKCS12CertificateLoader | None = None,
        signer: ECFXMLSigner | None = None,
        signature_validator: ECFSignatureValidator | None = None,
        lock_service: CertificationLockService | None = None,
    ) -> None:
        self.certificate_policy = certificate_policy or ECFCertificateSigningPolicy()
        self.certificate_loader = certificate_loader or PKCS12CertificateLoader()
        self.signer = signer or ECFXMLSigner()
        self.signature_validator = signature_validator or ECFSignatureValidator()
        self.lock_service = lock_service or CertificationLockService()

    def sign_item(self, *, item: DGIICertificationItem, user=None) -> DGIICertificationDocument:
        snapshot = self._capture_snapshot(item_id=item.pk, plan_id=item.plan_id, is_resign=False)
        try:
            prepared = self._prepare_signature(snapshot)
        except ECFError as exc:
            return self._mark_signing_error(snapshot=snapshot, user=user, error=str(exc))
        try:
            return self._publish_signature(prepared=prepared, actor=user)
        except Exception:
            self._cleanup_unpublished_path(prepared.storage_path)
            raise

    def prepare_document(
        self,
        *,
        prepared_document: PreparedCertificationDocument,
    ) -> PreparedCertificationSignature:
        """Sign prepared XML and store an immutable, still-unreferenced blob."""
        fence = prepared_document.target_fence
        snapshot = CertificationSigningSnapshot(
            plan_id=fence.plan_id,
            company_id=fence.company_id,
            item_id=fence.item_id,
            document_id=fence.document_id,
            group_number=prepared_document.item_snapshot.dgii_group,
            encf=prepared_document.item_snapshot.encf,
            xml_content=prepared_document.xml_content,
            xml_hash=prepared_document.xml_hash,
            signed_xml_path=fence.signed_xml_path,
            signed_xml_hash=fence.signed_xml_hash,
            signed_at=fence.signed_at,
            is_resign=bool(fence.signed_xml_path),
        )
        prepared = self._prepare_signature(snapshot)
        return PreparedCertificationSignature(
            prepared_document=prepared_document,
            storage_path=prepared.storage_path,
            signed_xml_hash=prepared.signed_xml_hash,
            policy_code=prepared.policy_code,
            warnings=prepared.warnings,
        )

    def resign_item(self, *, item: DGIICertificationItem, actor, reason: str) -> DGIICertificationDocument:
        normalized_reason = (reason or '').strip()
        if not normalized_reason:
            raise ValueError('La razón de refirma es obligatoria.')
        snapshot = self._capture_snapshot(
            item_id=item.pk, plan_id=item.plan_id, is_resign=True,
            actor=actor, reason=normalized_reason,
        )
        try:
            prepared = self._prepare_signature(snapshot)
        except ECFError as exc:
            self._record_resign_failure(snapshot=snapshot, actor=actor, error=str(exc))
            raise CertificationSigningAttemptFailed(str(exc)) from exc
        try:
            return self._publish_signature(prepared=prepared, actor=actor)
        except Exception:
            self._cleanup_unpublished_path(prepared.storage_path)
            raise

    def sign_group(self, *, plan: DGIICertificationPlan, group_number: int, user=None) -> dict:
        snapshots = []
        errors = []
        with transaction.atomic():
            locked_plan = self.lock_service.lock_plan(plan_id=plan.pk)
            item_ids = list(locked_plan.items.filter(dgii_group=group_number).order_by('pk').values_list('pk', flat=True))
            scope = self._lock_scope(locked_plan, item_ids)
            for item_id in item_ids:
                locked_item = scope.item(item_id)
                try:
                    document = scope.document_for_item(item_id)
                    self._assert_initial_signing_mutable(document)
                    snapshots.append(self._snapshot(locked_item, document, is_resign=False))
                except Exception as exc:
                    errors.append(self._group_error(locked_item, exc))

        prepared = []
        controlled_failures = []
        for snapshot in snapshots:
            try:
                prepared.append(self._prepare_signature(snapshot))
            except ECFError as exc:
                controlled_failures.append((snapshot, str(exc)))
            except Exception:
                for candidate in prepared:
                    self._cleanup_unpublished_path(candidate.storage_path)
                raise

        published, publication_errors = self._publish_group_candidates(
            plan_id=plan.pk, prepared=prepared, actor=user,
        )
        errors.extend(publication_errors)
        for snapshot, error in controlled_failures:
            try:
                self._mark_signing_error(snapshot=snapshot, user=user, error=error)
                errors.append(self._group_error_by_snapshot(snapshot, error))
            except (CertificationArtifactChanged, CertificationMutationBlocked) as exc:
                errors.append(self._group_error_by_snapshot(snapshot, exc))
        return {'signed': published, 'failed': len(errors), 'errors': errors}

    def _capture_snapshot(self, *, item_id, plan_id, is_resign, actor=None, reason=''):
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=plan_id)
            scope = self._lock_scope(plan, [item_id])
            locked_item = scope.item(item_id)
            document = scope.document_for_item(item_id)
            if is_resign:
                self._assert_resign_authorized(actor, plan.company_id)
                self._assert_resign_mutable(document)
            else:
                self._assert_initial_signing_mutable(document)
            return self._snapshot(locked_item, document, is_resign=is_resign, reason=reason)

    def _lock_scope(self, plan, item_ids):
        document_ids = list(
            DGIICertificationDocument.objects.filter(
                plan_id=plan.pk, company_id=plan.company_id, item_id__in=item_ids,
            ).order_by('pk').values_list('pk', flat=True)
        )
        return self.lock_service.lock_scope(
            plan_id=plan.pk, item_ids=sorted(item_ids), document_ids=document_ids,
        )

    @staticmethod
    def _snapshot(item, document, *, is_resign, reason=''):
        return CertificationSigningSnapshot(
            plan_id=document.plan_id, company_id=document.company_id,
            item_id=item.pk, document_id=document.pk, group_number=item.dgii_group,
            encf=document.encf, xml_content=document.xml_content, xml_hash=document.xml_hash,
            signed_xml_path=document.signed_xml_path,
            signed_xml_hash=document.signed_xml_hash, signed_at=document.signed_at,
            is_resign=is_resign, reason=reason,
        )

    def _assert_initial_signing_mutable(self, document):
        self._assert_submission_mutable(document)
        if document.status == DGIICertificationDocument.STATUS_SIGNED or self._has_signed_evidence(document):
            raise CertificationDocumentImmutableForSigning('El documento ya posee una firma; use la operación explícita de refirma.')
        if document.status != DGIICertificationDocument.STATUS_GENERATED or not document.xml_content or not document.xml_hash:
            raise CertificationDocumentImmutableForSigning('El documento no tiene una versión generada firmable.')

    def _assert_resign_mutable(self, document):
        self._assert_submission_mutable(document)
        if document.status != DGIICertificationDocument.STATUS_SIGNED:
            raise CertificationDocumentImmutableForSigning('Solo un documento firmado puede entrar en refirma.')
        if not all((document.signed_xml_path, document.signed_xml_hash, document.signed_at)):
            raise CertificationDocumentImmutableForSigning('La firma anterior está incompleta.')
        if not default_storage.exists(document.signed_xml_path):
            raise CertificationDocumentImmutableForSigning('El artefacto firmado anterior no está disponible.')

    def _assert_submission_mutable(self, document):
        if document.submission_outcome != DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED:
            raise CertificationMutationBlocked(
                f'{document.encf or document.pk}: submission_outcome={document.submission_outcome} bloquea firma.'
            )
        if self._has_dgii_delivery_evidence(document):
            raise CertificationMutationBlocked(f'{document.encf or document.pk}: existe evidencia de entrega DGII.')

    @staticmethod
    def _has_dgii_delivery_evidence(document):
        return bool(document.dgii_track_id or document.submitted_at or document.accepted_at or document.rejected_at)

    @staticmethod
    def _has_signed_evidence(document):
        return bool(document.signed_xml_path or document.signed_xml_hash or document.signed_at)

    @staticmethod
    def _assert_resign_authorized(actor, company_id):
        if actor and actor.is_authenticated and actor.is_superuser:
            return
        if actor and actor.is_authenticated and CompanyMembership.objects.filter(
            user=actor, company_id=company_id, is_active=True,
            role__in=(CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN),
        ).exists():
            return
        raise CertificationResignAuthorizationError('Solo un owner, admin o superusuario puede autorizar una refirma.')

    def _prepare_signature(self, snapshot):
        company = Company.objects.get(pk=snapshot.company_id)
        issuer = DGIICertificationDocumentGenerator()._resolve_issuer(company)
        policy_result = self.certificate_policy.evaluate(issuer)
        issuer.refresh_from_db()
        if policy_result.blocked:
            raise ECFValidationError(policy_result.reason)
        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        if not certificate_path:
            raise ECFValidationError('El emisor fiscal no tiene certificado DGII disponible para firmar.')
        certificate = self.certificate_loader.load(certificate_path, certificate_password)
        signed_xml = self.signer.sign(snapshot.xml_content, certificate)
        self.signature_validator.validate(signed_xml, certificate)
        encoded = signed_xml.encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()
        path = default_storage.save(
            self._signed_filename_for(snapshot=snapshot, signed_xml_hash=digest),
            ContentFile(encoded),
        )
        return CertificationPreparedSignature(
            snapshot=snapshot, storage_path=path, signed_xml_hash=digest,
            policy_code=policy_result.code, warnings=tuple(policy_result.warnings),
        )

    def _publish_signature(self, *, prepared, actor):
        snapshot = prepared.snapshot
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=snapshot.plan_id)
            scope = self._lock_scope(plan, [snapshot.item_id])
            item = scope.item(snapshot.item_id)
            document = scope.document(snapshot.document_id)
            self._assert_snapshot_current(document, snapshot)
            if snapshot.is_resign:
                self._assert_resign_authorized(actor, plan.company_id)
                self._assert_resign_mutable(document)
            else:
                self._assert_initial_signing_mutable(document)
            return self._publish_locked(item=item, document=document, prepared=prepared, actor=actor)

    def _publish_group_candidates(self, *, plan_id, prepared, actor):
        if not prepared:
            return 0, []
        cleanup = []
        errors = []
        published = 0
        try:
            with transaction.atomic():
                plan = self.lock_service.lock_plan(plan_id=plan_id)
                scope = self._lock_scope(plan, [candidate.snapshot.item_id for candidate in prepared])
                for candidate in prepared:
                    snapshot = candidate.snapshot
                    try:
                        with transaction.atomic():
                            item = scope.item(snapshot.item_id)
                            document = scope.document(snapshot.document_id)
                            self._assert_snapshot_current(document, snapshot)
                            self._assert_initial_signing_mutable(document)
                            self._publish_locked(item=item, document=document, prepared=candidate, actor=actor)
                        published += 1
                    except (
                        CertificationArtifactChanged,
                        CertificationMutationBlocked,
                        CertificationDocumentImmutableForSigning,
                    ) as exc:
                        cleanup.append(candidate.storage_path)
                        errors.append(self._group_error_by_snapshot(snapshot, exc))
        except Exception:
            cleanup.extend(candidate.storage_path for candidate in prepared)
            for path in set(cleanup):
                self._cleanup_unpublished_path(path)
            raise
        for path in cleanup:
            self._cleanup_unpublished_path(path)
        return published, errors

    @staticmethod
    def _publish_locked(*, item, document, prepared, actor):
        snapshot = prepared.snapshot
        previous_path = document.signed_xml_path
        previous_hash = document.signed_xml_hash
        document.status = DGIICertificationDocument.STATUS_SIGNED
        document.signed_xml_path = prepared.storage_path
        document.signed_xml_hash = prepared.signed_xml_hash
        document.signed_at = timezone.now()
        document.signing_error = ''
        document.save(update_fields=['status', 'signed_xml_path', 'signed_xml_hash', 'signed_at', 'signing_error', 'updated_at'])
        item.status = DGIICertificationItem.STATUS_SIGNED
        item.generation_error = ''
        item.save(update_fields=['status', 'generation_error', 'updated_at'])
        DGIICertificationEvent.objects.create(
            company=item.company, plan=item.plan, item=item,
            event_type=DGIICertificationEvent.EVENT_DOCUMENT_SIGNED,
            message='Documento e-CF de certificacion refirmado.' if snapshot.is_resign else 'Documento e-CF de certificacion firmado.',
            payload={
                'certification_document_id': document.pk, 'encf': document.encf,
                'sha256': prepared.signed_xml_hash, 'signed_xml_path': prepared.storage_path,
                'previous_signed_xml_path': previous_path, 'previous_signed_xml_hash': previous_hash,
                'resign': snapshot.is_resign, 'reason': snapshot.reason,
                'policy_code': prepared.policy_code, 'warnings': list(prepared.warnings),
            }, created_by=actor,
        )
        return document

    @staticmethod
    def _assert_snapshot_current(document, snapshot):
        current = (
            document.xml_content, document.xml_hash, document.signed_xml_path,
            document.signed_xml_hash, document.signed_at,
        )
        expected = (
            snapshot.xml_content, snapshot.xml_hash, snapshot.signed_xml_path,
            snapshot.signed_xml_hash, snapshot.signed_at,
        )
        if current != expected:
            raise CertificationArtifactChanged('El artefacto cambió mientras se preparaba la firma.')

    def _mark_signing_error(
        self,
        *,
        snapshot: CertificationSigningSnapshot,
        user=None,
        error: str,
    ) -> DGIICertificationDocument:
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=snapshot.plan_id)
            scope = self._lock_scope(plan, [snapshot.item_id])
            item = scope.item(snapshot.item_id)
            document = scope.document(snapshot.document_id)
            self._assert_initial_signing_mutable(document)
            self._assert_snapshot_current(document, snapshot)
            document.status = DGIICertificationDocument.STATUS_SIGNING_ERROR
            document.signing_error = error
            document.save(update_fields=['status', 'signing_error', 'updated_at'])
            item.status = DGIICertificationItem.STATUS_SIGNING_ERROR
            item.generation_error = error
            item.save(update_fields=['status', 'generation_error', 'updated_at'])
            self._record_signing_event(item=item, document=document, actor=user, error=error, resign=False)
            return document

    def _record_resign_failure(self, *, snapshot, actor, error):
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=snapshot.plan_id)
            scope = self._lock_scope(plan, [snapshot.item_id])
            item = scope.item(snapshot.item_id)
            document = scope.document(snapshot.document_id)
            self._assert_resign_mutable(document)
            self._assert_snapshot_current(document, snapshot)
            self._record_signing_event(item=item, document=document, actor=actor, error=error, resign=True, reason=snapshot.reason)

    @staticmethod
    def _record_signing_event(*, item, document, actor, error, resign, reason=''):
        DGIICertificationEvent.objects.create(
            company=item.company, plan=item.plan, item=item,
            event_type=DGIICertificationEvent.EVENT_DOCUMENT_SIGNING_ERROR,
            message=error,
            payload={
                'certification_document_id': document.pk, 'ecf_type': item.ecf_type,
                'dgii_group': item.dgii_group, 'encf': item.encf,
                'resign': resign, 'reason': reason,
                'preserved_signed_xml_path': document.signed_xml_path,
                'preserved_signed_xml_hash': document.signed_xml_hash,
            }, created_by=actor,
        )

    @staticmethod
    def _signed_filename_for(*, snapshot, signed_xml_hash):
        encf = snapshot.encf or f'item-{snapshot.item_id}'
        return (
            f'dgii_certification/company-{snapshot.company_id}/plan-{snapshot.plan_id}/'
            f'grupo-{snapshot.group_number}/signed/{encf}/xml-{snapshot.xml_hash[:16]}/'
            f'attempt-{uuid4().hex}-{signed_xml_hash}.xml'
        )

    def _cleanup_unpublished_path(self, path):
        if not path:
            return
        try:
            if DGIICertificationDocument.objects.filter(signed_xml_path=path).exists():
                return
            if default_storage.exists(path):
                default_storage.delete(path)
        except Exception:
            logger.exception('No se pudo limpiar artefacto de firma de certificación no publicado: %s', path)

    @staticmethod
    def _group_error(item, error):
        return {
            'item_id': item.pk, 'ecf_type': item.ecf_type,
            'source_sheet': item.source_sheet, 'source_row': item.source_row,
            'error': str(error),
        }

    @staticmethod
    def _group_error_by_snapshot(snapshot, error):
        item = DGIICertificationItem.objects.only('pk', 'ecf_type', 'source_sheet', 'source_row').get(pk=snapshot.item_id)
        return DGIICertificationDocumentSigner._group_error(item, error)


class CertificationPreparedArtifactPublisher:
    """Publish prepared XML and signature together after canonical fencing."""

    mutable_statuses = {
        DGIICertificationDocument.STATUS_PENDING,
        DGIICertificationDocument.STATUS_GENERATED,
        DGIICertificationDocument.STATUS_GENERATION_ERROR,
        DGIICertificationDocument.STATUS_SIGNING_ERROR,
        DGIICertificationDocument.STATUS_SIGNED,
    }

    def __init__(self, lock_service=None):
        self.lock_service = lock_service or CertificationLockService()

    def publish_document_and_signature(self, *, prepared_document, prepared_signature, actor=None):
        if prepared_signature.prepared_document != prepared_document:
            raise CertificationArtifactChanged('La firma preparada no corresponde al documento preparado.')
        path = prepared_signature.storage_path
        try:
            with transaction.atomic():
                fence = prepared_document.target_fence
                plan = self.lock_service.lock_plan(plan_id=fence.plan_id)
                item_ids = sorted({fence.item_id, *(dependency.item_id for dependency in prepared_document.dependency_fences)})
                items = self.lock_service.lock_items(plan=plan, item_ids=item_ids)
                current_target = DGIICertificationDocument.objects.filter(item_id=fence.item_id).first()
                document_ids = [dependency.document_id for dependency in prepared_document.dependency_fences]
                if current_target is not None:
                    document_ids.append(current_target.pk)
                documents = self.lock_service.lock_documents(
                    plan=plan, document_ids=sorted(set(document_ids)), locked_item_ids=item_ids,
                )
                scope = CertificationLockedScope.build(plan=plan, items=items, documents=documents)
                scope.assert_company_consistency()
                target = self._validate_target(scope=scope, fence=fence, current_target=current_target)
                self._validate_dependencies(scope=scope, dependencies=prepared_document.dependency_fences)
                self._validate_prepared_blob(prepared_signature)
                if target is None:
                    item = scope.item(fence.item_id)
                    target = DGIICertificationDocument.objects.create(
                        item=item, company=item.company, plan=item.plan,
                        ecf_type=item.ecf_type, encf=item.encf,
                    )
                item = scope.item(fence.item_id)
                now = timezone.now()
                target.status = DGIICertificationDocument.STATUS_SIGNED
                target.xml_content = prepared_document.xml_content
                target.xml_hash = prepared_document.xml_hash
                target.generated_at = prepared_document.generated_at
                target.generation_error = ''
                target.signed_xml_path = path
                target.signed_xml_hash = prepared_signature.signed_xml_hash
                target.signed_at = now
                target.signing_error = ''
                target.save(update_fields=[
                    'status', 'xml_content', 'xml_hash', 'generated_at', 'generation_error',
                    'signed_xml_path', 'signed_xml_hash', 'signed_at', 'signing_error', 'updated_at',
                ])
                item.status = DGIICertificationItem.STATUS_SIGNED
                item.generation_error = ''
                item.save(update_fields=['status', 'generation_error', 'updated_at'])
                dependency_payload = [
                    {
                        'document_id': dependency.document_id,
                        'xml_hash': dependency.xml_hash,
                        'signed_xml_path': dependency.signed_xml_path,
                        'signed_xml_hash': dependency.signed_xml_hash,
                        'signed_at': dependency.signed_at.isoformat() if dependency.signed_at else None,
                    }
                    for dependency in prepared_document.dependency_fences
                ]
                DGIICertificationEvent.objects.create(
                    company=item.company, plan=item.plan, item=item,
                    event_type=DGIICertificationEvent.EVENT_XML_GENERATED,
                    message='Documento e-CF preparado publicado conjuntamente con su firma.',
                    payload={'certification_document_id': target.pk, 'sha256': target.xml_hash, 'dependencies': dependency_payload},
                    created_by=actor,
                )
                DGIICertificationEvent.objects.create(
                    company=item.company, plan=item.plan, item=item,
                    event_type=DGIICertificationEvent.EVENT_DOCUMENT_SIGNED,
                    message='Firma preparada publicada conjuntamente con el documento e-CF.',
                    payload={
                        'certification_document_id': target.pk,
                        'sha256': target.signed_xml_hash,
                        'signed_xml_path': target.signed_xml_path,
                        'dependencies': dependency_payload,
                    },
                    created_by=actor,
                )
                return target
        except Exception:
            self.cleanup_unreferenced(path)
            raise

    def _validate_target(self, *, scope, fence, current_target):
        if fence.expected_document_absent:
            if current_target is not None:
                raise CertificationArtifactChanged('Apareció un documento target después del snapshot de ausencia.')
            return None
        if current_target is None or current_target.pk != fence.document_id:
            raise CertificationArtifactChanged('El documento target ya no coincide con el snapshot.')
        document = scope.document(fence.document_id)
        self._assert_target_mutable(document)
        current = (
            document.status, document.xml_content, document.xml_hash, document.signed_xml_path,
            document.signed_xml_hash, document.signed_at, document.submission_outcome,
        )
        expected = (
            fence.status, fence.xml_content, fence.xml_hash, fence.signed_xml_path,
            fence.signed_xml_hash, fence.signed_at, fence.submission_outcome,
        )
        if current != expected:
            raise CertificationArtifactChanged('El documento target cambió después del snapshot.')
        return document

    def _validate_dependencies(self, *, scope, dependencies):
        for fence in dependencies:
            document = scope.document(fence.document_id)
            current = (
                document.plan_id, document.company_id, document.item_id, document.xml_hash,
                document.signed_xml_path, document.signed_xml_hash, document.signed_at,
            )
            expected = (
                fence.plan_id, fence.company_id, fence.item_id, fence.xml_hash,
                fence.signed_xml_path, fence.signed_xml_hash, fence.signed_at,
            )
            if current != expected:
                raise CertificationArtifactChanged('Una dependencia cambió después del snapshot.')

    def _assert_target_mutable(self, document):
        if document.submission_outcome != DGIICertificationDocument.SUBMISSION_OUTCOME_NOT_STARTED:
            raise CertificationMutationBlocked(
                f'{document.encf or document.pk}: submission_outcome={document.submission_outcome} bloquea publicación.'
            )
        if document.dgii_track_id or document.submitted_at or document.accepted_at or document.rejected_at:
            raise CertificationMutationBlocked(f'{document.encf or document.pk}: existe evidencia de entrega DGII.')
        if document.status not in self.mutable_statuses:
            raise CertificationMutationBlocked(f'{document.encf or document.pk}: status={document.status} bloquea publicación.')

    @staticmethod
    def _validate_prepared_blob(prepared_signature):
        path = prepared_signature.storage_path
        if not path or not default_storage.exists(path):
            raise CertificationArtifactChanged('El archivo de firma preparado no está disponible.')
        with default_storage.open(path, 'rb') as signed_file:
            actual_hash = hashlib.sha256(signed_file.read()).hexdigest()
        if actual_hash != prepared_signature.signed_xml_hash:
            raise CertificationArtifactChanged('El archivo de firma preparado no coincide con su hash.')

    @staticmethod
    def cleanup_unreferenced(path):
        if not path:
            return
        try:
            if DGIICertificationDocument.objects.filter(signed_xml_path=path).exists():
                return
            if default_storage.exists(path):
                default_storage.delete(path)
        except Exception:
            logger.exception('No se pudo limpiar artefacto preparado no referenciado: %s', path)


class DGIICertificationRFCERebuilder:
    """Safely rebuild signed E32 <250k XMLs and their linked RFCE."""

    stale_reason = (
        'XML integros de facturas consumo <250K regenerados. '
        'Debe reenviar los RFCE porque CodigoSeguridadeCF depende de la nueva firma.'
    )

    def __init__(
        self,
        *,
        generator: DGIICertificationDocumentGenerator | None = None,
        signer: DGIICertificationDocumentSigner | None = None,
        publisher: CertificationPreparedArtifactPublisher | None = None,
        lock_service: CertificationLockService | None = None,
    ) -> None:
        self.generator = generator or DGIICertificationDocumentGenerator()
        self.signer = signer or DGIICertificationDocumentSigner()
        self.lock_service = lock_service or CertificationLockService()
        self.publisher = publisher or CertificationPreparedArtifactPublisher(
            lock_service=self.lock_service,
        )

    def rebuild(self, *, plan: DGIICertificationPlan, user=None) -> dict:
        summaries = {
            'generated_integral': self._empty_generation_summary(),
            'signed_integral': self._empty_signing_summary(),
            'generated_rfce': self._empty_generation_summary(),
            'signed_rfce': self._empty_signing_summary(),
        }
        source_documents: list[dict] = []
        try:
            group_snapshots = self._capture_rebuild_targets(plan_id=plan.pk)
        except Exception as exc:
            error = self._error_payload(None, exc)
            summaries['generated_integral']['failed'] = 1
            summaries['generated_integral']['errors'].append(error)
            return self._response(summaries, source_documents)

        integral_by_encf = {}
        for item, fence in group_snapshots[4]:
            prepared_document = None
            prepared_signature = None
            try:
                prepared_document = self.generator.prepare_item(
                    item_snapshot=item,
                    target_fence=fence,
                )
                summaries['generated_integral']['generated'] += 1
                prepared_signature = self.signer.prepare_document(
                    prepared_document=prepared_document,
                )
                published = self.publisher.publish_document_and_signature(
                    prepared_document=prepared_document,
                    prepared_signature=prepared_signature,
                    actor=user,
                )
                summaries['signed_integral']['signed'] += 1
                integral_by_encf[published.encf] = published.pk
                source_documents.append(self._source_document(published))
            except Exception as exc:
                if prepared_signature is not None:
                    self.publisher.cleanup_unreferenced(prepared_signature.storage_path)
                self._record_pipeline_failure(
                    summaries=summaries,
                    phase='integral',
                    item=item,
                    error=exc,
                    generation_prepared=prepared_document is not None,
                )

        if summaries['generated_integral']['failed'] or summaries['signed_integral']['failed']:
            return self._response(summaries, source_documents)

        for item, initial_fence in group_snapshots[3]:
            prepared_document = None
            prepared_signature = None
            try:
                source_id = integral_by_encf.get(item.encf)
                if source_id is None:
                    raise CertificationArtifactChanged(
                        f'{item.encf}: no existe integral firmado vigente para construir RFCE.'
                    )
                item_snapshot, target_fence, source_fence, signature_value = self._capture_rfce_snapshot(
                    plan_id=plan.pk,
                    target_item_id=item.pk,
                    source_document_id=source_id,
                    initial_target_fence=initial_fence,
                )
                prepared_document = self.generator.prepare_item(
                    item_snapshot=item_snapshot,
                    target_fence=target_fence,
                    dependency_fences=(source_fence,),
                    integral_signature_value=signature_value,
                )
                summaries['generated_rfce']['generated'] += 1
                prepared_signature = self.signer.prepare_document(
                    prepared_document=prepared_document,
                )
                self.publisher.publish_document_and_signature(
                    prepared_document=prepared_document,
                    prepared_signature=prepared_signature,
                    actor=user,
                )
                summaries['signed_rfce']['signed'] += 1
            except Exception as exc:
                if prepared_signature is not None:
                    self.publisher.cleanup_unreferenced(prepared_signature.storage_path)
                self._record_pipeline_failure(
                    summaries=summaries,
                    phase='rfce',
                    item=item,
                    error=exc,
                    generation_prepared=prepared_document is not None,
                )

        return self._response(summaries, source_documents)

    def _response(self, summaries, source_documents):
        return {
            'generated_integral': summaries['generated_integral'],
            'signed_integral': summaries['signed_integral'],
            'generated_rfce': summaries['generated_rfce'],
            'signed_rfce': summaries['signed_rfce'],
            'source_documents': source_documents,
            'rfce_marked_for_resubmit': 0,
            'failed': any(summary['failed'] for summary in summaries.values()),
        }

    def _capture_rebuild_targets(self, *, plan_id):
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=plan_id)
            items = list(
                plan.items.filter(dgii_group__in=(3, 4)).order_by('pk')
            )
            item_ids = [item.pk for item in items]
            locked_items = self.lock_service.lock_items(plan=plan, item_ids=item_ids)
            documents_by_item = {
                document.item_id: document
                for document in DGIICertificationDocument.objects.filter(
                    plan=plan, company=plan.company, item_id__in=item_ids,
                ).order_by('pk')
            }
            locked_documents = self.lock_service.lock_documents(
                plan=plan,
                document_ids=[document.pk for document in documents_by_item.values()],
                locked_item_ids=item_ids,
            )
            locked_by_item = {document.item_id: document for document in locked_documents}
            snapshots = {3: [], 4: []}
            for item in locked_items:
                document = locked_by_item.get(item.pk)
                if document is not None:
                    self.publisher._assert_target_mutable(document)
                snapshots[item.dgii_group].append((
                    copy.deepcopy(item),
                    self.generator.document_fence(item=item, document=document),
                ))
            return snapshots

    def _capture_rfce_snapshot(
        self, *, plan_id, target_item_id, source_document_id, initial_target_fence,
    ):
        with transaction.atomic():
            plan = self.lock_service.lock_plan(plan_id=plan_id)
            source = DGIICertificationDocument.objects.only('item_id').get(pk=source_document_id)
            item_ids = sorted({target_item_id, source.item_id})
            items = self.lock_service.lock_items(plan=plan, item_ids=item_ids)
            current_target = DGIICertificationDocument.objects.filter(item_id=target_item_id).first()
            document_ids = [source_document_id]
            if current_target is not None:
                document_ids.append(current_target.pk)
            documents = self.lock_service.lock_documents(
                plan=plan, document_ids=document_ids, locked_item_ids=item_ids,
            )
            scope = CertificationLockedScope.build(plan=plan, items=items, documents=documents)
            scope.assert_company_consistency()
            source = scope.document(source_document_id)
            target = self.publisher._validate_target(
                scope=scope,
                fence=initial_target_fence,
                current_target=current_target,
            )
            if source.status != DGIICertificationDocument.STATUS_SIGNED:
                raise CertificationArtifactChanged(f'{source.encf}: integral fuente no está firmado.')
            self.publisher._assert_target_mutable(source)
            signature_value, actual_hash = self._signature_and_hash(source)
            if actual_hash != source.signed_xml_hash:
                raise CertificationArtifactChanged(
                    f'{source.encf}: hash físico del integral no coincide con la evidencia persistida.'
                )
            source_fence = CertificationArtifactFence(
                plan_id=source.plan_id,
                company_id=source.company_id,
                item_id=source.item_id,
                document_id=source.pk,
                xml_hash=source.xml_hash,
                signed_xml_path=source.signed_xml_path,
                signed_xml_hash=source.signed_xml_hash,
                signed_at=source.signed_at,
            )
            target_item = scope.item(target_item_id)
            target_fence = self.generator.document_fence(item=target_item, document=target)
            return copy.deepcopy(target_item), target_fence, source_fence, signature_value

    def _source_document(self, document):
        signature_value, actual_hash = self._signature_and_hash(document)
        return {
            'encf': document.encf,
            'signed_xml_path': document.signed_xml_path,
            'signed_xml_hash': document.signed_xml_hash,
            'actual_sha256': actual_hash,
            'hash_matches_storage': actual_hash == document.signed_xml_hash,
            'signature_prefix': signature_value[:6],
        }

    def _signature_and_hash(self, document: DGIICertificationDocument) -> tuple[str, str]:
        if not document.signed_xml_path or not default_storage.exists(document.signed_xml_path):
            raise ValueError(f'{document.encf}: XML firmado no disponible para validar codigo RFCE.')
        with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
            signed_xml = signed_file.read()
        actual_hash = hashlib.sha256(signed_xml).hexdigest()
        root = ET.fromstring(signed_xml)
        signature_node = root.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        if signature_node is None:
            raise ValueError(f'{document.encf}: XML firmado no contiene SignatureValue.')
        signature_value = re.sub(r'\s+', '', ''.join(signature_node.itertext()).strip())
        return signature_value, actual_hash

    def _mark_rfce_for_resubmit(self, plan: DGIICertificationPlan, user) -> int:
        """Legacy compatibility hook; fiscal evidence is never reset by rebuild."""
        return 0

    @staticmethod
    def _empty_generation_summary():
        return {'generated': 0, 'failed': 0, 'errors': []}

    @staticmethod
    def _empty_signing_summary():
        return {'signed': 0, 'failed': 0, 'errors': []}

    @staticmethod
    def _error_payload(item, error):
        return {
            'item_id': item.pk if item else None,
            'ecf_type': item.ecf_type if item else None,
            'source_sheet': item.source_sheet if item else None,
            'source_row': item.source_row if item else None,
            'error': str(error),
        }

    def _record_pipeline_failure(self, *, summaries, phase, item, error, generation_prepared):
        payload = self._error_payload(item, error)
        generation = summaries[f'generated_{phase}']
        signing = summaries[f'signed_{phase}']
        if not generation_prepared:
            generation['failed'] += 1
            generation['errors'].append(payload)
        else:
            signing['failed'] += 1
            signing['errors'].append(payload)


class DGIICertificationDataTestsRunner:
    """Run DGII data tests as one sequential operation: data e-CF first, RFCE second."""

    def __init__(
        self,
        *,
        generator: DGIICertificationDocumentGenerator | None = None,
        signer: DGIICertificationDocumentSigner | None = None,
        submitter: DGIICertificationDGIISubmitter | None = None,
        rfce_rebuilder: DGIICertificationRFCERebuilder | None = None,
    ) -> None:
        self.generator = generator or DGIICertificationDocumentGenerator()
        self.signer = signer or DGIICertificationDocumentSigner()
        self.submitter = submitter or DGIICertificationDGIISubmitter()
        self.rfce_rebuilder = rfce_rebuilder or DGIICertificationRFCERebuilder(generator=self.generator, signer=self.signer)

    def run(self, *, plan: DGIICertificationPlan, user=None, environment: str | None = None) -> dict:
        phases = []
        for group_number in (1, 2):
            generated = self.generator.generate_group(plan=plan, group_number=group_number, user=user)
            phases.append({'stage': f'Preparando Grupo {group_number}', 'summary': generated})
            if generated.get('failed'):
                return self._failed(phases, f'Grupo {group_number}: error generando documentos.')
            signed = self.signer.sign_group(plan=plan, group_number=group_number, user=user)
            phases.append({'stage': f'Firmando Grupo {group_number}', 'summary': signed})
            if signed.get('failed'):
                return self._failed(phases, f'Grupo {group_number}: error firmando documentos.')

        submitted_data = self.submitter.submit_data_ecf(plan=plan, user=user, environment=environment)
        phases.append({'stage': 'Enviando 21 e-CF', 'summary': submitted_data})
        if submitted_data.get('failed') or submitted_data.get('rejected') or submitted_data.get('stopped'):
            return self._failed(phases, self._first_error(submitted_data) or 'DGII rechazo un e-CF de datos.')

        checked_data = self._check_or_count_data_ecf(plan=plan, user=user, environment=environment)
        phases.append({'stage': 'Consultando resultados 21 e-CF', 'summary': checked_data})
        data_accepted = self._accepted_count(plan, groups=(1, 2))
        if data_accepted != self.submitter.expected_data_ecf_count:
            return self._failed(phases, f'Datos e-CF no completados: {data_accepted}/21 aceptados reales.')

        rebuilt_rfce = self.rfce_rebuilder.rebuild(plan=plan, user=user)
        phases.append({'stage': 'Preparando 4 RFCE', 'summary': rebuilt_rfce})
        if rebuilt_rfce.get('failed'):
            return self._failed(phases, 'Error preparando RFCE vinculados a XML integros.')

        rfce_documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company, item__dgii_group=3)
            .order_by('item__source_row', 'id')
        )
        rfce_submit_summaries = []
        for document in rfce_documents:
            submitted_rfce = self.submitter.submit_item(
                plan=plan,
                item=document.item,
                user=user,
                environment=environment,
            )
            rfce_submit_summaries.append({'encf': document.encf, 'summary': submitted_rfce})
            if submitted_rfce.get('failed') or submitted_rfce.get('rejected') or submitted_rfce.get('stopped'):
                phases.append({'stage': 'Enviando 4 RFCE', 'summary': {'items': rfce_submit_summaries}})
                return self._failed(phases, self._first_error(submitted_rfce) or f'{document.encf}: DGII rechazo el RFCE.')

        phases.append({'stage': 'Enviando 4 RFCE', 'summary': {'items': rfce_submit_summaries}})
        checked_rfce = self._check_or_count_rfce(plan=plan, user=user, environment=environment)
        phases.append({'stage': 'Consultando resultados RFCE', 'summary': checked_rfce})
        rfce_accepted = self._accepted_count(plan, groups=(3,))
        if rfce_accepted != 4:
            return self._failed(phases, f'RFCE no completados: {rfce_accepted}/4 aceptados reales.')

        return {
            'failed': False,
            'message': 'Proceso completado.',
            'phases': phases,
            'data_ecf_accepted': data_accepted,
            'rfce_accepted': rfce_accepted,
        }

    def _check_or_count_data_ecf(self, *, plan, user, environment):
        if any(document.dgii_track_id for document in self.submitter._data_ecf_documents(plan)):
            return self.submitter.check_data_ecf_results(plan=plan, user=user, environment=environment)
        return {'checked': 0, 'accepted': self._accepted_count(plan, groups=(1, 2)), 'rejected': 0, 'failed': 0}

    def _check_or_count_rfce(self, *, plan, user, environment):
        if DGIICertificationDocument.objects.filter(plan=plan, item__dgii_group=3).exclude(dgii_track_id='').exists():
            return self.submitter.check_group_results(plan=plan, group_number=3, user=user, environment=environment)
        return {'checked': 0, 'accepted': self._accepted_count(plan, groups=(3,)), 'rejected': 0, 'failed': 0}

    def _accepted_count(self, plan: DGIICertificationPlan, *, groups: tuple[int, ...]) -> int:
        return DGIICertificationDocument.objects.filter(
            plan=plan,
            company=plan.company,
            item__dgii_group__in=groups,
            status=DGIICertificationDocument.STATUS_ACCEPTED,
            accepted_stale=False,
        ).count()

    def _failed(self, phases: list[dict], message: str) -> dict:
        return {'failed': True, 'message': message, 'phases': phases}

    def _first_error(self, summary: dict) -> str:
        errors = summary.get('errors') or []
        if not errors:
            return ''
        first = errors[0]
        return first.get('error') or first.get('message') or first.get('encf') or str(first)


@dataclass(frozen=True)
class DGIICertificationSubmitSummary:
    submitted: int
    accepted: int
    rejected: int
    sequence_already_used: int
    failed: int
    errors: list[dict]
    stopped: bool

    def as_dict(self) -> dict:
        return {
            'submitted': self.submitted,
            'accepted': self.accepted,
            'rejected': self.rejected,
            'sequence_already_used': self.sequence_already_used,
            'failed': self.failed,
            'errors': self.errors,
            'stopped': self.stopped,
        }


class DGIICertificationDGIISubmitter:
    """Send signed certification XMLs to DGII without touching productive documents."""

    enabled_groups = {1, 2, 3, 4}
    group_not_enabled_message = 'El envio automatico DGII solo esta habilitado para Datos e-CF y RFCE en esta fase.'
    isolated_group_two_message = (
        'Grupo 2 no debe enviarse aislado. Use el envio conjunto de datos e-CF '
        'para mandar Grupo 1 + Grupo 2 en el mismo ciclo.'
    )
    low_consumption_b2c_message = (
        'Las facturas de consumo menores a RD$250,000 no se envian por el endpoint e-CF normal. '
        'Despues de aceptar los RFCE, descargue los XML integros y carguelos en la seccion '
        '"Facturas de consumo <250Mil" del portal DGII.'
    )
    expected_group1_count = 18
    expected_group_counts = {1: 18, 2: 3, 3: 4, 4: 4}
    data_ecf_groups = (1, 2)
    expected_data_ecf_count = 21
    group1_order = {'31': 10, '32': 20, '41': 30, '43': 40, '44': 50, '45': 60, '46': 70, '47': 80}
    sequence_already_used_code = '1209'
    data_ecf_reset_phrase = 'las pruebas de datos de ecf han sido reiniciadas debido a que se han rechazado comprobantes'
    zero_accepted_markers = ('0 aceptados', '0/21', '0 / 21', '0/4', '0 / 4')

    def __init__(
        self,
        *,
        environment_resolver: DGIIRESTEnvironmentResolver | None = None,
        rest_client_class=None,
        parser: DGIISOAPResponseParser | None = None,
        xsd_validator: ECFXSDValidator | None = None,
        reset_service: CertificationResetService | None = None,
    ) -> None:
        self.environment_resolver = environment_resolver or DGIIRESTEnvironmentResolver()
        self.rest_client_class = rest_client_class or DGIIRESTClient
        self.parser = parser or DGIISOAPResponseParser()
        self.xsd_validator = xsd_validator or ECFXSDValidator()
        self.reset_service = reset_service or CertificationResetService()

    def submit_group(self, *, plan: DGIICertificationPlan, group_number: int, user=None, environment: str | None = None) -> dict:
        group_number = int(group_number)
        self._assert_group_enabled(group_number)
        if group_number == 2:
            raise ValueError(self.isolated_group_two_message)
        if group_number == 3:
            raise ValueError('RFCE debe enviarse individualmente hasta confirmar la estructura contra DGII.')
        if group_number == 4:
            raise ValueError(self.low_consumption_b2c_message)

        documents = self._signed_group_documents(plan, group_number)
        self._assert_group_ready(documents, group_number)
        documents_to_submit = self._documents_requiring_submission(documents)
        if not documents_to_submit:
            return DGIICertificationSubmitSummary(
                submitted=0,
                accepted=sum(1 for document in documents if document.status == DGIICertificationDocument.STATUS_ACCEPTED),
                rejected=0,
                sequence_already_used=sum(
                    1 for document in documents
                    if document.status == DGIICertificationDocument.STATUS_SUBMIT_CONFLICT
                ),
                failed=0,
                errors=[],
                stopped=False,
            ).as_dict()
        self._assert_signed_xml_matches_current_scenarios(documents_to_submit)
        self._assert_submit_payload_ready(documents_to_submit)

        return self._submit_documents(plan=plan, documents=documents_to_submit, user=user, environment=environment)

    def submit_item(self, *, plan: DGIICertificationPlan, item: DGIICertificationItem, user=None, environment: str | None = None) -> dict:
        self._assert_group_enabled(int(item.dgii_group))
        if int(item.dgii_group) == 2:
            raise ValueError(self.isolated_group_two_message)
        if int(item.dgii_group) == 4:
            raise ValueError(self.low_consumption_b2c_message)
        document = getattr(item, 'certification_document', None)
        if not document:
            raise ValueError('Este item no tiene documento de certificacion generado.')
        if document.ecf_type == 'RFCE':
            self._assert_rfce_contract_available()
        if document.status == DGIICertificationDocument.STATUS_ACCEPTED:
            return DGIICertificationSubmitSummary(
                submitted=0,
                accepted=1,
                rejected=0,
                sequence_already_used=0,
                failed=0,
                errors=[],
                stopped=False,
            ).as_dict()
        if document.status == DGIICertificationDocument.STATUS_SUBMIT_CONFLICT:
            return DGIICertificationSubmitSummary(
                submitted=0,
                accepted=0,
                rejected=0,
                sequence_already_used=1,
                failed=0,
                errors=[],
                stopped=False,
            ).as_dict()
        if not self._document_can_be_submitted(document):
            raise ValueError(f'{document.encf or item.encf}: el documento no tiene XML firmado listo para enviar.')
        self._assert_signed_xml_matches_current_scenarios([document])
        self._assert_submit_payload_ready([document])
        return self._submit_documents(plan=plan, documents=[document], user=user, environment=environment)

    def _assert_rfce_contract_available(self) -> None:
        if not has_rfce_contract():
            raise ValueError(RFCE_CONTRACT_MISSING_MESSAGE)

    def submit_data_ecf(self, *, plan: DGIICertificationPlan, user=None, environment: str | None = None) -> dict:
        documents = self._data_ecf_documents(plan)
        self._assert_data_ecf_ready(documents)
        self._assert_signed_xml_matches_current_scenarios(documents)
        self._assert_submit_payload_ready(documents)
        return self._submit_documents(plan=plan, documents=documents, user=user, environment=environment)

    def _submit_documents(
        self,
        *,
        plan: DGIICertificationPlan,
        documents: list[DGIICertificationDocument],
        user=None,
        environment: str | None = None,
    ) -> dict:
        self._assert_documents_not_claimed(documents)
        issuer = DGIICertificationDocumentGenerator()._resolve_issuer(plan.company)
        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        if not certificate_path:
            raise ValueError('El emisor fiscal no tiene certificado DGII disponible para enviar a DGII.')
        issuer_rnc = digits_only(issuer.rnc) or issuer.rnc

        environment_config = self.environment_resolver.resolve(environment)
        client = self.rest_client_class(environment=environment_config)

        submitted = accepted = rejected = sequence_already_used = failed = 0
        errors: list[dict] = []
        stopped = False

        for document in documents:
            try:
                if document.status == DGIICertificationDocument.STATUS_SUBMIT_ERROR:
                    self._reset_submit_error_for_retry(document, user)
                signed_xml = self._read_signed_xml(document)
                multipart_filename = self._multipart_filename_for(document, issuer_rnc=issuer_rnc)
                submit_method = client.submit_rfce if document.ecf_type == 'RFCE' else client.submit_ecf
                result = submit_method(
                    signed_xml_content=signed_xml,
                    encf=document.encf,
                    issuer_rnc=issuer_rnc,
                    certificate_path=certificate_path,
                    certificate_password=certificate_password,
                    filename=multipart_filename,
                )
                parsed = self.parser.parse_submission(result.result)
                normalized_status = self._normalize_submission_status(parsed.status, parsed.code)
                if normalized_status == DGIICertificationDocument.STATUS_REJECTED:
                    if self._is_sequence_already_used(parsed, result.result):
                        self._mark_sequence_already_used(document, parsed, result.result, user)
                        sequence_already_used += 1
                        continue
                    self._mark_rejected(document, parsed, result.result, user)
                    rejected += 1
                    stopped = True
                    errors.append(self._error_payload(document, 'DGII rechazo el documento.'))
                    break
                if normalized_status == DGIICertificationDocument.STATUS_ACCEPTED:
                    self._mark_accepted(document, parsed, result.result, user)
                    accepted += 1
                    continue
                if not parsed.track_id:
                    raise ECFValidationError('DGII no retorno TrackID para el envio de certificacion.')
                self._mark_submitted(document, parsed, result.result, user)
                submitted += 1
            except Exception as exc:  # noqa: BLE001 - converts DGII/network/parser errors into audited state.
                diagnostics = self._safe_error_diagnostics(exc, document)
                self._mark_submit_error(document, str(exc), user, diagnostics)
                failed += 1
                stopped = True
                errors.append(self._error_payload(document, str(exc), diagnostics))
                break

        return DGIICertificationSubmitSummary(
            submitted=submitted,
            accepted=accepted,
            rejected=rejected,
            sequence_already_used=sequence_already_used,
            failed=failed,
            errors=errors,
            stopped=stopped,
        ).as_dict()

    def check_group_results(self, *, plan: DGIICertificationPlan, group_number: int, user=None, environment: str | None = None) -> dict:
        group_number = int(group_number)
        self._assert_group_enabled(group_number)

        documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company, item__dgii_group=group_number)
            .exclude(dgii_track_id='')
            .order_by('item__source_row', 'id')
        )
        return self._check_documents_results(
            plan=plan,
            documents=documents,
            user=user,
            environment=environment,
            scope_groups=(group_number,),
        )

    def check_data_ecf_results(self, *, plan: DGIICertificationPlan, user=None, environment: str | None = None) -> dict:
        return self._check_documents_results(
            plan=plan,
            documents=[
                document for document in self._data_ecf_documents(plan)
                if document.dgii_track_id
            ],
            user=user,
            environment=environment,
            scope_groups=self.data_ecf_groups,
        )

    def _check_documents_results(
        self,
        *,
        plan: DGIICertificationPlan,
        documents: list[DGIICertificationDocument],
        user=None,
        environment: str | None = None,
        scope_groups: tuple[int, ...] | None = None,
    ) -> dict:
        if not documents:
            raise ValueError('No hay TrackID para consultar resultados DGII.')

        issuer = DGIICertificationDocumentGenerator()._resolve_issuer(plan.company)
        certificate_path, certificate_password = resolve_certificate_credentials(issuer)
        if not certificate_path:
            raise ValueError('El emisor fiscal no tiene certificado DGII disponible para consultar resultados.')

        environment_config = self.environment_resolver.resolve(environment)
        client = self.rest_client_class(environment=environment_config)

        checked = accepted = rejected = sequence_already_used = failed = 0
        errors: list[dict] = []
        had_current_acceptances = any(
            document.status == DGIICertificationDocument.STATUS_ACCEPTED and not document.accepted_stale
            for document in documents
        )
        current_acceptance_ids = [
            document.id
            for document in documents
            if document.status == DGIICertificationDocument.STATUS_ACCEPTED and not document.accepted_stale
        ]
        for document in documents:
            try:
                result = client.query_status(
                    track_id=document.dgii_track_id,
                    issuer_rnc=digits_only(issuer.rnc) or issuer.rnc,
                    certificate_path=certificate_path,
                    certificate_password=certificate_password,
                )
                parsed = self.parser.parse_status(result.result)
                checked += 1
                if parsed.normalized_status == 'accepted':
                    self._mark_accepted(document, parsed, result.result, user, event_type=DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED)
                    accepted += 1
                elif parsed.normalized_status == 'rejected':
                    if self._is_sequence_already_used(parsed, result.result):
                        self._mark_sequence_already_used(document, parsed, result.result, user, event_type=DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED)
                        sequence_already_used += 1
                    else:
                        self._mark_rejected(document, parsed, result.result, user, event_type=DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED)
                        rejected += 1
                else:
                    self._update_dgii_response(
                        document,
                        status=DGIICertificationDocument.STATUS_SUBMITTED,
                        dgii_status=parsed.status,
                        track_id=parsed.track_id or document.dgii_track_id,
                        response_code=parsed.code,
                        response_message=self._message_from(parsed.messages) or parsed.status,
                        response_payload=result.result,
                        user=user,
                        event_type=DGIICertificationEvent.EVENT_DOCUMENT_STATUS_CHECKED,
                        event_message='Resultado DGII consultado para documento de certificacion.',
                    )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append(self._error_payload(document, str(exc)))
                self._event(
                    document,
                    DGIICertificationEvent.EVENT_DOCUMENT_SUBMIT_ERROR,
                    f'Error consultando resultado DGII: {exc}',
                    user,
                    {'track_id': document.dgii_track_id},
                )

        stale_marked = 0
        reset_diagnostic = None
        if checked and accepted == 0 and had_current_acceptances and scope_groups:
            reset_diagnostic = {
                'possible_reset': True,
                'authoritative': False,
                'reason': 'DGII reportó cero aceptados; requiere confirmación autoritativa antes del reset.',
                'groups': list(scope_groups),
                'document_ids': current_acceptance_ids,
            }

        return {
            'checked': checked,
            'accepted': accepted,
            'rejected': rejected,
            'sequence_already_used': sequence_already_used,
            'failed': failed,
            'needs_resubmit': stale_marked,
            'reset_diagnostic': reset_diagnostic,
            'errors': errors,
        }

    def _signed_group_documents(self, plan: DGIICertificationPlan, group_number: int) -> list[DGIICertificationDocument]:
        documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company, item__dgii_group=group_number)
            .order_by('item__source_row', 'id')
        )
        if int(group_number) != 1:
            return documents
        return sorted(documents, key=lambda doc: (
            self.group1_order.get(doc.ecf_type, 999),
            doc.item.amount or Decimal('0'),
            doc.item.source_row,
            doc.id,
        ))

    def _data_ecf_documents(self, plan: DGIICertificationPlan) -> list[DGIICertificationDocument]:
        documents = []
        for group_number in self.data_ecf_groups:
            documents.extend(self._signed_group_documents(plan, group_number))
        return documents

    def _assert_group_enabled(self, group_number: int) -> None:
        if group_number not in self.enabled_groups:
            raise ValueError(self.group_not_enabled_message)

    def _assert_group_ready(self, documents: list[DGIICertificationDocument], group_number: int) -> None:
        expected_count = self.expected_group_counts[group_number]
        if len(documents) != expected_count:
            raise ValueError(
                f'Grupo {group_number} debe tener {expected_count} documentos firmados antes de enviar.'
            )
        missing = [
            document.encf or f'item-{document.item_id}'
            for document in documents
            if document.status not in {
                DGIICertificationDocument.STATUS_ACCEPTED,
                DGIICertificationDocument.STATUS_SUBMIT_CONFLICT,
            } and not self._document_can_be_submitted(document)
        ]
        if missing:
            raise ValueError(f'Grupo {group_number} tiene documentos sin XML firmado: {", ".join(missing[:5])}.')

    def _assert_data_ecf_ready(self, documents: list[DGIICertificationDocument]) -> None:
        if len(documents) != self.expected_data_ecf_count:
            raise ValueError(
                f'El envio conjunto debe tener {self.expected_data_ecf_count} documentos firmados '
                '(18 del Grupo 1 + 3 del Grupo 2).'
            )
        missing = [
            document.encf or f'item-{document.item_id}'
            for document in documents
            if not self._document_has_signed_xml(document)
        ]
        if missing:
            raise ValueError(f'El envio conjunto tiene documentos sin XML firmado: {", ".join(missing[:5])}.')

    def _reset_previous_dgii_results(self, documents: list[DGIICertificationDocument], user) -> None:
        """Legacy compatibility hook: submission must never reset fiscal evidence."""
        return None

    def _documents_requiring_submission(self, documents: list[DGIICertificationDocument]) -> list[DGIICertificationDocument]:
        return [
            document
            for document in documents
            if document.status not in {
                DGIICertificationDocument.STATUS_ACCEPTED,
                DGIICertificationDocument.STATUS_SUBMIT_CONFLICT,
            }
        ]

    def _assert_signed_xml_matches_current_scenarios(self, documents: list[DGIICertificationDocument]) -> None:
        for document in documents:
            signed_xml = self._read_signed_xml(document)
            signed_values = self._extract_xml_values(signed_xml)
            expected_values = self._extract_xml_values(document.xml_content)
            for key in (
                'RNCComprador',
                'IdentificadorExtranjero',
                'RazonSocialComprador',
                'FechaVencimientoSecuencia',
                'NumeroFacturaInterna',
                'MontoTotal',
            ):
                if (signed_values.get(key) or '') != (expected_values.get(key) or ''):
                    raise ValueError(
                        f'XML firmado de {document.encf} no coincide con el escenario vigente en {key}. '
                        'Regenera y firma el grupo antes de enviarlo.'
                    )

    def inspect_submit_payload(self, *, plan: DGIICertificationPlan, group_number: int) -> list[dict]:
        diagnostics = []
        documents = self._signed_group_documents(plan, group_number)
        for document in documents:
            diagnostics.append(self._inspect_document_submit_payload(document))
        return diagnostics

    def _assert_submit_payload_ready(self, documents: list[DGIICertificationDocument]) -> None:
        errors = []
        for document in documents:
            diagnostic = self._inspect_document_submit_payload(document)
            errors.extend(diagnostic.get('errors', []))
            try:
                self._validate_signed_xml_against_xsd(document)
            except Exception as exc:  # noqa: BLE001 - preflight reports every validation problem together.
                errors.append(f'{document.encf}: XML firmado no valida contra XSD DGII: {exc}')
        if errors:
            preview = '; '.join(errors[:5])
            raise ValueError(
                'Preflight DGII fallo: los XML firmados no estan listos para enviarse. '
                f'{preview}'
            )

    def _validate_signed_xml_against_xsd(self, document: DGIICertificationDocument) -> None:
        if not getattr(settings, 'ECF_DGII_CERTIFICATION_XSD_PREFLIGHT_REQUIRED', True):
            return
        signed_xml = self._read_signed_xml(document)
        self.xsd_validator.validate(document.ecf_type, signed_xml)

    def _inspect_document_submit_payload(self, document: DGIICertificationDocument) -> dict:
        errors = []
        signed_xml = ''
        size_bytes = 0
        sha256 = ''
        values = {
            'RNCEmisor': '',
            'CodigoVendedor': '',
            'NumeroFacturaInterna': '',
            'RNCComprador': '',
            'IdentificadorExtranjero': '',
            'NCFModificado': '',
        }

        if not document.signed_xml_path:
            errors.append(f'{document.encf}: no tiene signed_xml_path.')
        elif not default_storage.exists(document.signed_xml_path):
            errors.append(f'{document.encf}: signed_xml_path no existe en storage.')
        else:
            with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
                content = signed_file.read()
            size_bytes = len(content)
            sha256 = hashlib.sha256(content).hexdigest()
            signed_xml = content.decode('utf-8')
            try:
                values = self._extract_xml_values(signed_xml)
            except Exception as exc:  # noqa: BLE001 - diagnostic/preflight must report a clean error.
                errors.append(f'{document.encf}: XML firmado no se pudo parsear: {exc}.')

        rnc_emisor = digits_only(values.get('RNCEmisor')) or values.get('RNCEmisor', '')
        expected_filename = self._multipart_filename_for(document, issuer_rnc=rnc_emisor)
        filename_sent = self._multipart_filename_for(document, issuer_rnc=rnc_emisor)
        if filename_sent != expected_filename:
            errors.append(f'{document.encf}: filename multipart {filename_sent!r} no coincide con {expected_filename!r}.')
        if not rnc_emisor:
            errors.append(f'{document.encf}: no se pudo leer RNCEmisor del XML firmado.')
        if values.get('NumeroFacturaInterna') == DGII_CERTIFICATION_REJECTED_INTERNAL_INVOICE:
            errors.append(f'{document.encf}: NumeroFacturaInterna contiene valor rechazado AA000...')
        rfce_payload = self._rfce_payload_diagnostics(document, signed_xml, rnc_emisor) if document.ecf_type == 'RFCE' else {}
        contains_long_seller_code = DGII_CERTIFICATION_REJECTED_INTERNAL_INVOICE in signed_xml
        contains_expected_invoice = '123456789016' in signed_xml
        modified_encf = values.get('NCFModificado', '')
        origin_document = None
        if modified_encf:
            origin_document = (
                DGIICertificationDocument.objects
                .filter(plan=document.plan, company=document.company, encf=modified_encf)
                .select_related('item')
                .first()
            )

        return {
            'encf': document.encf,
            'ecf_type': document.ecf_type,
            'signed_xml_path': document.signed_xml_path,
            'issuer_rnc': rnc_emisor,
            'multipart_filename': filename_sent,
            'expected_filename': expected_filename,
            'filename_length': len(filename_sent),
            'size_bytes': size_bytes,
            'sha256': sha256,
            'CodigoVendedor': values.get('CodigoVendedor', ''),
            'NumeroFacturaInterna': values.get('NumeroFacturaInterna', ''),
            'RNCComprador': values.get('RNCComprador', ''),
            'IdentificadorExtranjero': values.get('IdentificadorExtranjero', ''),
            'NCFModificado': modified_encf,
            'origin_document_id': origin_document.id if origin_document else None,
            'origin_document_status': origin_document.status if origin_document else '',
            'origin_document_dgii_status': origin_document.dgii_status if origin_document else '',
            'contains_long_seller_code': contains_long_seller_code,
            'contains_expected_internal_invoice': contains_expected_invoice,
            **({'rfce_payload': rfce_payload} if rfce_payload else {}),
            'errors': errors,
        }

    def _rfce_payload_diagnostics(self, document: DGIICertificationDocument, signed_xml: str, issuer_rnc: str) -> dict:
        first_node = ''
        declared_type = ''
        try:
            root = ET.fromstring(signed_xml.encode('utf-8'))
            first_node = root.tag.split('}', 1)[-1]
            declared_type = self._find_text(root, 'TipoeCF')
        except Exception:  # noqa: BLE001 - diagnostic only.
            pass
        environment_config = self.environment_resolver.resolve()
        paths = getattr(settings, 'ECF_DGII_REST_PATHS', {})
        rfce_path = paths.get('rfce', DGIIRESTClient.rfce_path)
        url = f"{environment_config.rfce_base_url.rstrip('/')}{rfce_path}" if environment_config.rfce_base_url else ''
        return {
            'url': url,
            'method': 'POST',
            'multipart_field': getattr(settings, 'ECF_DGII_RFCE_MULTIPART_FIELD', 'xml'),
            'multipart_filename': self._multipart_filename_for(document, issuer_rnc=issuer_rnc),
            'content_type': getattr(settings, 'ECF_DGII_RFCE_CONTENT_TYPE', 'text/xml'),
            'xml_size_bytes': len(signed_xml.encode('utf-8')),
            'first_xml_node': first_node,
            'includes_signature': '<Signature' in signed_xml or '<ds:Signature' in signed_xml,
            'encf': document.encf,
            'declared_type': declared_type,
        }

    def _read_signed_xml(self, document: DGIICertificationDocument) -> str:
        with default_storage.open(document.signed_xml_path, 'rb') as signed_file:
            return signed_file.read().decode('utf-8')

    def _extract_xml_values(self, xml_text: str) -> dict[str, str]:
        root = ET.fromstring(xml_text.encode('utf-8'))
        return {
            'RNCEmisor': self._find_text(root, 'RNCEmisor'),
            'CodigoVendedor': self._find_text(root, 'CodigoVendedor'),
            'RNCComprador': self._find_text(root, 'RNCComprador'),
            'IdentificadorExtranjero': self._find_text(root, 'IdentificadorExtranjero'),
            'RazonSocialComprador': self._find_text(root, 'RazonSocialComprador'),
            'FechaVencimientoSecuencia': self._find_text(root, 'FechaVencimientoSecuencia'),
            'NumeroFacturaInterna': self._find_text(root, 'NumeroFacturaInterna'),
            'NCFModificado': self._find_text(root, 'NCFModificado'),
            'MontoTotal': self._find_text(root, 'MontoTotal'),
        }

    def _multipart_filename_for(self, document: DGIICertificationDocument, *, issuer_rnc: str | None = None) -> str:
        clean_rnc = digits_only(issuer_rnc or '')
        return f'{clean_rnc}{document.encf}.xml' if clean_rnc else f'{document.encf}.xml'

    def _find_text(self, root: ET.Element, tag: str) -> str:
        for node in root.iter():
            if node.tag.split('}')[-1] == tag:
                return (node.text or '').strip()
        return ''

    def _normalize_submission_status(self, status: str, code) -> str:
        normalized = self.parser.normalize_status(status, code)
        if normalized == 'accepted':
            return DGIICertificationDocument.STATUS_ACCEPTED
        if normalized == 'rejected':
            return DGIICertificationDocument.STATUS_REJECTED
        return DGIICertificationDocument.STATUS_SUBMITTED

    def _mark_submitted(self, document, parsed, response_payload, user) -> None:
        self._update_dgii_response(
            document,
            status=DGIICertificationDocument.STATUS_SUBMITTED,
            dgii_status=parsed.status,
            track_id=parsed.track_id,
            response_code=parsed.code,
            response_message=self._message_from(parsed.messages) or 'Documento enviado a DGII.',
            response_payload=response_payload,
            user=user,
            event_type=DGIICertificationEvent.EVENT_DOCUMENT_SUBMITTED,
            event_message='Documento de certificacion enviado a DGII.',
        )

    def _mark_accepted(self, document, parsed, response_payload, user, event_type=None) -> None:
        self._update_dgii_response(
            document,
            status=DGIICertificationDocument.STATUS_ACCEPTED,
            dgii_status=getattr(parsed, 'status', 'Aceptado'),
            track_id=getattr(parsed, 'track_id', None) or document.dgii_track_id,
            response_code=getattr(parsed, 'code', None),
            response_message=self._message_from(getattr(parsed, 'messages', [])) or 'Documento aceptado por DGII.',
            response_payload=response_payload,
            user=user,
            event_type=event_type or DGIICertificationEvent.EVENT_DOCUMENT_ACCEPTED,
            event_message='Documento de certificacion aceptado por DGII.',
            accepted=True,
        )

    def _mark_sequence_already_used(self, document, parsed, response_payload, user, event_type=None) -> None:
        self._update_dgii_response(
            document,
            status=DGIICertificationDocument.STATUS_SUBMIT_CONFLICT,
            dgii_status='Secuencia ya usada',
            track_id=getattr(parsed, 'track_id', None) or document.dgii_track_id,
            response_code=self.sequence_already_used_code,
            response_message=(
                'DGII indica que la secuencia ya fue utilizada; no cuenta como aceptada real. '
                f'{self._message_from(getattr(parsed, "messages", []))}'
            ),
            response_payload=response_payload,
            user=user,
            event_type=event_type or DGIICertificationEvent.EVENT_DOCUMENT_REJECTED,
            event_message='Documento de certificacion marcado con conflicto por secuencia ya utilizada en DGII.',
        )

    def _mark_rejected(self, document, parsed, response_payload, user, event_type=None) -> None:
        self._update_dgii_response(
            document,
            status=DGIICertificationDocument.STATUS_REJECTED,
            dgii_status=getattr(parsed, 'status', 'Rechazado'),
            track_id=getattr(parsed, 'track_id', None) or document.dgii_track_id,
            response_code=getattr(parsed, 'code', None),
            response_message=self._message_from(getattr(parsed, 'messages', [])) or 'Documento rechazado por DGII.',
            response_payload=response_payload,
            user=user,
            event_type=event_type or DGIICertificationEvent.EVENT_DOCUMENT_REJECTED,
            event_message='Documento de certificacion rechazado por DGII.',
            rejected=True,
        )

    def _mark_submit_error(self, document, error: str, user, diagnostics: dict | None = None) -> None:
        now = timezone.now()
        if diagnostics:
            error = f"{error} Detalle DGII: {json.dumps(diagnostics, ensure_ascii=False)}"
        document.status = DGIICertificationDocument.STATUS_SUBMIT_ERROR
        document.submit_error = error
        if diagnostics:
            document.dgii_response = diagnostics
            document.dgii_response_code = str(diagnostics.get('status_code') or diagnostics.get('response_code') or '')
            document.dgii_response_message = diagnostics.get('response_text') or diagnostics.get('error') or ''
        document.save(update_fields=[
            'status',
            'submit_error',
            'dgii_response',
            'dgii_response_code',
            'dgii_response_message',
            'updated_at',
        ])
        document.item.status = DGIICertificationItem.STATUS_SUBMIT_ERROR
        document.item.generation_error = error
        document.item.save(update_fields=['status', 'generation_error', 'updated_at'])
        self._event(
            document,
            DGIICertificationEvent.EVENT_DOCUMENT_SUBMIT_ERROR,
            error,
            user,
            self._submission_audit_payload(
                document,
                {
                    'submitted_at': now.isoformat(),
                    'encf': document.encf,
                    'dgii_error': diagnostics or {},
                },
            ),
        )
        self._invalidate_data_ecf_if_reset_detected(
            trigger_document=document,
            user=user,
            response_payload=diagnostics or {},
            message=error,
        )

    def _reset_submit_error_for_retry(self, document: DGIICertificationDocument, user) -> None:
        previous_error = document.submit_error or ''
        document.status = DGIICertificationDocument.STATUS_SIGNED
        document.submit_error = ''
        document.item.status = DGIICertificationItem.STATUS_SIGNED
        document.item.generation_error = ''
        document.save(update_fields=['status', 'submit_error', 'updated_at'])
        document.item.save(update_fields=['status', 'generation_error', 'updated_at'])
        self._event(
            document,
            DGIICertificationEvent.EVENT_DOCUMENT_SUBMIT_ERROR,
            'Reintentando envio DGII de documento con error previo.',
            user,
            {
                'encf': document.encf,
                'previous_error': previous_error[:2000],
                'retry': True,
            },
        )

    def _update_dgii_response(
        self,
        document,
        *,
        status: str,
        dgii_status: str,
        track_id: str | None,
        response_code,
        response_message: str,
        response_payload,
        user,
        event_type: str,
        event_message: str,
        accepted: bool = False,
        rejected: bool = False,
    ) -> None:
        now = timezone.now()
        document.status = status
        document.dgii_track_id = track_id or ''
        document.dgii_status = str(dgii_status or '')
        document.dgii_response_code = '' if response_code is None else str(response_code)
        document.dgii_response_message = response_message or ''
        document.dgii_response = response_payload
        document.submit_error = ''
        if not document.submitted_at:
            document.submitted_at = now
        if accepted:
            document.accepted_at = now
            document.rejected_at = None
            document.accepted_stale = False
            document.stale_reason = ''
            document.stale_at = None
        if rejected:
            document.rejected_at = now
        document.save(update_fields=[
            'status',
            'dgii_track_id',
            'dgii_status',
            'dgii_response_code',
            'dgii_response_message',
            'dgii_response',
            'submit_error',
            'submitted_at',
            'accepted_at',
            'rejected_at',
            'accepted_stale',
            'stale_reason',
            'stale_at',
            'updated_at',
        ])
        document.item.status = self._item_status_for_document(status)
        document.item.generation_error = ''
        document.item.save(update_fields=['status', 'generation_error', 'updated_at'])
        self._event(
            document,
            event_type,
            event_message,
            user,
            self._submission_audit_payload(
                document,
                {
                    'track_id': document.dgii_track_id,
                    'dgii_status': document.dgii_status,
                    'code': document.dgii_response_code,
                    'message': document.dgii_response_message,
                    'dgii_response': document.dgii_response,
                },
            ),
        )
        self._invalidate_data_ecf_if_reset_detected(
            trigger_document=document,
            user=user,
            response_payload=response_payload,
            message=response_message,
        )

    def _invalidate_data_ecf_if_reset_detected(
        self,
        *,
        trigger_document: DGIICertificationDocument,
        user,
        response_payload=None,
        message: str = '',
    ) -> int:
        if not self._response_is_authoritative_reset(message, response_payload):
            return 0
        reason = message or 'DGII reinicio las pruebas de datos eCF.'
        evidence = self._reset_evidence(trigger_document, message, response_payload)
        data_stale = self.reset_service.apply_reset(
            plan_id=trigger_document.plan_id,
            groups=self.data_ecf_groups,
            source=CertificationResetService.SOURCE_AUTOMATIC,
            reason=reason,
            evidence=evidence,
            actor=user,
        ).applied
        rfce_stale = 0
        if int(trigger_document.item.dgii_group) == 3:
            rfce_stale = self.reset_service.apply_reset(
                plan_id=trigger_document.plan_id,
                groups=(3,),
                source=CertificationResetService.SOURCE_AUTOMATIC,
                reason=reason,
                evidence=evidence,
                actor=user,
            ).applied
        return data_stale + rfce_stale

    def mark_data_ecf_acceptances_stale(
        self,
        *,
        plan: DGIICertificationPlan,
        user=None,
        reason: str = '',
        trigger_document: DGIICertificationDocument | None = None,
        response_payload=None,
        evidence=None,
        confirmed: bool = False,
    ) -> int:
        return self.mark_acceptances_stale(
            plan=plan,
            groups=self.data_ecf_groups,
            user=user,
            reason=reason or 'Las pruebas de datos de eCF fueron reiniciadas por DGII.',
            trigger_document=trigger_document,
            response_payload=response_payload,
            evidence=evidence,
            confirmed=confirmed,
        )

    def mark_acceptances_stale(
        self,
        *,
        plan: DGIICertificationPlan,
        groups: tuple[int, ...],
        document_ids: list[int] | None = None,
        user=None,
        reason: str = '',
        trigger_document: DGIICertificationDocument | None = None,
        response_payload=None,
        evidence=None,
        confirmed: bool = False,
    ) -> int:
        if document_ids is not None:
            raise ValueError('El reset seguro no admite scopes documentales parciales.')
        manual_evidence = evidence if evidence is not None else response_payload
        result = self.reset_service.apply_reset(
            plan_id=plan.pk,
            groups=groups,
            source=CertificationResetService.SOURCE_MANUAL,
            reason=reason or 'Las pruebas de certificación DGII fueron reiniciadas.',
            evidence=manual_evidence,
            actor=user,
            confirmed=confirmed,
        )
        return result.applied

    def sync_reset_state_from_stored_responses(self, *, plan: DGIICertificationPlan, user=None) -> dict:
        candidates = []
        seen = set()
        documents = list(
            DGIICertificationDocument.objects
            .select_related('item')
            .filter(plan=plan, company=plan.company)
            .order_by('item__dgii_group', 'item__source_row', 'id')
        )
        for document in documents:
            if not self._response_indicates_data_ecf_reset(
                document.dgii_response_message,
                document.submit_error,
                document.dgii_response,
            ):
                continue
            reason = document.dgii_response_message or document.submit_error or 'DGII reinicio pruebas de certificacion.'
            evidence = self._reset_evidence(
                document, reason, document.dgii_response,
            )
            scopes = [self.data_ecf_groups]
            if int(document.item.dgii_group) == 3:
                scopes.append((3,))
            for groups in scopes:
                reset_key = self.reset_service.build_reset_key(
                    plan_id=plan.pk,
                    groups=groups,
                    source=CertificationResetService.SOURCE_AUTOMATIC,
                    reason=reason,
                    evidence=evidence,
                )
                if reset_key in seen:
                    continue
                seen.add(reset_key)
                applied = DGIICertificationEvent.objects.filter(
                    plan=plan,
                    event_type=CertificationResetService.EVENT_DGII_RESET_APPLIED,
                    payload__reset_key=reset_key,
                ).exists()
                candidates.append({
                    'reset_key': reset_key,
                    'groups': list(groups),
                    'reason': reason,
                    'trigger_document_id': document.pk,
                    'authoritative_signal': self._response_is_authoritative_reset(
                        document.dgii_response_message,
                        document.submit_error,
                        document.dgii_response,
                    ),
                    'already_applied': applied,
                })
        return {
            'data_ecf_marked': 0,
            'rfce_marked': 0,
            'total_marked': 0,
            'possible_resets': len(candidates),
            'already_applied': sum(candidate['already_applied'] for candidate in candidates),
            'candidates': candidates,
        }

    @staticmethod
    def _reset_evidence(document, message, response_payload):
        return {
            'trigger_document_id': document.pk,
            'message': message or '',
            'response_payload': response_payload,
        }

    def _response_is_authoritative_reset(self, *values) -> bool:
        text_parts = []
        for value in values:
            if value is None:
                continue
            text_parts.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else str(value))
        normalized = unicodedata.normalize('NFKD', ' '.join(text_parts).lower())
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r'\s+', ' ', normalized)
        return self.data_ecf_reset_phrase in normalized

    def _response_indicates_data_ecf_reset(self, *values) -> bool:
        text_parts = []
        for value in values:
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple)):
                text_parts.append(json.dumps(value, ensure_ascii=False))
            else:
                text_parts.append(str(value))
        normalized = unicodedata.normalize('NFKD', ' '.join(text_parts).lower())
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r'\s+', ' ', normalized)
        return (
            self.data_ecf_reset_phrase in normalized
            or any(marker in normalized for marker in self.zero_accepted_markers)
        )

    def _submission_audit_payload(self, document: DGIICertificationDocument, extra: dict | None = None) -> dict:
        try:
            diagnostic = self._inspect_document_submit_payload(document)
        except Exception:  # noqa: BLE001 - audit must not mask the real DGII result.
            diagnostic = {}
        return {
            'encf': document.encf,
            'ecf_type': document.ecf_type,
            'multipart_filename': diagnostic.get('multipart_filename'),
            'track_id': document.dgii_track_id,
            'signed_xml_path': document.signed_xml_path,
            'signed_xml_hash': document.signed_xml_hash or diagnostic.get('sha256'),
            **(extra or {}),
        }

    def _item_status_for_document(self, document_status: str) -> str:
        return {
            DGIICertificationDocument.STATUS_SUBMITTED: DGIICertificationItem.STATUS_SENT,
            DGIICertificationDocument.STATUS_ACCEPTED: DGIICertificationItem.STATUS_ACCEPTED,
            DGIICertificationDocument.STATUS_REJECTED: DGIICertificationItem.STATUS_REJECTED,
            DGIICertificationDocument.STATUS_SUBMIT_ERROR: DGIICertificationItem.STATUS_SUBMIT_ERROR,
            DGIICertificationDocument.STATUS_SUBMIT_CONFLICT: DGIICertificationItem.STATUS_SUBMIT_CONFLICT,
        }.get(document_status, DGIICertificationItem.STATUS_SIGNED)

    def _event(self, document, event_type: str, message: str, user, payload: dict | None = None) -> None:
        DGIICertificationEvent.objects.create(
            company=document.company,
            plan=document.plan,
            item=document.item,
            event_type=event_type,
            message=message,
            payload={
                'certification_document_id': document.id,
                'ecf_type': document.ecf_type,
                'dgii_group': document.item.dgii_group,
                'encf': document.encf,
                **(payload or {}),
            },
            created_by=user,
        )

    def _message_from(self, messages) -> str:
        if not messages:
            return ''
        if isinstance(messages, str):
            return messages
        return '; '.join(str(message) for message in messages if message)

    def _is_sequence_already_used(self, parsed, response_payload) -> bool:
        code = str(getattr(parsed, 'code', '') or '')
        message = self._message_from(getattr(parsed, 'messages', []))
        if isinstance(response_payload, dict):
            message = f"{message} {json.dumps(response_payload, ensure_ascii=False)}"
        normalized_message = message.lower()
        return (
            code == self.sequence_already_used_code
            or 'secuencia ya ha sido utilizado' in normalized_message
            or 'número de secuencia ya ha sido utilizado' in normalized_message
            or 'numero de secuencia ya ha sido utilizado' in normalized_message
        )

    def _document_can_be_submitted(self, document: DGIICertificationDocument) -> bool:
        if document.status not in {
            DGIICertificationDocument.STATUS_SIGNED,
            DGIICertificationDocument.STATUS_SUBMIT_ERROR,
        }:
            return False
        return self._document_has_signed_xml(document)

    @staticmethod
    def _assert_documents_not_claimed(documents: list[DGIICertificationDocument]) -> None:
        claimed = [
            document.encf or str(document.pk)
            for document in documents
            if document.submission_outcome
            == DGIICertificationDocument.SUBMISSION_OUTCOME_CLAIMED
        ]
        if claimed:
            raise ValueError(
                "El envío está reclamado localmente y aún no puede despacharse: "
                f"{', '.join(claimed[:5])}."
            )

    def _document_has_signed_xml(self, document: DGIICertificationDocument) -> bool:
        return bool(document.signed_xml_path and default_storage.exists(document.signed_xml_path))

    def _safe_error_diagnostics(self, exc: Exception, document: DGIICertificationDocument) -> dict:
        if isinstance(exc, DGIIRESTHTTPError):
            payload = exc.as_safe_payload()
        else:
            payload = {}
        if document.ecf_type == 'RFCE':
            try:
                signed_xml = self._read_signed_xml(document)
                values = self._extract_xml_values(signed_xml)
                issuer_rnc = digits_only(values.get('RNCEmisor')) or values.get('RNCEmisor', '')
                payload['rfce_payload'] = self._rfce_payload_diagnostics(document, signed_xml, issuer_rnc)
            except Exception as diag_exc:  # noqa: BLE001 - diagnostics must stay best-effort.
                payload['rfce_payload_error'] = str(diag_exc)
        payload.setdefault("encf", document.encf)
        payload.setdefault("ecf_type", document.ecf_type)
        return payload

    def _error_payload(self, document, error: str, diagnostics: dict | None = None) -> dict:
        payload = {
            'item_id': document.item_id,
            'document_id': document.id,
            'ecf_type': document.ecf_type,
            'encf': document.encf,
            'error': error,
        }
        if diagnostics:
            payload['dgii_error'] = diagnostics
        return payload


def _clean_scenario_value(value) -> str:
    text = str(value or '').strip()
    if not text:
        return ''
    normalized = _normalize_text(text)
    if normalized in {'#e', 'e', 'n/a', 'na', 'null', 'none', 'no aplica'}:
        return ''
    return text
