from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import (
    ACTIVE_COMPANY_SESSION_KEY,
    get_current_company,
    get_current_membership,
    user_company_queryset,
)
from facturacion.api.serializers.companies import (
    CompanyMembershipCreateSerializer,
    CompanyMembershipSerializer,
    CompanyMembershipUpdateSerializer,
    CompanySerializer,
    CompanySwitchSerializer,
    CompanyWriteSerializer,
)
from facturacion.models import CompanyMembership
from facturacion.services.onboarding import assign_default_owner_permissions


MANAGER_ROLES = {
    CompanyMembership.ROLE_OWNER,
    CompanyMembership.ROLE_ADMIN,
}


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return user_company_queryset(self.request.user).order_by('name')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return CompanyWriteSerializer
        if self.action == 'members':
            return CompanyMembershipSerializer
        return CompanySerializer

    def _user_can_manage_any_company(self, request):
        user = request.user
        if user.is_superuser:
            return True
        return CompanyMembership.objects.filter(
            user=user,
            is_active=True,
            company__is_active=True,
            role__in=MANAGER_ROLES,
        ).exists()

    def _current_membership_can_manage(self, request):
        membership = get_current_membership(request)
        return bool(
            request.user.is_superuser
            or (membership and membership.is_active and membership.role in MANAGER_ROLES)
        )

    def _manager_context_or_response(self, request):
        company = get_current_company(request)
        if company is None:
            return None, None, Response(
                {'detail': 'Debes seleccionar una empresa activa para gestionar miembros.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        membership = get_current_membership(request)
        if request.user.is_superuser or (membership and membership.is_active and membership.role in MANAGER_ROLES):
            return company, membership, None
        return None, None, Response(
            {'detail': 'Solo un owner o admin puede gestionar miembros.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def _active_owner_count(self, company):
        return CompanyMembership.objects.filter(
            company=company,
            role=CompanyMembership.ROLE_OWNER,
            is_active=True,
        ).count()

    def _validate_membership_change(self, *, actor_membership, target_membership, role=None, is_active=None):
        actor_is_admin = actor_membership and actor_membership.role == CompanyMembership.ROLE_ADMIN
        target_is_owner = target_membership.role == CompanyMembership.ROLE_OWNER
        next_role = role if role is not None else target_membership.role
        next_active = is_active if is_active is not None else target_membership.is_active

        if actor_is_admin and target_is_owner:
            return 'Un admin no puede modificar a un owner.'
        if actor_is_admin and next_role == CompanyMembership.ROLE_OWNER:
            return 'Solo un owner puede asignar el rol owner.'
        if (
            target_is_owner
            and target_membership.is_active
            and (next_role != CompanyMembership.ROLE_OWNER or next_active is False)
            and self._active_owner_count(target_membership.company) <= 1
        ):
            return 'No puedes dejar la empresa sin un owner activo.'
        return None

    def create(self, request, *args, **kwargs):
        if not self._user_can_manage_any_company(request):
            return Response(
                {'detail': 'Solo un owner o admin puede crear empresas.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        CompanyMembership.objects.create(
            user=request.user,
            company=company,
            role=CompanyMembership.ROLE_OWNER,
            is_active=True,
        )
        output = CompanySerializer(company, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='setup-first')
    def setup_first(self, request):
        has_active_company = CompanyMembership.objects.filter(
            user=request.user,
            is_active=True,
            company__is_active=True,
        ).exists()
        if has_active_company:
            return Response(
                {'detail': 'Este usuario ya tiene una empresa activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CompanyWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        membership = CompanyMembership.objects.create(
            user=request.user,
            company=company,
            role=CompanyMembership.ROLE_OWNER,
            is_active=True,
        )
        assign_default_owner_permissions(request.user)

        if hasattr(request, 'session'):
            request.session[ACTIVE_COMPANY_SESSION_KEY] = company.id
        request.company = company
        request.company_membership = membership

        return Response(
            {
                'active_company': CompanySerializer(company, context=self.get_serializer_context()).data,
                'companies': CompanySerializer(self.get_queryset(), many=True, context=self.get_serializer_context()).data,
                'requires_selection': False,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        company = get_current_company(request)
        if not company or str(company.id) != str(kwargs.get('pk')) or not self._current_membership_can_manage(request):
            return Response(
                {'detail': 'Solo un owner o admin puede editar la empresa activa.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        company = get_current_company(request)
        if not company or str(company.id) != str(kwargs.get('pk')) or not self._current_membership_can_manage(request):
            return Response(
                {'detail': 'Solo un owner o admin puede editar la empresa activa.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        companies = self.get_queryset()
        active_company = getattr(request, 'company', None) or get_current_company(request)
        return Response(
            {
                'active_company': self.get_serializer(active_company).data if active_company else None,
                'companies': self.get_serializer(companies, many=True).data,
                'requires_selection': companies.count() > 1 and active_company is None,
            }
        )

    @action(detail=False, methods=['get', 'post'], url_path='members')
    def members(self, request):
        company = get_current_company(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para ver sus miembros.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method.lower() == 'post':
            company, actor_membership, error_response = self._manager_context_or_response(request)
            if error_response:
                return error_response

            serializer = CompanyMembershipCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            role = serializer.validated_data['role']
            user = get_user_model().objects.filter(email__iexact=serializer.validated_data['email']).first()
            if not user:
                return Response(
                    {'detail': 'El usuario debe existir antes de agregarlo.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            membership = CompanyMembership.objects.filter(user=user, company=company).first()
            if membership:
                error = self._validate_membership_change(
                    actor_membership=actor_membership,
                    target_membership=membership,
                    role=role,
                    is_active=True,
                )
                if error:
                    return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
                membership.role = role
                membership.is_active = True
                membership.save(update_fields=['role', 'is_active', 'updated_at'])
                response_status = status.HTTP_200_OK
            else:
                if actor_membership and actor_membership.role == CompanyMembership.ROLE_ADMIN and role == CompanyMembership.ROLE_OWNER:
                    return Response(
                        {'detail': 'Solo un owner puede asignar el rol owner.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                membership = CompanyMembership.objects.create(
                    user=user,
                    company=company,
                    role=role,
                    is_active=True,
                )
                response_status = status.HTTP_201_CREATED

            return Response(
                CompanyMembershipSerializer(membership, context=self.get_serializer_context()).data,
                status=response_status,
            )

        memberships = (
            CompanyMembership.objects
            .select_related('user')
            .filter(company=company)
            .order_by('-is_active', 'user__username')
        )
        return Response(self.get_serializer(memberships, many=True).data)

    @action(detail=False, methods=['patch'], url_path=r'members/(?P<membership_id>[^/.]+)')
    def update_member(self, request, membership_id=None):
        company, actor_membership, error_response = self._manager_context_or_response(request)
        if error_response:
            return error_response

        target = (
            CompanyMembership.objects
            .select_related('user', 'company')
            .filter(pk=membership_id, company=company)
            .first()
        )
        if not target:
            return Response({'detail': 'Miembro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CompanyMembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data.get('role')
        is_active = serializer.validated_data.get('is_active')
        error = self._validate_membership_change(
            actor_membership=actor_membership,
            target_membership=target,
            role=role,
            is_active=is_active,
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        update_fields = ['updated_at']
        if role is not None:
            target.role = role
            update_fields.append('role')
        if is_active is not None:
            target.is_active = is_active
            update_fields.append('is_active')
        target.save(update_fields=update_fields)

        return Response(CompanyMembershipSerializer(target, context=self.get_serializer_context()).data)

    @action(detail=False, methods=['post'], url_path='switch')
    def switch(self, request):
        serializer = CompanySwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_id = serializer.validated_data['company_id']

        membership = (
            CompanyMembership.objects
            .select_related('company')
            .filter(
                user=request.user,
                company_id=company_id,
                is_active=True,
                company__is_active=True,
            )
            .first()
        )
        if not membership:
            return Response(
                {'detail': 'No tienes una membresía activa en esa empresa o la empresa está inactiva.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if hasattr(request, 'session'):
            request.session[ACTIVE_COMPANY_SESSION_KEY] = membership.company_id
        request.company = membership.company
        request.company_membership = membership

        return Response(
            {
                'active_company': self.get_serializer(membership.company).data,
                'companies': self.get_serializer(self.get_queryset(), many=True).data,
                'requires_selection': False,
            }
        )
