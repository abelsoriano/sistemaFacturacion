import json
import io
import base64
import platform
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, viewsets, status, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer

import barcode
from barcode.writer import ImageWriter
from io import BytesIO

from .serializers import *
from .permissions import HasRequiredPermissions


MODEL_PERMISSION_METHODS = {
    'GET': ['facturacion.view_{model}'],
    'POST': ['facturacion.add_{model}'],
    'PUT': ['facturacion.change_{model}'],
    'PATCH': ['facturacion.change_{model}'],
    'DELETE': ['facturacion.delete_{model}'],
}


def model_permissions(model_name):
    return {
        method: [permission.format(model=model_name) for permission in permissions]
        for method, permissions in MODEL_PERMISSION_METHODS.items()
    }


# ============ CATEGORY VIEWS ============
class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('category')


class CategoryRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('category')


# ============ PRODUCT VIEWS ============
class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('product')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        queryset = Product.objects.select_related('category').all()

        low_stock = self.request.query_params.get('low_stock')
        if low_stock and low_stock.lower() == 'true':
            queryset = queryset.filter(
                Q(stock__lt=3) | Q(stock__lt=F('min_stock'))
            )

        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        search = self.request.query_params.get('search')

        if category:
            queryset = queryset.filter(category__name=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(barcode__icontains=search)
            )

        ordering = self.request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset


class ProductRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('product')


class ProductHistoryListView(generics.ListAPIView):
    serializer_class = ProductHistorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get_queryset(self):
        product_id = self.kwargs.get('pk')
        return ProductHistory.objects.filter(product_id=product_id).order_by('-timestamp')


# ============ LOW STOCK VIEWS ============
class LowStockProductsView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request):
        try:
            low_stock_products = Product.objects.filter(
                Q(stock__lt=3) | Q(stock__lt=F('min_stock'))
            ).select_related('category')

            products_data = [
                {
                    'id': p.id,
                    'name': p.name,
                    'barcode': p.barcode,
                    'category': p.category.name if p.category else 'Sin categoría',
                    'category_name': p.category.name if p.category else 'Sin categoría',
                    'stock': p.stock,
                    'min_stock': p.min_stock if p.min_stock else 3,
                    'price': str(p.price),
                    'description': p.description,
                }
                for p in low_stock_products
            ]

            return Response(products_data)

        except Exception as e:
            print(f"Error: {e}")
            return Response([], status=500)


@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def generate_low_stock_pdf(request):
    if not request.user.is_superuser and not request.user.has_perm('facturacion.view_product'):
        return Response({'detail': 'No tienes permiso para generar este reporte.'}, status=403)

    try:
        data = request.data
        products = data.get('products', [])

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Reporte de Productos con Bajo Stock", styles['Title']))
        elements.append(Paragraph(
            f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        if products:
            table_data = [['Producto', 'Stock', 'Stock Mínimo', 'Estado']]
            for product in products:
                estado = "Agotado" if product.get('stock', 0) == 0 else "Bajo Stock"
                table_data.append([
                    product.get('name', ''),
                    str(product.get('stock', 0)),
                    str(product.get('min_stock', 3)),
                    estado
                ])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="productos-bajo-stock.pdf"'
        return response

    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ============ SALE VIEWS ============
class SaleCreateView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'POST': ['facturacion.add_sale']}

    def post(self, request, *args, **kwargs):
        serializer = SaleSerializer(data=request.data)
        if serializer.is_valid():
            sale = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SaleListView(generics.ListAPIView):
    queryset = Sale.objects.prefetch_related('details__product').all()
    serializer_class = SaleListSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_sale']}


class SalesUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class = SaleListSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('sale')


class SalesDetail(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'DELETE': ['facturacion.delete_sale']}

    def delete(self, request, pk):
        try:
            sale = Sale.objects.get(pk=pk)
            for detail in sale.details.all():
                product = detail.product
                product.stock += detail.quantity
                product.save()
            sale.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Sale.DoesNotExist:
            return Response({"error": "Venta no encontrada"}, status=status.HTTP_404_NOT_FOUND)


# ============ INVOICE VIEWS ============
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('client')


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.prefetch_related('details__product').all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('invoice')

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()

            # Normalizar payment_method
            payment_map = {
                'efectivo': 'cash',
                'tarjeta': 'card',
                'transferencia': 'transfer',
            }
            if 'payment_method' in data:
                data['payment_method'] = payment_map.get(
                    data['payment_method'], data['payment_method']
                )

            # Asegurar que receipt_type sea válido
            if data.get('receipt_type') not in ('ticket', 'invoice'):
                data['receipt_type'] = 'invoice'

            # Redondear change antes de validar (evita float sucio, ej: 10.700000000000045)
            if 'change' in data:
                data['change'] = float(
                    Decimal(str(data['change'])).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                )

            # Convertir product_id → product en los detalles
            if 'details' in data:
                for detail in data['details']:
                    if 'product_id' in detail:
                        detail['product'] = detail.pop('product_id')

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            invoice = serializer.save()

            return Response(
                self.get_serializer(invoice).data,
                status=status.HTTP_201_CREATED
            )

        except DRFValidationError:
            # Deja que DRF devuelva el 400 normalmente
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============ ALMACEN VIEWS ============
class AlmacenViewSet(viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('almacen')


# ============ LABOUR VIEWS ============
class ServicioManoObraViewSet(viewsets.ModelViewSet):
    queryset = ServicioManoObra.objects.prefetch_related('abonos').all()
    serializer_class = ServicioManoObraSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('servicio_mano_obra')

    @action(detail=True, methods=['post'], url_path='pagar-completo')
    def pagar_completo(self, request, pk=None):
        """Registra un abono por el saldo pendiente completo"""
        servicio = self.get_object()

        if servicio.esta_pagado:
            return Response(
                {'detail': 'Este servicio ya está pagado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        abono = AbonoServicio.objects.create(
            servicio=servicio,
            monto=servicio.saldo_pendiente,
            notas='Pago completo del saldo pendiente',
            registrado_por=request.user
        )

        return Response(
            AbonoServicioSerializer(abono, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='resumen')
    def resumen(self, request, pk=None):
        """Devuelve un resumen del estado de pago"""
        servicio = self.get_object()
        return Response({
            'nombre_persona': servicio.nombre_persona,
            'precio_total': servicio.precio_total,
            'total_abonado': servicio.total_abonado,
            'saldo_pendiente': servicio.saldo_pendiente,
            'estado_pago': servicio.estado_pago,
            'modalidad_pago': servicio.modalidad_pago,
            'cantidad_abonos': servicio.abonos.count(),
        })


class AbonoServicioViewSet(viewsets.ModelViewSet):
    queryset = AbonoServicio.objects.select_related('servicio', 'registrado_por').all()
    serializer_class = AbonoServicioSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('abono_servicio')

    def get_queryset(self):
        qs = super().get_queryset()
        servicio_id = self.request.query_params.get('servicio')
        if servicio_id:
            qs = qs.filter(servicio_id=servicio_id)
        return qs



class ServicioManoObraUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ServicioManoObra.objects.all()
    serializer_class = ServicioManoObraSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('servicio_mano_obra')


# ============ BARCODE VIEWS ============
class GenerateBarcodeImageView(APIView):
    """
    Genera imagen del código de barras en base64.
    GET /api/products/{id}/barcode-image/
    """
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)

            if not product.barcode:
                return Response(
                    {"error": "Este producto no tiene código de barras"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            CODE128 = barcode.get_barcode_class('code128')
            code = CODE128(product.barcode, writer=ImageWriter())

            buffer = BytesIO()
            code.write(buffer)
            buffer.seek(0)

            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            return Response({
                "barcode": product.barcode,
                "image": f"data:image/png;base64,{image_base64}",
                "product_name": product.name,
                "price": str(product.price),
            })

        except Product.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateZPLLabelView(APIView):
    """
    Genera etiqueta ZPL para impresora Zebra.
    POST /api/products/print-label/
    Body: {"product_id": 1, "quantity": 1}
    """
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'POST': ['facturacion.view_product']}

    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)

            if not product_id:
                return Response(
                    {"error": "product_id es requerido"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"error": f"Producto con ID {product_id} no encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not product.barcode:
                return Response(
                    {"error": "Este producto no tiene código de barras"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            zpl_commands = self.generate_zpl_label(product, quantity)

            return Response({
                "success": True,
                "zpl": zpl_commands,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "barcode": product.barcode,
                    "price": str(product.price),
                },
                "quantity": quantity,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def generate_zpl_label(self, product, quantity=1):
        product_name = product.name[:22].upper()
        price_formatted = f"${product.price:.2f}"
        barcode_value = product.barcode.strip()

        return (
            f"^XA\n"
            f"^MMT\n"
            f"^PW400\n"
            f"^LL200\n"
            f"^LS0\n"
            f"^PQ{quantity}\n"
            f"^FO75,20^A0N,18,18^FD{product_name}^FS\n"
            f"^FO75,55^BY2^BCN,50,N,N,N^FD{barcode_value}^FS\n"
            f"^FO75,110^A0N,18,18^FD{barcode_value}^FS\n"
            f"^XZ"
        )


class PrintLabelDirectView(APIView):
    """
    Envía etiqueta ZPL directamente a la impresora Zebra.
    POST /api/products/print-direct/
    Body: {"product_id": 1, "quantity": 1}
    """
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'POST': ['facturacion.view_product']}

    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)

            if not product_id:
                return Response(
                    {"error": "product_id es requerido"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"error": f"Producto con ID {product_id} no encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not product.barcode:
                return Response(
                    {"error": "Este producto no tiene código de barras"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            zpl_commands = GenerateZPLLabelView().generate_zpl_label(product, quantity)
            success, message = self.print_to_zebra(zpl_commands)

            if success:
                return Response({
                    "success": True,
                    "message": message,
                    "product": product.name,
                    "quantity": quantity,
                })
            else:
                return Response(
                    {"success": False, "error": message, "zpl": zpl_commands},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def print_to_zebra(self, zpl_content):
        if platform.system() != "Windows":
            return False, "Solo soportado en Windows"

        success, message = self.print_windows_win32(zpl_content)
        if success:
            return True, message

        print(f"win32print falló, intentando copy: {message}")
        return self.print_windows_copy(zpl_content)

    def print_windows_win32(self, zpl_content):
        try:
            import win32print

            printer_name = self.find_zebra_printer()
            if not printer_name:
                return False, "No se encontró impresora Zebra"

            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Etiqueta ZPL", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, zpl_content.encode('latin-1', errors='replace'))
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)

            return True, f"Etiqueta enviada a {printer_name}"

        except ImportError:
            return False, "Instalar pywin32: pip install pywin32"
        except Exception as e:
            return False, f"Error win32print: {str(e)}"

    def print_windows_copy(self, zpl_content):
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.zpl', delete=False, encoding='latin-1'
        ) as tmp:
            tmp.write(zpl_content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                f'copy /b "{tmp_path}" USB001',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, "Etiqueta enviada a USB001"
            return False, f"Error copy: {result.stderr or 'Fallo desconocido'}"
        except Exception as e:
            return False, f"Error copy: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def find_zebra_printer(self):
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-Printer | Where-Object {$_.Name -like "*Zebra*" -or $_.Name -like "*ZDesigner*"} | '
                 'Select-Object -ExpandProperty Name -First 1'],
                capture_output=True, text=True, timeout=5
            )
            printer_name = result.stdout.strip()
            return printer_name if printer_name else None
        except Exception as e:
            print(f"Error buscando impresora: {e}")
            return None


class ListPrintersView(APIView):
    """
    Lista impresoras Zebra disponibles.
    GET /api/products/list-printers/
    """
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request):
        system = platform.system()
        printers = []

        try:
            if system == "Windows":
                result = subprocess.run(
                    ['powershell', '-Command',
                     'Get-Printer | Select-Object Name, PortName | ConvertTo-Json'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    printers_data = json.loads(result.stdout)
                    if isinstance(printers_data, dict):
                        printers_data = [printers_data]
                    printers = [
                        {"name": p.get('Name'), "port": p.get('PortName')}
                        for p in printers_data
                        if 'Zebra' in p.get('Name', '') or 'ZDesigner' in p.get('Name', '')
                    ]
            elif system in ("Linux", "Darwin"):
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Zebra' in line or 'ZDesigner' in line:
                            name = line.split()[1]
                            printers.append({"name": name, "port": "USB"})

            return Response({"system": system, "printers": printers, "count": len(printers)})

        except Exception as e:
            return Response({"error": str(e), "system": system, "printers": []})


class SearchByBarcodeView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request):
        barcode_value = request.query_params.get('barcode', '').strip()

        if not barcode_value:
            return Response(
                {"error": "Se requiere el parámetro 'barcode'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.select_related('category').get(barcode=barcode_value)
            serializer = ProductSerializer(product, context={'request': request})
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Producto con código '{barcode_value}' no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )


# ============ DASHBOARD VIEW ============
class DashboardView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_sale', 'facturacion.view_product']}

    def get(self, request):
        can_view_totals = request.user.is_superuser or request.user.has_perm('facturacion.view_sale_totals')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        time_frame = request.query_params.get('time_frame', 'month')

        try:
            if start_date and end_date:
                start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
            else:
                end_date = timezone.now()
                start_date = end_date - timedelta(days=30)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)

        end_date = end_date.replace(hour=23, minute=59, second=59)

        sales = Sale.objects.filter(date__range=[start_date, end_date])

        total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
        sales_count = sales.count()
        products_sold = SaleDetail.objects.filter(sale__in=sales).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        top_products = (
            Product.objects
            .annotate(total_sold=Sum(
                'saledetail__quantity',
                filter=Q(saledetail__sale__in=sales)
            ))
            .filter(total_sold__isnull=False)
            .order_by('-total_sold')[:5]
            .values('name', 'total_sold')
        )

        sale_details = SaleDetail.objects.filter(
            sale__in=sales
        ).select_related('product__category')

        category_totals = defaultdict(float)
        for detail in sale_details:
            category_name = detail.product.category.name
            subtotal = float(detail.subtotal) if hasattr(detail, 'subtotal') and detail.subtotal \
                else float(detail.price * detail.quantity)
            category_totals[category_name] += subtotal

        sales_by_category = [
            {'name': name, 'value': value}
            for name, value in category_totals.items()
            if value > 0
        ]

        data = {
            'salesSummary': {
                'total_sales': float(total_sales) if can_view_totals else None,
                'sales_count': sales_count,
                'products_sold': products_sold,
            },
            'topProducts': [
                {'name': p['name'], 'quantity': p['total_sold'] or 0}
                for p in top_products
            ],
            'salesByCategory': sales_by_category if can_view_totals else [],
            'salesTrend': self.get_sales_trend(sales, time_frame) if can_view_totals else [],
            'inventoryStatus': self.get_inventory_status(),
            'recentSales': [
                {
                    'id': s['id'],
                    'customer': s['customer'] or 'N/A',
                    'date': s['date'].isoformat() if hasattr(s['date'], 'isoformat') else s['date'],
                    **({'total': float(s['total'])} if can_view_totals else {}),
                    'details_count': s['details_count'],
                }
                for s in sales.order_by('-date')[:10].annotate(
                    details_count=Count('details')
                ).values('id', 'customer', 'date', 'total', 'details_count')
            ],
        }

        return Response(data)

    def get_sales_trend(self, sales, time_frame):
        from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

        trunc_map = {
            'day': (TruncDay('date'), '%d/%m/%Y'),
            'week': (TruncWeek('date'), '%Y-%U'),
            'year': (TruncYear('date'), '%Y'),
        }
        trunc_function, _ = trunc_map.get(time_frame, (TruncMonth('date'), '%Y-%m'))

        sales_by_period = (
            sales
            .annotate(period=trunc_function)
            .values('period')
            .annotate(sales=Sum('total'))
            .order_by('period')
        )

        trend_data = []
        for entry in sales_by_period:
            if entry['period'] is None:
                continue

            if time_frame == 'week':
                period_str = f"Semana {entry['period'].strftime('%U')} de {entry['period'].strftime('%Y')}"
            elif time_frame == 'day':
                period_str = entry['period'].strftime('%d/%m/%Y')
            elif time_frame == 'year':
                period_str = entry['period'].strftime('%Y')
            else:
                period_str = entry['period'].strftime('%B %Y')

            trend_data.append({
                'period': period_str,
                'sales': float(entry['sales'] or 0),
            })

        return trend_data

    def get_inventory_status(self):
        try:
            categories_inventory = (
                Category.objects
                .annotate(total_stock=Sum('products__stock'))
                .values('name', 'total_stock')
            )

            categories = []
            low_stock_count = 0

            for category in categories_inventory:
                name = category['name']
                low_stock_products = Product.objects.filter(
                    category__name=name, stock__lt=5
                ).count()
                out_of_stock = Product.objects.filter(
                    category__name=name, stock=0
                ).count()
                in_stock = Product.objects.filter(
                    category__name=name, stock__gt=5
                ).count()

                low_stock_count += low_stock_products
                categories.append({
                    'name': name,
                    'in_stock': in_stock,
                    'low_stock': low_stock_products,
                    'out_of_stock': out_of_stock,
                    'total': category['total_stock'] or 0,
                })

            return {'low_stock_count': low_stock_count, 'categories': categories}

        except Exception as e:
            print(f"Error getting inventory status: {e}")
            return {'low_stock_count': 0, 'categories': []}


# ============ ASSET VIEWS ============
class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('assetcategory')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('category').all()
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = model_permissions('asset')
    action_required_permissions = {
        'assign': ['facturacion.change_asset'],
        'return_asset': ['facturacion.change_asset'],
    }
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'condition', 'category', 'assigned_to']
    search_fields = ['code', 'name', 'description', 'brand', 'model', 'serial_number', 'location']
    ordering_fields = ['code', 'name', 'created_at', 'purchase_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        return AssetSerializer

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        total = self.queryset.count()
        by_status = self.queryset.values('status').annotate(count=Count('id'))
        by_condition = self.queryset.values('condition').annotate(count=Count('id'))
        by_category = self.queryset.values('category__name').annotate(count=Count('id'))
        needs_maintenance = self.queryset.filter(
            next_maintenance__lte=timezone.now().date()
        ).count()

        return Response({
            'total': total,
            'by_status': list(by_status),
            'by_condition': list(by_condition),
            'by_category': list(by_category),
            'needs_maintenance': needs_maintenance,
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        available_assets = self.queryset.filter(status='available')
        serializer = self.get_serializer(available_assets, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def maintenance_required(self, request):
        assets = self.queryset.filter(next_maintenance__lte=timezone.now().date())
        serializer = self.get_serializer(assets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        asset = self.get_object()
        assigned_to = request.data.get('assigned_to')

        if not assigned_to:
            return Response(
                {'error': 'Se requiere especificar a quién se asignará el activo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        asset.assigned_to = assigned_to
        asset.status = 'in_use'
        asset.save()

        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=['post'])
    def return_asset(self, request, pk=None):
        asset = self.get_object()
        asset.assigned_to = None
        asset.status = 'available'
        asset.save()

        return Response(self.get_serializer(asset).data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
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
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
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
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['auth.view_permission']}


# ============ AUTH VIEWS ============
class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Usuario y contraseña son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": {
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
            })

        return Response(
            {"error": "Credenciales incorrectas"},
            status=status.HTTP_401_UNAUTHORIZED
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'groups': [group.name for group in user.groups.all()],
            'permissions': sorted(user.get_all_permissions()),
        })

    def put(self, request):
        user = request.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.save()

        return Response({
            'message': 'Perfil actualizado correctamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'groups': [group.name for group in user.groups.all()],
                'permissions': sorted(user.get_all_permissions()),
            }
        })


class VerifyTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "valid": True,
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser,
                "groups": [group.name for group in request.user.groups.all()],
                "permissions": sorted(request.user.get_all_permissions()),
            }
        })
