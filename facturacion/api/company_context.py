"""Helpers for resolving the active SaaS company for a request."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from facturacion.models import Company, CompanyMembership


ACTIVE_COMPANY_SESSION_KEY = "active_company_id"
ACTIVE_COMPANY_HEADER = "HTTP_X_COMPANY_ID"


def get_current_company(request):
    """Return the active company for an authenticated user, or None when selection is required."""
    company = getattr(request, "company", None)
    membership = getattr(request, "company_membership", None)
    if company is not None and membership is not None:
        return company

    company, membership = resolve_company_context(request)
    _assign_company_context(request, company, membership)
    return company


def require_current_company(request):
    company = get_current_company(request)
    if company is None:
        raise PermissionDenied("Debes seleccionar una empresa activa para continuar.")
    return company


def get_current_membership(request):
    get_current_company(request)
    return getattr(request, "company_membership", None)


def get_user_companies(user):
    return user_company_queryset(user)


def user_has_company_access(user, company):
    if not user or not user.is_authenticated or company is None:
        return False
    return CompanyMembership.objects.filter(
        user=user,
        company=company,
        is_active=True,
        company__is_active=True,
    ).exists()


def resolve_company_context(request):
    """Resolve active company and membership without relying on existing request attributes."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None, None

    memberships = (
        CompanyMembership.objects
        .select_related("company")
        .filter(user=user, is_active=True, company__is_active=True)
        .order_by("company__name")
    )

    count = memberships.count()
    if count == 0:
        _clear_active_company(request)
        return None, None
    if count == 1:
        membership = memberships.first()
        _set_active_company(request, membership.company_id)
        return membership.company, membership

    session_company_id = _session_company_id(request)
    if session_company_id:
        membership = memberships.filter(company_id=session_company_id).first()
        if membership:
            return membership.company, membership
        _clear_active_company(request)

    header_company_id = _header_company_id(request)
    if header_company_id:
        membership = memberships.filter(company_id=header_company_id).first()
        if membership:
            _set_active_company(request, membership.company_id)
            return membership.company, membership

    membership = memberships.first()
    _set_active_company(request, membership.company_id)
    return membership.company, membership


def user_company_queryset(user):
    if not user or not user.is_authenticated:
        return Company.objects.none()
    return Company.objects.filter(memberships__user=user, memberships__is_active=True, is_active=True).distinct()


def _assign_company_context(request, company, membership):
    request.company = company
    request.company_membership = membership


def _header_company_id(request):
    header_value = request.META.get(ACTIVE_COMPANY_HEADER)
    if header_value:
        try:
            return int(header_value)
        except (TypeError, ValueError):
            return None
    return None


def _session_company_id(request):
    session = getattr(request, "session", None)
    if session is None:
        return None
    try:
        return int(session.get(ACTIVE_COMPANY_SESSION_KEY) or 0) or None
    except (TypeError, ValueError):
        return None


def _set_active_company(request, company_id):
    session = getattr(request, "session", None)
    if session is not None:
        session[ACTIVE_COMPANY_SESSION_KEY] = company_id


def _clear_active_company(request):
    session = getattr(request, "session", None)
    if session is not None:
        session.pop(ACTIVE_COMPANY_SESSION_KEY, None)
