from django.contrib.auth.models import User, Group

# Obtener el grupo Administrador
admin_group = Group.objects.get(name='Administrador')

# Listar usuarios existentes
users = User.objects.all()
print('Usuarios existentes:')
for user in users:
    print(f'{user.username} - {user.email} - Superuser: {user.is_superuser}')

# Asignar grupo Administrador al superusuario
admin_user = User.objects.filter(is_superuser=True).first()
if admin_user:
    admin_user.groups.add(admin_group)
    print(f'Asignado grupo Administrador a {admin_user.username}')
else:
    print('No se encontró superusuario')