from pathlib import Path

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import get_current_company, get_current_membership
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_config import (
    DGIICertificationCommercialApprovalItemSerializer,
    DGIICertificationCommercialApprovalPlanSerializer,
)
from facturacion.models import (
    CompanyMembership,
    DGIICertificationCommercialApprovalItem,
    DGIICertificationCommercialApprovalPlan,
)
from facturacion.services.dgii_commercial_approval import (
    DGIICertificationCommercialApprovalImporter,
    DGIICertificationCommercialApprovalImportError,
    DGIICertificationCommercialApprovalSubmitter,
)


MANAGER_ROLES = {CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN}


class DGIICertificationCommercialApprovalViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = (
        DGIICertificationCommercialApprovalPlan.objects
        .select_related('company', 'imported_by')
        .prefetch_related('items', 'events')
        .all()
    )
    serializer_class = DGIICertificationCommercialApprovalPlanSerializer
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='import',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_approvals(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para importar aprobaciones comerciales DGII.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede importar aprobaciones comerciales DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'file': ['Debe cargar el Excel entregado por DGII.']}, status=status.HTTP_400_BAD_REQUEST)
        if Path(uploaded_file.name).suffix.lower() != '.xlsx':
            return Response({'file': ['El archivo debe ser .xlsx.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _plan, summary = DGIICertificationCommercialApprovalImporter().import_workbook(
                uploaded_file=uploaded_file,
                company=company,
                user=request.user,
            )
        except DGIICertificationCommercialApprovalImportError as exc:
            return Response(
                {
                    'detail': str(exc),
                    'code': 'dgii_commercial_approval_import_error',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(summary, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        company = get_current_company(request)
        if company is None:
            return Response({'detail': 'Debes seleccionar una empresa activa.'}, status=status.HTTP_400_BAD_REQUEST)
        plan = self.filter_queryset(self.get_queryset()).filter(company=company).order_by('-imported_at').first()
        if plan is None:
            return Response({'detail': 'No hay aprobaciones comerciales importadas.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=['get'], url_path='items')
    def items(self, request, pk=None):
        plan = self.get_object()
        queryset = plan.items.select_related('plan', 'company').all()

        status_filter = request.query_params.get('status')
        encf = request.query_params.get('encf')
        issuer_rnc = request.query_params.get('issuer_rnc')
        buyer_rnc = request.query_params.get('buyer_rnc')
        match_status = request.query_params.get('match_status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if status_filter:
            queryset = queryset.filter(dgii_status=status_filter)
        if encf:
            queryset = queryset.filter(encf__icontains=encf)
        if issuer_rnc:
            queryset = queryset.filter(issuer_rnc__icontains=issuer_rnc)
        if buyer_rnc:
            queryset = queryset.filter(buyer_rnc__icontains=buyer_rnc)
        if match_status:
            queryset = queryset.filter(match_status=match_status)
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        serializer = DGIICertificationCommercialApprovalItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='submit-dgii')
    def submit_dgii(self, request, pk=None):
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response
        plan = self.get_object()
        summary = DGIICertificationCommercialApprovalSubmitter().run(plan=plan, user=request.user)
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        response_status = status.HTTP_400_BAD_REQUEST if summary.get('failed') else status.HTTP_200_OK
        return Response({'summary': summary, 'plan': serializer.data}, status=response_status)

    def _manager_permission_response(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.is_superuser:
            return None
        if membership and membership.role in MANAGER_ROLES and membership.is_active:
            return None
        return Response(
            {'detail': 'Solo un owner o admin puede procesar aprobaciones comerciales DGII.'},
            status=status.HTTP_403_FORBIDDEN,
        )
