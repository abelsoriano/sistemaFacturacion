from rest_framework import generics, viewsets
from .models import *
from .serializers import *
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from django.shortcuts import render, redirect
from django.forms import modelformset_factory
from django.contrib import messages

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

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
                Q(name__icontains=search) | Q(description__icontains=search)
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
