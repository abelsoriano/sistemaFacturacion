"""Date helpers for DGII XML formats."""

from datetime import date, datetime

from django.utils import timezone

from facturacion.ecf.constants import DGII_DATE_FORMAT, DGII_DATETIME_FORMAT


def format_dgii_date(value: date | datetime | None) -> str | None:
    """Format a date as DD-MM-YYYY for DGII."""
    if value is None:
        return None
    if isinstance(value, datetime):
        value = timezone.localtime(value) if timezone.is_aware(value) else value
        return value.strftime(DGII_DATE_FORMAT)
    return value.strftime(DGII_DATE_FORMAT)


def format_dgii_datetime(value: datetime | None = None) -> str:
    """Format a datetime as DD-MM-YYYY HH:MM:SS for DGII."""
    value = value or timezone.now()
    value = timezone.localtime(value) if timezone.is_aware(value) else value
    return value.strftime(DGII_DATETIME_FORMAT)

