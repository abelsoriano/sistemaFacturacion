from pathlib import Path

from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from facturacion.api.company_context import get_current_company, get_current_membership
from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.ecf_config import DGIICertificationItemSerializer, DGIICertificationPlanSerializer
from facturacion.models import CompanyMembership, DGIICertificationItem, DGIICertificationPlan
from facturacion.services.dgii_certification import DGIICertificationExcelImporter, DGIICertificationXMLGenerator


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

    @action(detail=True, methods=['post'], url_path=r'items/(?P<item_id>[^/.]+)/generate-xml')
    def generate_item_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        item = DGIICertificationXMLGenerator().generate_item(item=item, user=request.user)
        serializer = DGIICertificationItemSerializer(item, context={'request': request})
        response_status = status.HTTP_200_OK
        if item.status == DGIICertificationItem.STATUS_GENERATION_ERROR:
            response_status = status.HTTP_400_BAD_REQUEST
        return Response(serializer.data, status=response_status)

    @action(detail=True, methods=['post'], url_path=r'groups/(?P<group_number>[1-4])/generate-xml')
    def generate_group_xml(self, request, pk=None, group_number=None):
        plan = self.get_object()
        permission_response = self._manager_permission_response(request)
        if permission_response is not None:
            return permission_response

        summary = DGIICertificationXMLGenerator().generate_group(
            plan=plan,
            group_number=int(group_number),
            user=request.user,
        )
        plan.refresh_from_db()
        serializer = self.get_serializer(plan)
        return Response({'summary': summary, 'plan': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path=r'items/(?P<item_id>[^/.]+)/download-xml')
    def download_item_xml(self, request, pk=None, item_id=None):
        plan = self.get_object()
        item = self._get_plan_item(plan, item_id)
        if item is None:
            return Response({'detail': 'Item de certificacion DGII no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not item.generated_xml_path:
            return Response({'detail': 'Este item todavia no tiene escenario generado.'}, status=status.HTTP_404_NOT_FOUND)
        if not default_storage.exists(item.generated_xml_path):
            return Response({'detail': 'El escenario generado no esta disponible en almacenamiento.'}, status=status.HTTP_404_NOT_FOUND)

        filename = item.generated_xml_path.rsplit('/', 1)[-1]
        return FileResponse(default_storage.open(item.generated_xml_path, 'rb'), as_attachment=True, filename=filename)

    def _manager_permission_response(self, request):
        company = get_current_company(request)
        membership = get_current_membership(request)
        if company is None:
            return Response(
                {'detail': 'Debes seleccionar una empresa activa para generar XML DGII.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user.is_superuser:
            return None
        if membership and membership.role in MANAGER_ROLES and membership.is_active:
            return None
        return Response(
            {'detail': 'Solo un owner o admin puede generar XML del plan DGII.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def _get_plan_item(self, plan, item_id):
        try:
            return plan.items.get(id=item_id, company=plan.company)
        except DGIICertificationItem.DoesNotExist:
            return None
