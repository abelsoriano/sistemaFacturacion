from pathlib import Path

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import get_current_company, get_current_membership
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_config import DGIICertificationPlanSerializer
from facturacion.models import CompanyMembership, DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationExcelImporter


MANAGER_ROLES = {CompanyMembership.ROLE_OWNER, CompanyMembership.ROLE_ADMIN}


class DGIICertificationPlanViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = (
        DGIICertificationPlan.objects
        .select_related('company', 'imported_by')
        .prefetch_related('items', 'events')
        .all()
    )
    serializer_class = DGIICertificationPlanSerializer
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='import-set',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_set(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para importar el set DGII.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (request.user.is_superuser or (membership and membership.role in MANAGER_ROLES and membership.is_active)):
            return Response(
                {'detail': 'Solo un owner o admin puede importar el set DGII.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'file': ['Debe cargar el Excel entregado por DGII.']}, status=status.HTTP_400_BAD_REQUEST)
        if Path(uploaded_file.name).suffix.lower() not in {'.xlsx', '.xls'}:
            return Response({'file': ['El set DGII debe ser un archivo .xlsx o .xls.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = DGIICertificationExcelImporter().import_workbook(
                uploaded_file=uploaded_file,
                company=company,
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {
                    'detail': 'No se pudo importar el Excel DGII.',
                    'code': 'dgii_excel_import_error',
                    'error': str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
