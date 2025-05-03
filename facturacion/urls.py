from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

# Definir el router para los ViewSets
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

# Combinar las URLs generadas por el router con las rutas personalizadas
urlpatterns = router.urls + [
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryRetrieveUpdateDeleteView.as_view(), name='category-detail'),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductRetrieveUpdateDeleteView.as_view(), name='product-detail'),
    path('sales/', SaleCreateView.as_view(), name='create-sale'),
    path('sales/list/', SaleListView.as_view(), name='list-sales'),
    path('salesUpdate/<int:pk>/', SalesUpdateDeleteView.as_view(), name='list-sales'),
]
