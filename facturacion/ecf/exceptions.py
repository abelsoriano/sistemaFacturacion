"""Custom exceptions for the DGII e-CF XML module."""


class ECFError(Exception):
    """Base exception for e-CF processing errors."""


class ECFValidationError(ECFError):
    """Raised when an e-CF document does not pass business or XML validation."""


class ECFTemporaryError(ECFError):
    """Raised when an external condition can succeed on retry."""


class ECFCeleryUnavailable(ECFTemporaryError):
    """Raised when Celery broker/result backend is not reachable."""


class ECFPermanentError(ECFError):
    """Raised when retrying without data/configuration changes is not useful."""


class UnsupportedECFTypeError(ECFError):
    """Raised when the requested e-CF type has no XML builder."""
