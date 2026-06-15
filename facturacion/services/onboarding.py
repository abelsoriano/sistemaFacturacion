"""SaaS onboarding permission helpers."""

from django.contrib.auth.models import Group, Permission, User


DEFAULT_OWNER_GROUP_NAME = "Owner SaaS Inicial"

DEFAULT_OWNER_PERMISSION_CODENAMES = {
    "add_category",
    "change_category",
    "view_category",
    "add_product",
    "change_product",
    "view_product",
    "add_client",
    "change_client",
    "view_client",
    "add_almacen",
    "change_almacen",
    "view_almacen",
    "add_invoice",
    "change_invoice",
    "view_invoice",
    "reverse_invoice",
    "view_financial_totals",
    "add_quotation",
    "change_quotation",
    "view_quotation",
    "add_creditnote",
    "view_creditnote",
    "add_ecfissuerconfig",
    "change_ecfissuerconfig",
    "view_ecfissuerconfig",
    "add_ecfsequence",
    "change_ecfsequence",
    "view_ecfsequence",
    "view_electronicfiscaldocument",
    "view_ecfeventlog",
}


def sync_default_owner_group_permissions() -> tuple[Group, int, int]:
    """Synchronize the controlled initial owner permission group."""
    group, _ = Group.objects.get_or_create(name=DEFAULT_OWNER_GROUP_NAME)
    permissions = Permission.objects.filter(
        content_type__app_label="facturacion",
        codename__in=DEFAULT_OWNER_PERMISSION_CODENAMES,
    )
    before_ids = set(group.permissions.values_list("id", flat=True))
    expected_ids = set(permissions.values_list("id", flat=True))
    group.permissions.set(permissions)
    removed_count = len(before_ids - expected_ids)
    added_count = len(expected_ids - before_ids)
    return group, removed_count, added_count


def assign_default_owner_permissions(user: User) -> Group:
    """Assign the controlled initial owner permission group to a new SaaS owner."""
    group, _, _ = sync_default_owner_group_permissions()
    user.groups.add(group)
    return group
