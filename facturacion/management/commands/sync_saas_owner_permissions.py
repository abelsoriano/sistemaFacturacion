from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from facturacion.services.onboarding import (
    DEFAULT_OWNER_GROUP_NAME,
    DEFAULT_OWNER_PERMISSION_CODENAMES,
    sync_default_owner_group_permissions,
)


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
    help = "Sincroniza el grupo Owner SaaS Inicial y remueve permisos globales auth.* históricos."

    def handle(self, *args, **options):
        group_exists = Group.objects.filter(name=DEFAULT_OWNER_GROUP_NAME).exists()
        if not group_exists:
            self.stdout.write(
                self.style.WARNING(
                    f"El grupo '{DEFAULT_OWNER_GROUP_NAME}' no existia; sera creado con permisos operativos."
                )
            )

        group = Group.objects.filter(name=DEFAULT_OWNER_GROUP_NAME).first()
        historical_auth = []
        if group:
            historical_auth = list(
                group.permissions.filter(
                    content_type__app_label="auth",
                    codename__in=SENSITIVE_AUTH_PERMISSIONS,
                )
                .order_by("codename")
                .values_list("codename", flat=True)
            )

        group, removed_count, added_count = sync_default_owner_group_permissions()
        maintained_count = Permission.objects.filter(
            content_type__app_label="facturacion",
            codename__in=DEFAULT_OWNER_PERMISSION_CODENAMES,
        ).count()

        if historical_auth:
            self.stdout.write(
                self.style.SUCCESS(
                    "Permisos auth.* removidos: " + ", ".join(f"auth.{codename}" for codename in historical_auth)
                )
            )
        else:
            self.stdout.write("Permisos auth.* removidos: ninguno")

        self.stdout.write(f"Permisos operativos mantenidos/agregados: {maintained_count}")
        self.stdout.write(f"Permisos agregados en esta ejecucion: {added_count}")
        self.stdout.write(f"Permisos removidos en esta ejecucion: {removed_count}")
        self.stdout.write(self.style.SUCCESS(f"Grupo sincronizado: {group.name}"))
