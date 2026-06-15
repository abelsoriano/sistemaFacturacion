"""Constants used by the DGII e-CF XML module."""

from decimal import Decimal


ECF_VERSION = "1.0"
SUPPORTED_XML_TYPES = {"31", "32", "34"}
DGII_DATE_FORMAT = "%d-%m-%Y"
DGII_DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"
XMLDSIG_NAMESPACE = "http://www.w3.org/2000/09/xmldsig#"

ITBIS_RATE_18 = Decimal("18.00")
ITBIS_RATE_16 = Decimal("16.00")
ITBIS_RATE_0 = Decimal("0.00")

ITBIS_INDICATOR_18 = "1"
ITBIS_INDICATOR_16 = "2"
ITBIS_INDICATOR_0 = "3"
ITBIS_INDICATOR_EXEMPT = "4"

PAYMENT_METHOD_TO_DGII = {
    "cash": "1",
    "transfer": "2",
    "card": "3",
}
