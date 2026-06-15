from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand


SENSITIVE_AUTH_PERMISSIONS = {
    "add_user",
    "change_user",
    "delete_user",
    "view_user",
    "add_group",
    "change_group",
    "delete_group",
    "view_group",
    "view_permission",
}


class Command(BaseCommand):
    help = "Remueve permisos directos auth.* sensibles de usuarios SaaS no administrativos."

    def handle(self, *args, **options):
        sensitive_permissions = list(
            Permission.objects.filter(
                content_type__app_label="auth",
                codename__in=SENSITIVE_AUTH_PERMISSIONS,
            ).order_by("codename")
        )
        sensitive_ids = {permission.id for permission in sensitive_permissions}
        User = get_user_model()

        inspected = 0
        changed = 0
        removed_total = 0
        preserved_total = 0

        for user in User.objects.filter(user_permissions__in=sensitive_permissions).distinct().order_by("username"):
            inspected += 1
            direct_permissions = list(
                user.user_permissions.filter(id__in=sensitive_ids).order_by("content_type__app_label", "codename")
            )
            before = [self._label(permission) for permission in direct_permissions]
            to_remove = []
            preserved = []
            reason = ""

            if user.is_superuser:
                preserved = direct_permissions
                reason = "superuser esperado"
            elif user.is_staff:
                group_permission_ids = set(
                    Permission.objects.filter(group__user=user, id__in=sensitive_ids).values_list("id", flat=True)
                )
                to_remove = [permission for permission in direct_permissions if permission.id in group_permission_ids]
                preserved = [permission for permission in direct_permissions if permission.id not in group_permission_ids]
                reason = "staff: se remueven directos redundantes; se conservan directos no redundantes"
            else:
                to_remove = direct_permissions
                reason = "usuario SaaS normal"

            if to_remove:
                user.user_permissions.remove(*to_remove)
                changed += 1
                removed_total += len(to_remove)
            preserved_total += len(preserved)

            after = [self._label(permission) for permission in preserved]
            self.stdout.write(f"Usuario {user.username} ({user.id}) - {reason}")
            self.stdout.write(f"  Antes: {', '.join(before) if before else 'ninguno'}")
            self.stdout.write(
                "  Removidos: "
                + (", ".join(self._label(permission) for permission in to_remove) if to_remove else "ninguno")
            )
            self.stdout.write(f"  Despues: {', '.join(after) if after else 'ninguno'}")

        if inspected == 0:
            self.stdout.write("No se encontraron permisos directos auth.* sensibles para limpiar.")

        self.stdout.write(f"Usuarios auditados: {inspected}")
        self.stdout.write(f"Usuarios modificados: {changed}")
        self.stdout.write(f"Permisos directos removidos: {removed_total}")
        self.stdout.write(f"Permisos directos conservados: {preserved_total}")
        self.stdout.write(self.style.SUCCESS("Limpieza de permisos directos auth.* completada."))

    def _label(self, permission):
        return f"{permission.content_type.app_label}.{permission.codename}"
