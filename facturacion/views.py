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
import socket
import subprocess
import platform
import tempfile
import os

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
        Genera comandos ZPL para etiqueta de 50x25mm (2x1 pulgadas)
        Ajusta las dimensiones según tu etiqueta
        """
        # Truncar nombre si es muy largo
        product_name = product.name[:25] if len(product.name) > 25 else product.name
        price_formatted = f"${product.price:.2f}"
        
        # Comandos ZPL para etiqueta 50x25mm
        zpl = f"""^XA
^PW300
^LL200
^PQ{quantity}
^FO20,10^A0N,22,22^FD{product_name}^FS
^FO20,40^BY1.5,2,40^BCN,40,Y,N,N^FD{product.barcode}^FS
^FO20,90^A0N,20,20^FD{price_formatted}^FS
^XZ"""
        return zpl


class PrintLabelDirectView(APIView):
    """
    Vista para enviar directamente a imprimir
    POST /api/products/print-direct/
    Body: {"product_id": 1, "quantity": 1, "printer_name": "USB001"}
    """
    def post(self, request):
        try:
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            printer_name = request.data.get('printer_name', 'USB001')
            
            print(f"PrintDirect - product_id: {product_id}, quantity: {quantity}, printer: {printer_name}")
            
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
            
            print(f"ZPL generado ({len(zpl_commands)} caracteres):")
            print(zpl_commands[:200] + "...")  # Imprimir primeros 200 caracteres
            
            # Intentar imprimir según el sistema operativo
            success, message = self.print_to_zebra(zpl_commands, printer_name)
            
            if success:
                return Response({
                    "success": True,
                    "message": message,
                    "product": product.name,
                    "quantity": quantity,
                    "debug_info": {
                        "zpl_length": len(zpl_commands),
                        "method_used": message
                    }
                })
            else:
                return Response({
                    "success": False,
                    "error": message,
                    "zpl": zpl_commands,
                    "suggestion": "Intenta con 'Descargar ZPL' y luego ejecuta en CMD: copy /b archivo.zpl USB001"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            print(f"Error en PrintLabelDirectView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def print_to_zebra(self, zpl_content, printer_name):
        """
        Envía comandos ZPL a la impresora Zebra
        Retorna: (success: bool, message: str)
        """
        system = platform.system()
        
        if system == "Windows":
            # Intentar múltiples métodos en orden
            methods = [
                ("PowerShell Out-Printer", self.print_windows_powershell),
                ("Python win32print", self.print_windows_win32),
                ("CMD copy", self.print_windows_copy),
                ("NET USE", self.print_windows_net),
            ]
            
            for method_name, method_func in methods:
                try:
                    print(f"\nIntentando método: {method_name}")
                    success, message = method_func(zpl_content, printer_name)
                    if success:
                        print(f"✓ {method_name} funcionó!")
                        return True, f"{message} (método: {method_name})"
                    else:
                        print(f"✗ {method_name} falló: {message}")
                except Exception as e:
                    print(f"✗ {method_name} excepción: {str(e)}")
                    continue
            
            return False, "Todos los métodos de impresión fallaron. Usa 'Descargar ZPL'."
        else:
            return False, f"Sistema operativo no soportado para impresión directa: {system}"
    
    def print_windows_powershell(self, zpl_content, printer_name):
        """
        Método 1: PowerShell con Out-Printer (el más confiable)
        """
        # Buscar el nombre real de la impresora
        real_printer_name = self.find_zebra_printer_name()
        if not real_printer_name and not printer_name.startswith('USB'):
            real_printer_name = printer_name
        
        if not real_printer_name:
            return False, "No se encontró nombre de impresora Zebra"
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zpl', delete=False, encoding='utf-8') as tmp:
            tmp.write(zpl_content)
            tmp_path = tmp.name
        
        try:
            # Script de PowerShell más robusto
            ps_script = f'''
$ErrorActionPreference = "Stop"
$printerName = "{real_printer_name}"
$filePath = "{tmp_path.replace(chr(92), chr(92)+chr(92))}"

try {{
    # Leer contenido del archivo como bytes
    $bytes = [System.IO.File]::ReadAllBytes($filePath)
    $content = [System.Text.Encoding]::ASCII.GetString($bytes)
    
    # Enviar a impresora
    Out-Printer -Name $printerName -InputObject $content
    Write-Output "SUCCESS"
}} catch {{
    Write-Error $_.Exception.Message
    exit 1
}}
'''
            
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            print(f"PowerShell stdout: {result.stdout}")
            print(f"PowerShell stderr: {result.stderr}")
            print(f"PowerShell return code: {result.returncode}")
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                return True, f"Etiqueta enviada a {real_printer_name}"
            else:
                return False, f"PowerShell falló: {result.stderr}"
                
        except Exception as e:
            return False, f"Error PowerShell: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def print_windows_win32(self, zpl_content, printer_name):
        """
        Método 2: win32print (requiere pywin32)
        """
        try:
            import win32print
            
            # Buscar nombre de impresora
            real_printer_name = self.find_zebra_printer_name()
            if not real_printer_name:
                return False, "No se encontró impresora Zebra"
            
            # Abrir impresora
            hPrinter = win32print.OpenPrinter(real_printer_name)
            
            try:
                # Iniciar documento
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Etiqueta ZPL", None, "RAW"))
                
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, zpl_content.encode('utf-8'))
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
                    
                return True, f"Etiqueta enviada a {real_printer_name} via win32print"
                
            finally:
                win32print.ClosePrinter(hPrinter)
                
        except ImportError:
            return False, "win32print no está instalado (pip install pywin32)"
        except Exception as e:
            return False, f"Error win32print: {str(e)}"
    
    def print_windows_copy(self, zpl_content, printer_name):
        """
        Método 3: CMD copy (requiere privilegios)
        """
        # Intentar con el puerto directamente
        port = printer_name if printer_name.startswith(('USB', 'COM', 'LPT')) else 'USB001'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zpl', delete=False, encoding='utf-8') as tmp:
            tmp.write(zpl_content)
            tmp_path = tmp.name
        
        try:
            # Comando copy con modo binario
            cmd = f'copy /b "{tmp_path}" {port}'
            print(f"Ejecutando: {cmd}")
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"copy stdout: {result.stdout}")
            print(f"copy stderr: {result.stderr}")
            
            if result.returncode == 0:
                return True, f"Etiqueta enviada a {port} via copy"
            else:
                return False, f"copy falló: {result.stderr}"
                
        except Exception as e:
            return False, f"Error copy: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def print_windows_net(self, zpl_content, printer_name):
        """
        Método 4: NET USE (para impresoras compartidas)
        """
        real_printer_name = self.find_zebra_printer_name()
        if not real_printer_name:
            return False, "No se encontró impresora"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zpl', delete=False, encoding='utf-8') as tmp:
            tmp.write(zpl_content)
            tmp_path = tmp.name
        
        try:
            # Intentar imprimir directamente con print comando
            cmd = f'print /d:"{real_printer_name}" "{tmp_path}"'
            print(f"Ejecutando: {cmd}")
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Etiqueta enviada a {real_printer_name} via print"
            else:
                return False, f"print falló: {result.stderr}"
                
        except Exception as e:
            return False, f"Error print: {str(e)}"
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def find_zebra_printer_name(self):
        """
        Encuentra el nombre exacto de la impresora Zebra en Windows
        """
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Printer | Where-Object {$_.Name -like "*Zebra*" -or $_.Name -like "*ZDesigner*"} | Select-Object -ExpandProperty Name -First 1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            printer_name = result.stdout.strip()
            if printer_name:
                print(f"Impresora Zebra encontrada: {printer_name}")
                return printer_name
                
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

   



