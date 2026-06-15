import base64
import io
import json
import platform
import subprocess
from datetime import datetime
from io import BytesIO

import barcode
from barcode.writer import ImageWriter
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes as drf_permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from facturacion.api.company_context import get_current_company
from facturacion.api.serializers.inventory import ProductSerializer
from facturacion.models import Product
from facturacion.permissions import HasRequiredPermissions


def _require_company(request):
    company = get_current_company(request)
    if company is None:
        raise PermissionDenied("Debes seleccionar una empresa activa para continuar.")
    return company


def _tenant_product_queryset(request):
    return Product.objects.select_related('category').filter(company=_require_company(request))


def _extract_product_id(product):
    product_id = product.get('id') or product.get('product_id') if isinstance(product, dict) else None
    if product_id in (None, ''):
        return None
    try:
        return int(product_id)
    except (TypeError, ValueError):
        return None


@api_view(['POST'])
@drf_permission_classes([IsAuthenticated])
def generate_low_stock_pdf(request):
    if not request.user.is_superuser and not request.user.has_perm('facturacion.view_product'):
        return Response({'detail': 'No tienes permiso para generar este reporte.'}, status=403)

    try:
        company = _require_company(request)
        data = request.data
        products = data.get('products', [])
        if products:
            product_ids = [_extract_product_id(product) for product in products]
            if any(product_id is None for product_id in product_ids):
                return Response(
                    {'detail': 'Cada producto del reporte debe incluir un id valido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            product_map = {
                product.id: product
                for product in Product.objects.filter(company=company, id__in=product_ids)
            }
            if len(product_map) != len(set(product_ids)):
                return Response({'detail': 'Producto no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            products = [
                {
                    'name': product_map[product_id].name,
                    'stock': product_map[product_id].stock,
                    'min_stock': product_map[product_id].min_stock,
                }
                for product_id in product_ids
            ]

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


class GenerateBarcodeImageView(APIView):
    """
    Genera imagen del código de barras en base64.
    GET /api/products/{id}/barcode-image/
    """
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request, pk):
        try:
            product = _tenant_product_queryset(request).get(pk=pk)

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
                product = _tenant_product_queryset(request).get(pk=product_id)
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
                product = _tenant_product_queryset(request).get(pk=product_id)
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
            product = _tenant_product_queryset(request).get(barcode=barcode_value)
            serializer = ProductSerializer(product, context={'request': request})
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {"error": f"Producto con código '{barcode_value}' no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
