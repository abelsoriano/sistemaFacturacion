"""Celery task discovery entrypoint for the facturacion app."""

from facturacion.ecf.tasks.dgii import check_status, retry_submission, submit_dgii  # noqa: F401
from facturacion.ecf.tasks.signing import sign_xml  # noqa: F401
from facturacion.ecf.tasks.xml import generate_xml  # noqa: F401
