from rest_framework.permissions import BasePermission


class HasRequiredPermissions(BasePermission):
    # message = 'No tienes permiso para acceder a esta sección.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        action_permissions = getattr(view, 'action_required_permissions', {})
        action = getattr(view, 'action', None)
        required_permissions = getattr(view, 'required_permissions', {})
        permissions = action_permissions.get(action, required_permissions.get(request.method, []))

        if not permissions:
            return True

        return request.user.has_perms(permissions)
