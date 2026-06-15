from decimal import Decimal

from rest_framework import serializers

from facturacion.api.company_context import get_current_company
from facturacion.models import AbonoServicio, Almacen, Category, ServicioManoObra


class AlmacenSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            company = get_current_company(request)
            if company:
                self.fields['category_id'].queryset = Category.objects.filter(company=company)

    class Meta:
        model = Almacen
        fields = ['id', 'company', 'name', 'description', 'location', 'stock', 'category', 'category_id']
        read_only_fields = ['company']

    def get_category(self, obj):
        return obj.category.name if obj.category else None


class AbonoServicioSerializer(serializers.ModelSerializer):
    registrado_por_nombre = serializers.CharField(
        source='registrado_por.username',
        read_only=True,
    )

    class Meta:
        model = AbonoServicio
        fields = [
            'id', 'company', 'servicio', 'monto', 'fecha_abono',
            'notas', 'registrado_por', 'registrado_por_nombre',
        ]
        read_only_fields = ['company', 'registrado_por']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            company = get_current_company(request)
            if company:
                self.fields['servicio'].queryset = ServicioManoObra.objects.filter(company=company)

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto del abono debe ser mayor a cero.")
        return value

    def validate(self, data):
        servicio = data.get('servicio')
        monto = data.get('monto', Decimal('0.00'))

        if servicio and servicio.esta_pagado:
            raise serializers.ValidationError(
                "Este servicio ya está completamente pagado."
            )
        if servicio and monto > servicio.saldo_pendiente:
            raise serializers.ValidationError(
                f"El monto excede el saldo pendiente (${servicio.saldo_pendiente})."
            )
        return data

    def create(self, validated_data):
        validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)


class ServicioManoObraSerializer(serializers.ModelSerializer):
    abonos = AbonoServicioSerializer(many=True, read_only=True)
    saldo_pendiente = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    esta_pagado = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServicioManoObra
        fields = [
            'id', 'company', 'nombre_persona', 'descripcion', 'precio_total',
            'factura_asociada', 'modalidad_pago', 'estado_pago',
            'total_abonado', 'saldo_pendiente', 'esta_pagado',
            'fecha_creacion', 'fecha_actualizacion', 'abonos',
        ]
        read_only_fields = ['company', 'estado_pago', 'total_abonado', 'fecha_creacion', 'fecha_actualizacion']
