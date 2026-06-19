from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views

from facturacion.api.views.assets import AssetCategoryViewSet, AssetViewSet
from facturacion.api.views.auth import (
    GroupViewSet,
    LoginView,
    PermissionListView,
    ProfileView,
    RegisterView,
    UserViewSet,
    VerifyTokenView,
)
from facturacion.api.views.clients import ClientViewSet
from facturacion.api.views.companies import CompanyViewSet
from facturacion.api.views.credit_notes import CreditNoteViewSet
from facturacion.api.views.ecf_config import ECFEventLogViewSet, ECFIssuerConfigViewSet, ECFSequenceViewSet
from facturacion.api.views.dgii_certification import DGIICertificationPlanViewSet
from facturacion.api.views.ecf_runtime import ElectronicFiscalDocumentViewSet
from facturacion.api.views.inventory import (
    CategoryListCreateView,
    CategoryRetrieveUpdateDeleteView,
    LowStockProductsView,
    ProductListCreateView,
    ProductHistoryListView,
    ProductRetrieveUpdateDeleteView,
)
from facturacion.api.views.inventory_utils import (
    GenerateBarcodeImageView,
    GenerateZPLLabelView,
    ListPrintersView,
    PrintLabelDirectView,
    SearchByBarcodeView,
    generate_low_stock_pdf,
)
from facturacion.api.views.invoices import InvoiceViewSet
from facturacion.api.views.operations import (
    AbonoServicioViewSet,
    AlmacenViewSet,
    ServicioManoObraUpdateDeleteView,
    ServicioManoObraViewSet,
)
from facturacion.api.views.quotations import QuotationViewSet
from facturacion.api.views.reports import DashboardView
from facturacion.api.views.sales_legacy import SaleCreateView, SaleListView, SalesUpdateDeleteView

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'quotations', QuotationViewSet, basename='quotation')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'credit-notes', CreditNoteViewSet, basename='credit-note')
router.register(r'almacens', AlmacenViewSet, basename='almacen')
# router.register(r'labours', LabourViewSet, basename='labour')
router.register(r'assets/categories', AssetCategoryViewSet, basename='asset-category')
router.register(r'assets', AssetViewSet, basename='assets')
# GESTIÓN DE USUARIOS Y ROLES
router.register(r'users', UserViewSet, basename='user')
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'abonos', AbonoServicioViewSet, basename='abono')
router.register(r'servicios-mano-obra', ServicioManoObraViewSet, basename='servicio-mano-obra')
router.register(r'ecf/issuers', ECFIssuerConfigViewSet, basename='ecf-issuer')
router.register(r'ecf/sequences', ECFSequenceViewSet, basename='ecf-sequence')
router.register(r'ecf/certification-plans', DGIICertificationPlanViewSet, basename='dgii-certification-plan')
router.register(r'ecf/documents', ElectronicFiscalDocumentViewSet, basename='ecf-document')
router.register(r'ecf/events', ECFEventLogViewSet, basename='ecf-event')



# Combinar las URLs generadas por el router con las rutas personalizadas
urlpatterns = router.urls + [

    # ==========================================
    # AUTENTICACIÓN - ¡AGREGAR ESTO!
    # ==========================================
    path('login/', LoginView.as_view(), name='login'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
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
    path('products/<int:pk>/history/', ProductHistoryListView.as_view(), name='product-history'),
    path('products/low-stock/', LowStockProductsView.as_view(), name='low-stock-products'),
    
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
    path('labourUpdate/<int:pk>/', ServicioManoObraUpdateDeleteView.as_view(), name='labour-list'),
    
    # ==========================================
    # DASHBOARD Y REPORTES
    # ==========================================
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('reports/low-stock-pdf/', generate_low_stock_pdf, name='low-stock-pdf'),

    # path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='reservar_turno'), name='logout'),
    path('profile/', ProfileView.as_view()),
    path('verify-token/', VerifyTokenView.as_view(), name='verify-token'),
    # GESTIÓN DE USUARIOS Y ROLES
    path('permissions/', PermissionListView.as_view(), name='permissions-list'),
]
