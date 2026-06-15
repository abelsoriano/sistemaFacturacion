"""Reusable queryset scoping helpers for future company-aware domains."""

from django.core.exceptions import PermissionDenied

from facturacion.api.company_context import get_current_company


class CompanyScopedQuerysetMixin:
    """Filter querysets by request.company when a model owns a company field.

    This mixin is intentionally not applied globally yet. Future phases can add it
    domain by domain after each model has an explicit company relationship.
    """

    company_field = "company"
    require_company = True
    allow_superuser_bypass = False

    def get_queryset(self):
        return self.get_company_scoped_queryset(super().get_queryset())

    def perform_create(self, serializer):
        company = get_current_company(self.request)
        if company is None:
            raise PermissionDenied("Debes seleccionar una empresa activa para continuar.")
        serializer.save(**{self.company_field: company})

    def get_company_scoped_queryset(self, queryset):
        request = getattr(self, "request", None)
        company = get_current_company(request) if request else None

        if (
            self.allow_superuser_bypass
            and request
            and getattr(request, "user", None)
            and request.user.is_superuser
        ):
            return queryset

        if company is None:
            if self.require_company:
                raise PermissionDenied("Debes seleccionar una empresa activa para continuar.")
            return queryset.none()

        return queryset.filter(**{self.company_field: company})
