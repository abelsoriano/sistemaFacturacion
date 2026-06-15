from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission, User
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from facturacion.api.serializers.auth import (
    GroupSerializer,
    PermissionSerializer,
    PublicRegistrationSerializer,
    UserSerializer,
)
from facturacion.permissions import HasRequiredPermissions


class IsStaffOrSuperuser(IsAuthenticated):
    message = 'Esta sección es administración técnica global.'

    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and (request.user.is_staff or request.user.is_superuser)
        )


def auth_user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "groups": [group.name for group in user.groups.all()],
        "permissions": sorted(user.get_all_permissions()),
    }


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsStaffOrSuperuser, HasRequiredPermissions]
    required_permissions = {
        'GET': ['auth.view_user'],
        'POST': ['auth.add_user'],
        'PUT': ['auth.change_user'],
        'PATCH': ['auth.change_user'],
        'DELETE': ['auth.delete_user'],
    }

    def get_object(self):
        obj = super().get_object()
        if self.request.user.is_superuser or self.request.user.has_perm('auth.view_user') or obj == self.request.user:
            return obj
        raise PermissionDenied('No tienes permiso para acceder a este usuario.')


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsStaffOrSuperuser, HasRequiredPermissions]
    required_permissions = {
        'GET': ['auth.view_group'],
        'POST': ['auth.add_group'],
        'PUT': ['auth.change_group'],
        'PATCH': ['auth.change_group'],
        'DELETE': ['auth.delete_group'],
    }


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsStaffOrSuperuser, HasRequiredPermissions]
    required_permissions = {'GET': ['auth.view_permission']}


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Usuario y contraseña son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": auth_user_payload(user),
            })

        return Response(
            {"error": "Credenciales incorrectas"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PublicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": auth_user_payload(user),
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(auth_user_payload(user))

    def put(self, request):
        user = request.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.save()

        return Response({
            'message': 'Perfil actualizado correctamente',
            'user': auth_user_payload(user),
        })


class VerifyTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "valid": True,
            "user": auth_user_payload(request.user),
        })
