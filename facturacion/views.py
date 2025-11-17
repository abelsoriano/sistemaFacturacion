import json
from rest_framework import generics, viewsets

from .serializers import *
from django.db.models import Q, F

from rest_framework import status
from django.utils import timezone

from django.db.models import Sum,  Count
from collections import defaultdict
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime
from django.utils.timezone import make_aware
from rest_framework.decorators import action
from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django_filters.rest_framework import DjangoFilterBackend
import subprocess
import platform
from rest_framework import viewsets, status, filters


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    
    def get_serializer_context(self):
        """Agrega el request al contexto del serializer para generar URLs absolutas"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        queryset = Product.objects.select_related('category').all()
        
        # Filtro para bajo stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock and low_stock.lower() == 'true':
            queryset = queryset.filter(
                Q(stock__lt=3) | Q(stock__lt=F('min_stock'))
            )
        
        category = self.request.query_params.get('category.name')
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
                Q(barcode__icontains=search)  # NUEVO: Búsqueda por código de barras
            )

        ordering = self.request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset


class ProductRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# ============================================================================
# NUEVAS VISTAS PARA CÓDIGOS DE BARRAS
# ============================================================================

class GenerateBarcodeImageView(APIView):
    """
    Vista para generar imagen del código de barras
    GET /api/products/{id}/barcode-image/
    """
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            
            if not product.barcode:
                return Response(
                    {"error": "Este producto no tiene código de barras"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generar código de barras Code128
            CODE128 = barcode.get_barcode_class('code128')
            code = CODE128(product.barcode, writer=ImageWriter())
            
            # Generar imagen en memoria
            buffer = BytesIO()
            code.write(buffer)
            buffer.seek(0)
            
            # Convertir a base64 para enviar al frontend
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return Response({
                "barcode": product.barcode,
                "image": f"data:image/png;base64,{image_base64}",
                "product_name": product.name,
                "price": str(product.price)
            })
            
        except Product.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    """
    Vista para generar etiqueta ZPL para impresora Zebra
    POST /api/products/print-label/
    Body: {"product_id": 1, "quantity": 1}
    """
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            # Debugging: Ver qué datos llegan
            print(f"Datos recibidos - product_id: {product_id}, quantity: {quantity}")
            print(f"Request data completo: {request.data}")
            
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
            
            # Generar código ZPL
            zpl_commands = self.generate_zpl_label(product, quantity)
            
            return Response({
                "success": True,
                "zpl": zpl_commands,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "barcode": product.barcode,
                    "price": str(product.price)
                },
                "quantity": quantity
            })
            
        except Exception as e:
            print(f"Error en GenerateZPLLabelView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_zpl_label(self, product, quantity=1):
        """
        Genera comandos ZPL para etiqueta de 50x25mm (2x1 pulgadas)
        Ajusta las dimensiones según tu etiqueta
        """
        # Truncar nombre si es muy largo
        product_name = product.name[:30] if len(product.name) > 30 else product.name
        price_formatted = f"${product.price:.2f}"
        
        # Comandos ZPL para etiqueta 50x25mm
        zpl = f"""^XA
^PQ{quantity}
^FO50,20^A0N,25,25^FD{product_name}^FS
^FO50,50^BY2,2,50^BCN,50,Y,N,N^FD{product.barcode}^FS
^FO50,110^A0N,20,20^FD{price_formatted}^FS
^XZ"""
        return zpl

class GenerateZPLLabelView(APIView):
    """
    Vista para generar etiqueta ZPL para impresora Zebra
    POST /api/products/print-label/
    Body: {"product_id": 1, "quantity": 1}
    """
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            # Debugging: Ver qué datos llegan
            print(f"Datos recibidos - product_id: {product_id}, quantity: {quantity}")
            print(f"Request data completo: {request.data}")
            
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
            
            # Generar código ZPL
            zpl_commands = self.generate_zpl_label(product, quantity)
            
            return Response({
                "success": True,
                "zpl": zpl_commands,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "barcode": product.barcode,
                    "price": str(product.price)
                },
                "quantity": quantity
            })
            
        except Exception as e:
            print(f"Error en GenerateZPLLabelView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def generate_zpl_label(self, product, quantity=1):
        """
        Versión alternativa con código de barras más compacto
        ^FO75,130^A0N,20,20^FD{price_formatted}^FS
        """
        product_name = product.name[:22].upper() if len(product.name) > 22 else product.name.upper()
        price_formatted = f"${product.price:.2f}"
        barcode = product.barcode.strip()
        
        zpl = f"""^XA
^MMT
^PW400
^LL200
^LS0
^PQ{quantity}

^FO75,20^A0N,18,18^FD{product_name}^FS

^FO75,55^BY2^BCN,50,N,N,N^FD{barcode}^FS

^FO75,110^A0N,18,18^FD{barcode}^FS


^XZ"""
        
        return zpl
    


class PrintLabelDirectView(APIView):
    """
    Vista para enviar directamente a imprimir (requiere configuración del servidor)
    POST /api/products/print-direct/
    """
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            # Debugging
            print(f"PrintDirect - product_id: {product_id}, quantity: {quantity}")
            
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
            
            # Generar ZPL
            view = GenerateZPLLabelView()
            zpl_commands = view.generate_zpl_label(product, quantity)
            
            # Aquí podrías enviar directamente a la impresora si está en red
            # IMPORTANTE: Descomenta y configura solo si tu impresora está en red
            # import socket
            # printer_ip = "192.168.1.100"  # IP de tu impresora
            # printer_port = 9100
            # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # sock.connect((printer_ip, printer_port))
            # sock.send(zpl_commands.encode())
            # sock.close()
            
            return Response({
                "success": True,
                "message": "Etiqueta generada (impresión directa no configurada)",
                "product": product.name,
                "quantity": quantity,
                "zpl": zpl_commands
            })
            
        except Exception as e:
            print(f"Error en PrintLabelDirectView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PrintLabelDirectView(APIView):
    """
    Vista para enviar directamente a imprimir etiquetas ZPL
    POST /api/products/print-direct/
    Body: {"product_id": 1, "quantity": 1, "printer_name": "opcional"}
    """
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
            
            # Generar ZPL
            view = GenerateZPLLabelView()
            zpl_commands = view.generate_zpl_label(product, quantity)
            
            # Intentar imprimir
            success, message = self.print_to_zebra(zpl_commands)
            
            if success:
                return Response({
                    "success": True,
                    "message": message,
                    "product": product.name,
                    "quantity": quantity
                })
            else:
                return Response({
                    "success": False,
                    "error": message,
                    "zpl": zpl_commands
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            print(f"Error en PrintLabelDirectView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def print_to_zebra(self, zpl_content):
        """Envía comandos ZPL a la impresora Zebra"""
        if platform.system() != "Windows":
            return False, "Solo soportado en Windows"
        
        # Intentar win32print primero (más rápido)
        success, message = self.print_windows_win32(zpl_content)
        if success:
            return True, message
        
        # Fallback a copy como respaldo
        print(f"win32print falló, intentando copy: {message}")
        return self.print_windows_copy(zpl_content)
    
    def print_windows_win32(self, zpl_content):
        """Método principal: win32print (más rápido y confiable)"""
        try:
            import win32print
            
            # Buscar impresora Zebra
            printer_name = self.find_zebra_printer()
            if not printer_name:
                return False, "No se encontró impresora Zebra"
            
            # Abrir impresora
            hPrinter = win32print.OpenPrinter(printer_name)
            
            try:
                # Iniciar trabajo de impresión en modo RAW
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Etiqueta ZPL", None, "RAW"))
                
                try:
                    win32print.StartPagePrinter(hPrinter)
                    # Enviar como ASCII
                    win32print.WritePrinter(hPrinter, zpl_content.encode('ascii'))
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
                
                return True, f"Etiqueta enviada a {printer_name}"
                
            finally:
                win32print.ClosePrinter(hPrinter)
                
        except ImportError:
            return False, "Instalar pywin32: pip install pywin32"
        except Exception as e:
            return False, f"Error win32print: {str(e)}"
    
    def print_windows_copy(self, zpl_content):
        """Método de respaldo: CMD copy (más lento, requiere permisos)"""
        import tempfile
        import subprocess
        import os
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zpl', delete=False, encoding='ascii') as tmp:
            tmp.write(zpl_content)
            tmp_path = tmp.name
        
        try:
            # Intentar con USB001 por defecto
            cmd = f'copy /b "{tmp_path}" USB001'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, "Etiqueta enviada a USB001"
            else:
                return False, f"Error copy: {result.stderr or 'Fallo desconocido'}"
                
        except Exception as e:
            return False, f"Error copy: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def find_zebra_printer(self):
        """Encuentra el nombre exacto de la impresora Zebra instalada"""
        try:
            import subprocess
            
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-Printer | Where-Object {$_.Name -like "*Zebra*" -or $_.Name -like "*ZDesigner*"} | Select-Object -ExpandProperty Name -First 1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            printer_name = result.stdout.strip()
            return printer_name if printer_name else None
                
        except Exception as e:
            print(f"Error buscando impresora: {str(e)}")
            return None


class ListPrintersView(APIView):
    """
    Vista para listar impresoras disponibles
    GET /api/products/list-printers/
    """
    def get(self, request):
        system = platform.system()
        printers = []
        
        try:
            if system == "Windows":
                # Usar PowerShell para listar impresoras
                result = subprocess.run(
                    ['powershell', '-Command', 'Get-Printer | Select-Object Name, PortName | ConvertTo-Json'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    import json
                    printers_data = json.loads(result.stdout)
                    if isinstance(printers_data, dict):
                        printers_data = [printers_data]
                    printers = [
                        {"name": p.get('Name'), "port": p.get('PortName')}
                        for p in printers_data
                        if 'Zebra' in p.get('Name', '') or 'ZDesigner' in p.get('Name', '')
                    ]
            elif system == "Linux":
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('printer'):
                            name = line.split()[1]
                            printers.append({"name": name, "port": "USB"})
            elif system == "Darwin":
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Zebra' in line or 'ZDesigner' in line:
                            name = line.split()[1]
                            printers.append({"name": name, "port": "USB"})
            
            return Response({
                "system": system,
                "printers": printers,
                "count": len(printers)
            })
            
        except Exception as e:
            return Response({
                "error": str(e),
                "system": system,
                "printers": []
            })       

class SearchByBarcodeView(APIView):
    """
    Vista para buscar producto por código de barras (para la pistola escáner)
    GET /api/products/search-barcode/?barcode=PRD123456789012
    """
    def get(self, request):
        barcode = request.query_params.get('barcode')
        
        if not barcode:
            return Response(
                {"error": "El parámetro 'barcode' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(barcode=barcode)
            serializer = ProductSerializer(product, context={'request': request})
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado con ese código de barras"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class SaleCreateView(APIView):
    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", request.data)  # Imprime los datos recibidos para depuración
        serializer = SaleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Errores de validación:", serializer.errors)  # Imprime errores si los hay
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SaleListView(generics.ListAPIView):
    queryset = Sale.objects.prefetch_related('details__product').all()
    serializer_class = SaleListSerializer

class SalesUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sale.objects.all()
    serializer_class= SaleListSerializer


class SalesDetail(APIView):
    def delete(self, request, pk):
        try:
            sale = Sale.objects.get(pk=pk)
            sale.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Sale.DoesNotExist:
            return Response({"error": "Venta no encontrada"}, status=status.HTTP_404_NOT_FOUND)


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def create(self, request, *args, **kwargs):
        try:
            print("Received Invoice Data:", request.data)
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
            return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            print("Validation Error:", e.detail)
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("Unexpected Error:", str(e))
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AlmacenViewSet(viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer


class LabourViewSet(viewsets.ModelViewSet):
    queryset = Labour.objects.all()
    serializer_class = LabourSerializer

class LabourUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Labour.objects.all()
    serializer_class= LabourSerializer

class LowStockProductsView(APIView):
    def get(self, request):
        try:
            # Obtener productos con bajo stock (stock < stock mínimo o < 5 por defecto)
            low_stock_products = Product.objects.filter(
                Q(stock__lt=3) |  # Stock menor a 5
                Q(stock__lt=F('min_stock'))  # O stock menor al mínimo definido
            ).select_related('category')
            
            # Serializar los datos
            products_data = []
            for product in low_stock_products:
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'code': product.code,
                    'category': product.category.name if product.category else 'Sin categoría',
                    'category_name': product.category.name if product.category else 'Sin categoría',
                    'stock': product.stock,
                    'min_stock': product.min_stock if product.min_stock else 3,
                    'price': str(product.price),
                    'description': product.description
                })
            
            return Response(products_data)
            
        except Exception as e:
            print(f"Error obteniendo productos con bajo stock: {e}")
            return Response([], status=500)

# O si prefieres una función-based view:
@api_view(['GET'])
def low_stock_products(request):
    try:
        # Obtener productos con bajo stock
        low_stock_products = Product.objects.filter(
            Q(stock__lt=3) |  # Stock menor a 5
            Q(stock__lt=F('min_stock'))  # O stock menor al mínimo definido
        ).select_related('category')
        
        # Serializar los datos
        products_data = []
        for product in low_stock_products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'category': product.category.name if product.category else 'Sin categoría',
                'category_name': product.category.name if product.category else 'Sin categoría',
                'stock': product.stock,
                'min_stock': product.min_stock if product.min_stock else 3,
                'price': str(product.price),
                'description': product.description
            })
        
        return Response(products_data)
        
    except Exception as e:
        print(f"Error obteniendo productos con bajo stock: {e}")
        return Response([], status=500)

@csrf_exempt
def generate_low_stock_pdf(request):
    if request.method == 'POST':
        try:
            # Obtener datos del request
            data = json.loads(request.body)
            products = data.get('products', [])
            
            # Crear buffer para el PDF
            buffer = io.BytesIO()
            
            # Crear documento
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            
            # Título
            title = Paragraph("Reporte de Productos con Bajo Stock", styles['Title'])
            elements.append(title)
            
            # Fecha
            date_str = Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
            elements.append(date_str)
            elements.append(Spacer(1, 20))
            
            # Tabla de productos
            if products:
                # Encabezados de la tabla
                data = [['Producto',  'Stock', 'Stock Mínimo', 'Estado']]
                
                for product in products:
                    status = "Agotado" if product.get('stock', 0) == 0 else "Bajo Stock"
                    data.append([
                        product.get('name', ''),
                        # product.get('category', ''),
                        str(product.get('stock', 0)),
                        str(product.get('min_stock', 3)),
                        status
                    ])
                
                # Crear tabla
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
            
            # Generar PDF
            doc.build(elements)
            
            # Preparar respuesta
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="productos-bajo-stock.pdf"'
            
            return response
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


class DashboardView(APIView):
    def get(self, request):
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        time_frame = request.query_params.get('time_frame', 'month')

        # Convertir fechas string a datetime
        try:
            if start_date and end_date:
                # Corregir la sintaxis del parsing de fechas
                start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
            else:
                end_date = timezone.now()
                start_date = end_date - timedelta(days=30)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)

        # Asegurar que end_date incluya todo el día
        end_date = end_date.replace(hour=23, minute=59, second=59)

        # Filter sales by date range
        sales = Sale.objects.filter(date__range=[start_date, end_date])

        # Sales summary
        total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
        sales_count = sales.count()
        products_sold = SaleDetail.objects.filter(sale__in=sales).aggregate(
            total=Sum('quantity'))['total'] or 0

        # Top products
        top_products = (
            Product.objects
            .annotate(
                total_sold=Sum('saledetail__quantity', filter=Q(saledetail__sale__in=sales))
            )
            .filter(total_sold__isnull=False)
            .order_by('-total_sold')[:5]
            .values('name', 'total_sold')
        )

        # Sales by category - ALTERNATIVE APPROACH
        # We'll calculate this in Python instead of at the database level

        # First get all sale details for the period
        sale_details = SaleDetail.objects.filter(sale__in=sales).select_related('product__category')

        # Calculate totals by category
        category_totals = defaultdict(float)
        for detail in sale_details:
            category_name = detail.product.category.name
            # Use the total from the detail if available, otherwise calculate it
            if hasattr(detail, 'subtotal') and detail.subtotal:
                category_totals[category_name] += float(detail.subtotal)
            else:
                category_totals[category_name] += float(detail.price * detail.quantity)

        # Format for the response
        sales_by_category = [
            {'name': name, 'value': value}
            for name, value in category_totals.items()
            if value > 0
        ]

        # Sales trend - placeholder implementation
        sales_trend = self.get_sales_trend(sales, time_frame)

        # Inventory status - placeholder implementation
        inventory_status = self.get_inventory_status()

        # Recent sales
        recent_sales = (
            sales
            .order_by('-date')[:10]
            .annotate(details_count=Count('details'))
            .values('id', 'customer', 'date', 'total', 'details_count')
        )

        data = {
            'salesSummary': {
                'total_sales': float(total_sales),
                'sales_count': sales_count,
                'products_sold': products_sold,
            },
            'topProducts': [
                {'name': p['name'], 'quantity': p['total_sold'] or 0}
                for p in top_products
            ],
            'salesByCategory': sales_by_category,
            'salesTrend': sales_trend,
            'inventoryStatus': inventory_status,
            'recentSales': [
                {
                    'id': s['id'],
                    'customer': s['customer'] or 'N/A',
                    'date': s['date'].isoformat() if hasattr(s['date'], 'isoformat') else s['date'],
                    'total': float(s['total']),
                    'details_count': s['details_count']
                }
                for s in recent_sales
            ],
        }

        return Response(data)

    def get_sales_trend(self, sales, time_frame):
        # Implementation for sales trend based on time_frame
        from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

        # Determine the date truncation function based on time_frame
        if time_frame == 'day':
            trunc_function = TruncDay('date')
            format_str = '%Y-%m-%d'
        elif time_frame == 'week':
            trunc_function = TruncWeek('date')
            format_str = '%Y-%U'  # Year-Week number
        elif time_frame == 'year':
            trunc_function = TruncYear('date')
            format_str = '%Y'
        else:
            # Default to month
            trunc_function = TruncMonth('date')
            format_str = '%Y-%m'

        # Get sales data aggregated by the selected time period
        sales_by_period = (
            sales
            .annotate(period=trunc_function)
            .values('period')
            .annotate(sales=Sum('total'))
            .order_by('period')
        )

        # Format the data for the front-end
        trend_data = []

        for entry in sales_by_period:
            if entry['period'] is not None:
                # Format the period based on the time_frame
                if time_frame == 'week':
                    # For weekly data, we format as "Week X of YYYY"
                    week_number = entry['period'].strftime('%U')
                    year = entry['period'].strftime('%Y')
                    period_str = f"Semana {week_number} de {year}"
                elif time_frame == 'day':
                    # For daily data, format as DD/MM/YYYY
                    period_str = entry['period'].strftime('%d/%m/%Y')
                elif time_frame == 'year':
                    # For yearly data, just the year
                    period_str = entry['period'].strftime('%Y')
                else:
                    # For monthly data, format as Month YYYY
                    period_str = entry['period'].strftime('%B %Y')

                trend_data.append({
                    'period': period_str,
                    'sales': float(entry['sales'] or 0)
                })

        return trend_data

    def get_inventory_status(self):
        # Implementation for inventory status using Almacen model
        try:
            # Get inventory data grouped by category
            categories_inventory = (
                Category.objects.annotate(
                    total_stock=Sum('products__stock')
                )
                .values('name', 'total_stock')
            )

            # Process data for front-end
            categories = []
            low_stock_count = 0

            for category in categories_inventory:
                # Get products in this category with low stock
                low_stock_products = Product.objects.filter(
                    category__name=category['name'],
                    stock__lt=5  # Assuming < 10 is low stock
                ).count()

                # Get products out of stock
                out_of_stock = Product.objects.filter(
                    category__name=category['name'],
                    stock=0
                ).count()

                # Get in stock count (not low, not out)
                in_stock = Product.objects.filter(
                    category__name=category['name'],
                    stock__gt=5
                ).count()

                # Add to low stock count
                low_stock_count += low_stock_products

                # Add category data
                categories.append({
                    'name': category['name'],
                    'in_stock': in_stock,
                    'low_stock': low_stock_products,
                    'out_of_stock': out_of_stock,
                    'total': category['total_stock'] or 0
                })

            return {
                'low_stock_count': low_stock_count,
                'categories': categories
            }
        except Exception as e:
            print(f"Error getting inventory status: {e}")
            return {
                'low_stock_count': 0,
                'categories': []
            }


# Testing views for Asset Management Module
   
class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related('category').all()
    serializer_class = AssetSerializer
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
        """Obtener estadísticas de activos"""
        total = self.queryset.count()
        by_status = self.queryset.values('status').annotate(count=Count('id'))
        by_condition = self.queryset.values('condition').annotate(count=Count('id'))
        by_category = self.queryset.values('category__name').annotate(count=Count('id'))
        
        # Activos que necesitan mantenimiento
        from django.utils import timezone
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
        """Listar solo activos disponibles"""
        available_assets = self.queryset.filter(status='available')
        serializer = self.get_serializer(available_assets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def maintenance_required(self, request):
        """Listar activos que necesitan mantenimiento"""
        from django.utils import timezone
        assets = self.queryset.filter(
            next_maintenance__lte=timezone.now().date()
        )
        serializer = self.get_serializer(assets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Asignar activo a una persona"""
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
        
        serializer = self.get_serializer(asset)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def return_asset(self, request, pk=None):
        """Devolver activo (marcarlo como disponible)"""
        asset = self.get_object()
        asset.assigned_to = None
        asset.status = 'available'
        asset.save()
        
        serializer = self.get_serializer(asset)
        return Response(serializer.data)
