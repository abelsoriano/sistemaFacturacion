from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from facturacion.api.company_context import get_current_company
from facturacion.api.permissions import can_view_financial_totals
from facturacion.models import Category, Invoice, InvoiceDetail, Product
from facturacion.permissions import HasRequiredPermissions


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_invoice', 'facturacion.view_product']}

    def get(self, request):
        can_view_totals = can_view_financial_totals(request.user)
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

        company = get_current_company(request)
        invoices = Invoice.objects.none()
        if company:
            invoices = Invoice.objects.filter(company=company, created_at__range=[start_date, end_date])

        paid_invoices = invoices.filter(status='paid')
        pending_invoices = invoices.filter(status='pending')
        accepted_fiscal_invoices = invoices.filter(electronic_document__fiscal_status='accepted')

        total_sales = paid_invoices.aggregate(total=Sum('total'))['total'] or 0
        sales_count = paid_invoices.count()
        accounts_receivable_total = pending_invoices.aggregate(total=Sum('total'))['total'] or 0
        accepted_fiscal_total = accepted_fiscal_invoices.aggregate(total=Sum('total'))['total'] or 0
        products_sold = InvoiceDetail.objects.filter(invoice__in=paid_invoices).aggregate(
            total=Sum('quantity')
        )['total'] or 0

        top_products = (
            Product.objects
            .annotate(total_sold=Sum(
                'invoicedetail__quantity',
                filter=Q(invoicedetail__invoice__in=paid_invoices)
            ))
            .filter(company=company, total_sold__isnull=False)
            .order_by('-total_sold')[:5]
            .values('name', 'total_sold')
        )

        invoice_details = InvoiceDetail.objects.filter(
            invoice__in=paid_invoices
        ).select_related('product__category')

        category_totals = defaultdict(float)
        for detail in invoice_details:
            category = getattr(detail.product, 'category', None)
            category_name = category.name if category else 'Sin categoría'
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
                'paid_total': float(total_sales) if can_view_totals else None,
                'paid_count': sales_count,
                'accounts_receivable_total': float(accounts_receivable_total) if can_view_totals else None,
                'accounts_receivable_count': pending_invoices.count(),
                'accepted_fiscal_total': float(accepted_fiscal_total) if can_view_totals else None,
                'accepted_fiscal_count': accepted_fiscal_invoices.count(),
                'total_invoices_count': invoices.count(),
            },
            'topProducts': [
                {'name': p['name'], 'quantity': p['total_sold'] or 0}
                for p in top_products
            ],
            'salesByCategory': sales_by_category if can_view_totals else [],
            'salesTrend': self.get_sales_trend(paid_invoices, time_frame) if can_view_totals else [],
            'inventoryStatus': self.get_inventory_status(request),
            'recentSales': [
                {
                    'id': s['id'],
                    'customer': s['client__name'] or 'Consumidor Final',
                    'date': s['created_at'].isoformat() if hasattr(s['created_at'], 'isoformat') else s['created_at'],
                    **({'total': float(s['total'])} if can_view_totals else {}),
                    'details_count': s['details_count'],
                }
                for s in paid_invoices.order_by('-created_at')[:10].annotate(
                    details_count=Count('details')
                ).values('id', 'client__name', 'created_at', 'total', 'details_count')
            ],
        }

        return Response(data)

    def get_sales_trend(self, invoices, time_frame):
        from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear

        trunc_map = {
            'day': (TruncDay('created_at'), '%d/%m/%Y'),
            'week': (TruncWeek('created_at'), '%Y-%U'),
            'year': (TruncYear('created_at'), '%Y'),
        }
        trunc_function, _ = trunc_map.get(time_frame, (TruncMonth('created_at'), '%Y-%m'))

        sales_by_period = (
            invoices
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

    def get_inventory_status(self, request):
        try:
            company = get_current_company(request)
            if company is None:
                return {'low_stock_count': 0, 'categories': []}

            categories_inventory = (
                Category.objects
                .filter(company=company)
                .annotate(total_stock=Sum('products__stock'))
                .values('name', 'total_stock')
            )

            categories = []
            low_stock_count = 0

            for category in categories_inventory:
                name = category['name']
                product_queryset = Product.objects.filter(company=company, category__name=name)
                low_stock_products = product_queryset.filter(stock__lt=5).count()
                out_of_stock = product_queryset.filter(stock=0).count()
                in_stock = product_queryset.filter(stock__gt=5).count()

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
