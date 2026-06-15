"""Normalize DRF errors without changing HTTP semantics."""

from __future__ import annotations

from rest_framework.views import exception_handler


def normalized_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    code = getattr(getattr(exc, 'default_code', None), 'value', None) or getattr(exc, 'default_code', None) or 'api_error'

    if isinstance(data, dict) and 'detail' in data and len(data) == 1:
        response.data = {
            'detail': data['detail'],
            'code': code,
        }
        return response

    response.data = {
        'detail': 'Error de validacion.' if response.status_code == 400 else 'No fue posible procesar la solicitud.',
        'code': code,
        'fields': data,
    }
    return response
