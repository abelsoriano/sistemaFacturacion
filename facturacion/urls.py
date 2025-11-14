from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static
from django.conf import settings
from .views import *
from . import views

from .views import (
    CategoryListCreateView,
    CategoryRetrieveUpdateDeleteView,
    ProductListCreateView,
    ProductRetrieveUpdateDeleteView,
    SaleCreateView,
    SaleListView,
    SalesUpdateDeleteView,
    LabourUpdateDeleteView,
    DashboardView,
    generate_low_stock_pdf,
    # NUEVAS VISTAS IMPORTADAS
    GenerateBarcodeImageView,
    GenerateZPLLabelView,
    PrintLabelDirectView,
    SearchByBarcodeView,
    ListPrintersView,  # NUEVA
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'almacens', AlmacenViewSet, basename='almacen')
router.register(r'labours', LabourViewSet, basename='labour')
# router.register(r'products', ProductListCreateView, basename='products')


# Combinar las URLs generadas por el router con las rutas personalizadas
urlpatterns = router.urls + [
    # ==========================================
    # CATEGORÍAS
    # ==========================================
    path('products/', ProductListCreateView.as_view(), name='products'),
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryRetrieveUpdateDeleteView.as_view(), name='category-detail'),
    
    # ==========================================
    # PRODUCTOS
    # ==========================================
    path('products/<int:pk>/', ProductRetrieveUpdateDeleteView.as_view(), name='product-detail'),
    path('products/low-stock/', views.LowStockProductsView.as_view(), name='low-stock-products'),
    
    # ==========================================
    # CÓDIGOS DE BARRAS - NUEVAS RUTAS
    # ==========================================
    path('products/<int:pk>/barcode-image/', GenerateBarcodeImageView.as_view(), name='generate-barcode-image'),
    path('products/print-label/', GenerateZPLLabelView.as_view(), name='print-label'),
    path('products/print-direct/', PrintLabelDirectView.as_view(), name='print-direct'),
    path('products/search-barcode/', SearchByBarcodeView.as_view(), name='search-barcode'),
    path('products/list-printers/', ListPrintersView.as_view(), name='list-printers'), 
    
    # ==========================================
    # VENTAS
    # ==========================================
    path('sales/', SaleCreateView.as_view(), name='create-sale'),
    path('sales/list/', SaleListView.as_view(), name='list-sales'),
    path('salesUpdate/<int:pk>/', SalesUpdateDeleteView.as_view(), name='list-sales'),
    
    # ==========================================
    # LABORES
    # ==========================================
    path('labourUpdate/<int:pk>/', LabourUpdateDeleteView.as_view(), name='labour-list'),
    
    # ==========================================
    # DASHBOARD Y REPORTES
    # ==========================================
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('reports/low-stock-pdf/', generate_low_stock_pdf, name='low-stock-pdf'),
]