from django.db.models import F, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from facturacion.api.scoping import CompanyScopedQuerysetMixin
from facturacion.api.serializers.inventory import (
    CategorySerializer,
    ProductHistorySerializer,
    ProductSerializer,
)
from facturacion.models import Category, Product, ProductHistory
from facturacion.permissions import HasRequiredPermissions


class CategoryListCreateView(CompanyScopedQuerysetMixin, generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_category'],
        'POST': ['facturacion.add_category'],
        'PUT': ['facturacion.change_category'],
        'PATCH': ['facturacion.change_category'],
        'DELETE': ['facturacion.delete_category'],
    }


class CategoryRetrieveUpdateDeleteView(CompanyScopedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_category'],
        'POST': ['facturacion.add_category'],
        'PUT': ['facturacion.change_category'],
        'PATCH': ['facturacion.change_category'],
        'DELETE': ['facturacion.delete_category'],
    }


class ProductListCreateView(CompanyScopedQuerysetMixin, generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_product'],
        'POST': ['facturacion.add_product'],
        'PUT': ['facturacion.change_product'],
        'PATCH': ['facturacion.change_product'],
        'DELETE': ['facturacion.delete_product'],
    }

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        queryset = self.get_company_scoped_queryset(Product.objects.select_related('category').all())

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


class ProductRetrieveUpdateDeleteView(CompanyScopedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {
        'GET': ['facturacion.view_product'],
        'POST': ['facturacion.add_product'],
        'PUT': ['facturacion.change_product'],
        'PATCH': ['facturacion.change_product'],
        'DELETE': ['facturacion.delete_product'],
    }


class ProductHistoryListView(CompanyScopedQuerysetMixin, generics.ListAPIView):
    serializer_class = ProductHistorySerializer
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get_queryset(self):
        product_id = self.kwargs.get('pk')
        product_queryset = self.get_company_scoped_queryset(Product.objects.filter(id=product_id))
        return ProductHistory.objects.filter(product__in=product_queryset).order_by('-timestamp')


class LowStockProductsView(CompanyScopedQuerysetMixin, APIView):
    permission_classes = [IsAuthenticated, HasRequiredPermissions]
    required_permissions = {'GET': ['facturacion.view_product']}

    def get(self, request):
        try:
            low_stock_products = self.get_company_scoped_queryset(Product.objects.filter(
                Q(stock__lt=3) | Q(stock__lt=F('min_stock'))
            )).select_related('category')

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
