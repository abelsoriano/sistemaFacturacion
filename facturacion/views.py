from rest_framework import generics, viewsets
from .models import *
from .serializers import *
from django.db.models import Sum, Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone
from django.shortcuts import render, redirect
from django.forms import modelformset_factory
from django.db.models import F
from django.db.models import Sum,  Count
from collections import defaultdict
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response

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
                Q(description__icontains=search)
            )

        ordering = self.request.query_params.get('ordering')
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset

class ProductRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


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


class DashboardView(APIView):
    def get(self, request):
        # Get query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        time_frame = request.query_params.get('time_frame', 'month')
        
        # Convertir fechas string a datetime
        try:
            if start_date and end_date:
                start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
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
                    total_stock=Sum('almacenes__stock')
                )
                .values('name', 'total_stock')
            )
            
            # Process data for front-end
            categories = []
            low_stock_count = 0
            
            for category in categories_inventory:
                # Get products in this category with low stock
                low_stock_products = Almacen.objects.filter(
                    category__name=category['name'],
                    stock__lt=10  # Assuming < 10 is low stock
                ).count()
                
                # Get products out of stock
                out_of_stock = Almacen.objects.filter(
                    category__name=category['name'],
                    stock=0
                ).count()
                
                # Get in stock count (not low, not out)
                in_stock = Almacen.objects.filter(
                    category__name=category['name'],
                    stock__gt=10
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