"""Request middleware for SaaS company context."""

from rest_framework.authtoken.models import Token

from facturacion.api.company_context import resolve_company_context


class CompanyContextMiddleware:
    """Attach the active company context to authenticated requests when available."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        request.company_membership = None

        token_user = self._user_from_token(request)
        if token_user is not None:
            request.user = token_user

        company, membership = resolve_company_context(request)
        request.company = company
        request.company_membership = membership

        return self.get_response(request)

    def _user_from_token(self, request):
        current_user = getattr(request, "user", None)
        if current_user and current_user.is_authenticated:
            return None

        authorization = request.META.get("HTTP_AUTHORIZATION", "")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "token":
            return None

        try:
            token = Token.objects.select_related("user").get(key=parts[1])
        except Token.DoesNotExist:
            return None
        return token.user
