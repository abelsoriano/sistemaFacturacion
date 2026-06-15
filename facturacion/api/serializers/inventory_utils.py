from rest_framework import serializers


class PrintLabelSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    label_width = serializers.IntegerField(default=50)
    label_height = serializers.IntegerField(default=25)
