from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from facturacion.models import Category, Product, Sale, Invoice, Client, Almacen, Labour, Asset, AssetCategory


EXTRA_PERMISSIONS = {
    'sale': {
        'view_totals': 'view_sale_totals',
    },
}


class Command(BaseCommand):
    help = 'Inicializa grupos y permisos básicos del sistema'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando grupos y permisos...')

        # Definir permisos por modelo
        permissions_data = {
            'Administrador': {
                'categories': ['add', 'change', 'delete', 'view'],
                'products': ['add', 'change', 'delete', 'view'],
                'sales': ['add', 'change', 'delete', 'view'],
                'invoices': ['add', 'change', 'delete', 'view'],
                'clients': ['add', 'change', 'delete', 'view'],
                'almacens': ['add', 'change', 'delete', 'view'],
                'labours': ['add', 'change', 'delete', 'view'],
                'assets': ['add', 'change', 'delete', 'view'],
                'asset_categories': ['add', 'change', 'delete', 'view'],
                'users': ['add', 'change', 'delete', 'view'],
                'groups': ['add', 'change', 'delete', 'view'],
                'permissions': ['view'],
                'sales_extra': ['view_totals'],
            },
            'Vendedor': {
                'categories': ['view'],
                'products': ['add', 'change', 'view'],
                'sales': ['add', 'change', 'view'],
                'invoices': ['add', 'change', 'view'],
                'clients': ['add', 'change', 'delete', 'view'],
            },
            'Almacenista': {
                'categories': ['view'],
                'products': ['add', 'change', 'view'],
                'almacens': ['add', 'change', 'delete', 'view'],
            },
            'Técnico': {
                'labours': ['add', 'change', 'delete', 'view'],
                'assets': ['add', 'change', 'delete', 'view'],
                'asset_categories': ['add', 'change', 'delete', 'view'],
            },
        }

        # Modelos disponibles
        models = {
            'categories': Category,
            'products': Product,
            'sales': Sale,
            'invoices': Invoice,
            'clients': Client,
            'almacens': Almacen,
            'labours': Labour,
            'assets': Asset,
            'asset_categories': AssetCategory,
            'users': User,
            'groups': Group,
            'permissions': Permission,
            'sales_extra': Sale,
        }

        # Crear grupos y asignar permisos
        for group_name, permissions in permissions_data.items():
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                self.stdout.write(f'Creando grupo: {group_name}')
            else:
                self.stdout.write(f'Actualizando grupo: {group_name}')
                group.permissions.clear()  # Limpiar permisos existentes

            for model_name, actions in permissions.items():
                if model_name in models:
                    model = models[model_name]
                    content_type = ContentType.objects.get_for_model(model)

                    for action in actions:
                        codename = EXTRA_PERMISSIONS.get(model._meta.model_name, {}).get(
                            action,
                            f'{action}_{model._meta.model_name}'
                        )
                        try:
                            permission = Permission.objects.get(
                                content_type=content_type,
                                codename=codename
                            )
                            group.permissions.add(permission)
                            self.stdout.write(f'  Agregando permiso: {codename}')
                        except Permission.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  Permiso no encontrado: {codename} para {model_name}'
                                )
                            )

        self.stdout.write(
            self.style.SUCCESS('Grupos y permisos inicializados correctamente')
        )
