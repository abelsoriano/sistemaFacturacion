"""Celery application for the Django billing project."""

from __future__ import annotations

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setting.settings")

app = Celery("sistema_facturacion")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.imports = (
    "facturacion.tasks",
    "facturacion.ecf.tasks.xml",
    "facturacion.ecf.tasks.signing",
    "facturacion.ecf.tasks.dgii",
)
