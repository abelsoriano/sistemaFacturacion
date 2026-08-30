"""Constants used by the DGII e-CF XML module."""

from decimal import Decimal


ECF_VERSION = "1.0"
SUPPORTED_XML_TYPES = {"31", "32", "34"}
ECF_TYPE_RULES = {
    "31": {
        "include_buyer": True, "allow_sequence_expiration_date": True,
        "allow_income_type": True, "allow_default_payment_forms": True,
        "allow_payment_term": True, "allow_service_all_included_indicator": True,
    },
    "32": {
        "include_buyer": True, "allow_sequence_expiration_date": False,
        "allow_income_type": True, "allow_default_payment_forms": True,
        "allow_payment_term": True, "allow_service_all_included_indicator": True,
    },
    "33": {
        "include_buyer": None, "allow_sequence_expiration_date": True,
        "allow_credit_note_indicator": False, "allow_income_type": True,
        "allow_default_payment_forms": True, "allow_payment_term": True,
        "allow_service_all_included_indicator": True,
    },
    "34": {
        "include_buyer": None, "allow_sequence_expiration_date": False,
        "allow_credit_note_indicator": True, "allow_income_type": True,
        "allow_default_payment_forms": False,
        "allow_payment_term": False, "allow_service_all_included_indicator": True,
    },
    "41": {
        "include_buyer": True, "allow_sequence_expiration_date": True,
        "allow_income_type": False, "allow_default_payment_forms": False,
        "allow_payment_term": True, "allow_service_all_included_indicator": False,
    },
    "43": {
        "include_buyer": False, "allow_sequence_expiration_date": True,
        "allow_income_type": False, "allow_default_payment_forms": False,
        "allow_payment_term": False, "allow_service_all_included_indicator": False,
    },
    "44": {
        "include_buyer": True, "allow_sequence_expiration_date": True,
        "allow_income_type": True, "allow_default_payment_forms": True,
        "allow_payment_term": True, "allow_service_all_included_indicator": True,
    },
    "45": {
        "include_buyer": True, "allow_sequence_expiration_date": True,
        "allow_income_type": True, "allow_default_payment_forms": True,
        "allow_payment_term": True, "allow_service_all_included_indicator": True,
    },
    "46": {
        "include_buyer": True, "allow_sequence_expiration_date": True,
        "allow_income_type": True, "allow_default_payment_forms": False,
        "allow_payment_term": True, "allow_service_all_included_indicator": False,
    },
    "47": {
        "include_buyer": None, "allow_sequence_expiration_date": True,
        "allow_income_type": False, "allow_default_payment_forms": False,
        "allow_payment_term": True, "allow_service_all_included_indicator": False,
    },
}

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


def should_include_buyer(ecf_type: str, payload_include_buyer: bool) -> bool:
    """Return whether the current e-CF payload must include Comprador."""
    rule = ECF_TYPE_RULES.get(ecf_type, {}).get("include_buyer")
    if rule is True:
        return True
    if rule is False:
        return False
    return payload_include_buyer

PAYMENT_METHOD_TO_DGII = {
    "cash": "1",
    "transfer": "2",
    "card": "3",
}
