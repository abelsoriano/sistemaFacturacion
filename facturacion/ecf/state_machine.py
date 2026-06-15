"""Explicit fiscal state machine for e-CF documents."""

from facturacion.ecf.exceptions import ECFValidationError


FISCAL_LOCKED_STATUSES = {"signed", "submitted", "processing", "accepted"}
SUBMISSION_TERMINAL_STATUSES = {"accepted", "rejected", "cancelled"}

ALLOWED_TRANSITIONS = {
    "draft": {"queued", "xml_generated", "cancelled", "error"},
    "queued": {"xml_generated", "signed", "pending", "submitted", "error", "cancelled"},
    "xml_generated": {"signed", "error", "cancelled"},
    "signed": {"pending", "submitted", "error"},
    "pending": {"submitted", "processing", "accepted", "rejected", "error"},
    "submitted": {"processing", "accepted", "rejected", "error"},
    "processing": {"accepted", "rejected", "error"},
    "accepted": set(),
    "rejected": {"draft", "xml_generated", "cancelled"},
    "error": {"draft", "queued", "xml_generated", "signed", "pending", "cancelled"},
    "cancelled": set(),
}


class ECFStateMachine:
    """Centralize valid e-CF transitions and idempotency checks."""

    def assert_transition(self, current: str, target: str) -> None:
        if current == target:
            return
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ECFValidationError(f"Transicion fiscal invalida: {current} -> {target}.")

    def assert_can_submit(self, document, *, force: bool = False) -> None:
        if document.status in SUBMISSION_TERMINAL_STATUSES:
            raise ECFValidationError(f"No se puede reenviar un e-CF en estado {document.status}.")
        if document.track_id and not force:
            raise ECFValidationError("El documento ya fue enviado a DGII. Usa force solo para reintentos controlados.")
        if document.status not in {"queued", "signed", "pending", "error"} and not force:
            raise ECFValidationError(f"El documento debe estar firmado antes de enviarse. Estado actual: {document.status}.")

    def assert_mutable_invoice(self, invoice) -> None:
        if invoice.is_fiscally_locked:
            raise ECFValidationError(invoice.fiscal_lock_reason)


FISCAL_ALLOWED_TRANSITIONS = {
    "draft": {"xml_generated"},
    "xml_generated": {"signed"},
    "signed": {"submitted"},
    "submitted": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}

JOB_ALLOWED_TRANSITIONS = {
    "idle": {"queued"},
    "queued": {"running", "failed"},
    "running": {"idle", "retrying", "failed"},
    "retrying": {"queued", "running", "failed"},
    "failed": {"queued"},
}

FISCAL_TERMINAL_STATUSES = {"accepted", "rejected"}
JOB_TERMINAL_STATUSES = {"idle", "failed"}


class ECFFiscalStateMachine:
    """New fiscal-only state machine introduced for the status split."""

    terminal_statuses = FISCAL_TERMINAL_STATUSES

    def assert_transition(self, current: str, target: str) -> None:
        if current == target:
            return
        allowed = FISCAL_ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ECFValidationError(f"Transicion fiscal invalida: {current} -> {target}.")

    def is_terminal(self, status: str) -> bool:
        return status in self.terminal_statuses


class ECFJobStateMachine:
    """New technical/job-only state machine introduced for async processing."""

    terminal_statuses = JOB_TERMINAL_STATUSES

    def assert_transition(self, current: str, target: str) -> None:
        if current == target:
            return
        allowed = JOB_ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ECFValidationError(f"Transicion tecnica invalida: {current} -> {target}.")

    def is_terminal(self, status: str) -> bool:
        return status in self.terminal_statuses
