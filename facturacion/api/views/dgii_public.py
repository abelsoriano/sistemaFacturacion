import hashlib
import json
import re
import uuid

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from facturacion.models import DGIIPublicRequestLog


MAX_PUBLIC_DGII_PAYLOAD_BYTES = 2 * 1024 * 1024
BODY_PREVIEW_BYTES = 512
ALLOWED_POST_CONTENT_TYPES = (
    'application/json',
    'application/xml',
    'text/xml',
    'text/plain',
    'application/x-www-form-urlencoded',
)
SENSITIVE_HEADER_PARTS = ('authorization', 'cookie', 'token', 'secret', 'password', 'key')
SENSITIVE_BODY_PATTERNS = (
    re.compile(r'(?i)(password|token|secret|certificado|certificate)\s*[:=]\s*["\']?[^"\'<>&\s]+'),
    re.compile(r'(?is)<(password|token|secret|certificado|certificate)[^>]*>.*?</\1>'),
)
RNC_PATTERN = re.compile(r'(?<!\d)(\d{9}|\d{11})(?!\d)')


def _json_response(payload, status=200):
    return JsonResponse(payload, status=status, json_dumps_params={'ensure_ascii': False})


def _safe_headers(request):
    headers = {}
    for key, value in request.headers.items():
        lowered = key.lower()
        if any(part in lowered for part in SENSITIVE_HEADER_PARTS):
            headers[key] = '[redacted]'
        else:
            headers[key] = str(value)[:200]
    return headers


def _remote_addr(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def _decode_preview(body):
    preview = body[:BODY_PREVIEW_BYTES].decode('utf-8', errors='replace')
    for pattern in SENSITIVE_BODY_PATTERNS:
        preview = pattern.sub('[redacted]', preview)
    return preview


def _extract_rnc(body):
    text = body[:4096].decode('utf-8', errors='ignore')
    match = RNC_PATTERN.search(text)
    return match.group(1) if match else ''


def _audit_request(request, *, endpoint, response_status, error=''):
    body = getattr(request, 'body', b'') or b''
    DGIIPublicRequestLog.objects.create(
        endpoint=endpoint,
        method=request.method,
        content_type=(request.headers.get('Content-Type') or '').split(';')[0].strip(),
        safe_headers=_safe_headers(request),
        body_sha256=hashlib.sha256(body).hexdigest() if body else '',
        body_preview=_decode_preview(body) if body else '',
        rnc=_extract_rnc(body),
        remote_addr=_remote_addr(request),
        response_status=response_status,
        error=error,
    )


class DGIIPublicEndpointMixin:
    endpoint_name = ''
    allowed_methods = ('POST',)

    def dispatch(self, request, *args, **kwargs):
        if request.method not in self.allowed_methods:
            return self._reject(request, 405, 'method_not_allowed', 'Método no permitido.')

        if request.method in ('POST', 'PUT', 'PATCH'):
            content_length = int(request.META.get('CONTENT_LENGTH') or 0)
            if content_length > MAX_PUBLIC_DGII_PAYLOAD_BYTES:
                return self._reject(request, 413, 'payload_too_large', 'Payload excede el tamaño máximo permitido.')

            content_type = (request.headers.get('Content-Type') or '').split(';')[0].strip().lower()
            if content_type not in ALLOWED_POST_CONTENT_TYPES:
                return self._reject(request, 415, 'unsupported_media_type', 'Content-Type no soportado para endpoint público DGII.')

        return super().dispatch(request, *args, **kwargs)

    def _reject(self, request, status, code, message):
        _audit_request(request, endpoint=self.endpoint_name, response_status=status, error=message)
        return _json_response({
            'ok': False,
            'code': code,
            'message': message,
            'request_id': str(uuid.uuid4()),
        }, status=status)

    def _accept(self, request, *, code, message, extra=None, status=200):
        _audit_request(request, endpoint=self.endpoint_name, response_status=status)
        body = request.body or b''
        payload = {
            'ok': True,
            'code': code,
            'message': message,
            'request_id': str(uuid.uuid4()),
            'rnc': _extract_rnc(body) or None,
        }
        if extra:
            payload.update(extra)
        return _json_response(payload, status=status)


@method_decorator(csrf_exempt, name='dispatch')
class FEReceptionView(DGIIPublicEndpointMixin, View):
    endpoint_name = 'fe_recepcion_ecf'

    def post(self, request):
        return self._accept(
            request,
            code='FE_RECEIVED_PENDING_PROCESSING',
            message='Solicitud de recepción e-CF recibida y auditada. Procesamiento fiscal público pendiente de habilitación.',
        )


@method_decorator(csrf_exempt, name='dispatch')
class FECommercialApprovalView(DGIIPublicEndpointMixin, View):
    endpoint_name = 'fe_aprobacion_comercial_ecf'

    def post(self, request):
        return self._accept(
            request,
            code='FE_COMMERCIAL_APPROVAL_RECEIVED',
            message='Solicitud de aprobación comercial recibida y auditada. Este endpoint no ejecuta aprobación interna de cotizaciones.',
        )


@method_decorator(csrf_exempt, name='dispatch')
class FESeedView(DGIIPublicEndpointMixin, View):
    endpoint_name = 'fe_autenticacion_semilla'
    allowed_methods = ('GET',)

    def get(self, request):
        seed = f"<Semilla>{uuid.uuid4().hex}</Semilla>"
        _audit_request(request, endpoint=self.endpoint_name, response_status=200)
        return _json_response({
            'ok': True,
            'code': 'FE_SEED_CREATED',
            'semilla': seed,
            'request_id': str(uuid.uuid4()),
        })


@method_decorator(csrf_exempt, name='dispatch')
class FECertificateValidationView(DGIIPublicEndpointMixin, View):
    endpoint_name = 'fe_autenticacion_semilla_validacion_certificado'

    def post(self, request):
        return self._accept(
            request,
            code='FE_CERTIFICATE_VALIDATION_RECEIVED',
            message='Solicitud de validación de semilla/certificado recibida y auditada. No se exponen secretos.',
        )
