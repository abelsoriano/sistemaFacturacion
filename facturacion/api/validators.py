import re

from rest_framework import serializers


RNC_LENGTHS = {9, 11}
PHONE_MAX_LENGTH = 20
PHONE_PATTERN = re.compile(r"^[0-9\s()+-]*$")


def normalize_rnc(value, *, required=False, label="RNC"):
    raw = str(value or "").strip()
    if not raw:
        if required:
            raise serializers.ValidationError(f"{label} es obligatorio.")
        return ""
    if not raw.isdigit():
        raise serializers.ValidationError(f"{label} solo debe contener numeros.")
    if len(raw) not in RNC_LENGTHS:
        raise serializers.ValidationError(f"{label} debe tener 9 u 11 digitos.")
    return raw


def validate_phone(value, *, label="Telefono"):
    raw = str(value or "").strip()
    if not raw:
        return raw
    if not PHONE_PATTERN.match(raw):
        raise serializers.ValidationError(
            f"{label} solo puede contener digitos, espacios, guiones, parentesis y +."
        )
    if len(raw) > PHONE_MAX_LENGTH:
        raise serializers.ValidationError(
            f"{label} no debe exceder {PHONE_MAX_LENGTH} caracteres."
        )
    return raw
