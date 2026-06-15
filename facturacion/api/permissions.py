"""Shared permission helpers for API view modules."""


FINANCIAL_TOTALS_PERMISSION = 'facturacion.view_financial_totals'
LEGACY_SALE_TOTALS_PERMISSION = 'facturacion.view_sale_totals'
FINANCIAL_TOTALS_PERMISSIONS = (
    FINANCIAL_TOTALS_PERMISSION,
    LEGACY_SALE_TOTALS_PERMISSION,
)


MODEL_PERMISSION_METHODS = {
    'GET': ['facturacion.view_{model}'],
    'POST': ['facturacion.add_{model}'],
    'PUT': ['facturacion.change_{model}'],
    'PATCH': ['facturacion.change_{model}'],
    'DELETE': ['facturacion.delete_{model}'],
}


def model_permissions(model_name):
    return {
        method: [permission.format(model=model_name) for permission in permissions]
        for method, permissions in MODEL_PERMISSION_METHODS.items()
    }


def can_view_financial_totals(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return any(user.has_perm(permission) for permission in FINANCIAL_TOTALS_PERMISSIONS)
