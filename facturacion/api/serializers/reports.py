from rest_framework import serializers


class SalesSummarySerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    sales_count = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    average_ticket = serializers.DecimalField(max_digits=10, decimal_places=2)


class TopProductSerializer(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class RecentSaleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer = serializers.CharField()
    date = serializers.DateTimeField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    items_count = serializers.IntegerField()
