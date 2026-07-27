"""Load an official RFCE XSD or example XML into the local contract folder."""

from __future__ import annotations

import shutil
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from facturacion.ecf.rfce_contract import rfce_schema_dir


class Command(BaseCommand):
    help = "Copia un XSD o XML ejemplo oficial RFCE a facturacion/ecf/schemas/rfce/."

    allowed_suffixes = {".xsd", ".xml"}

    def add_arguments(self, parser):
        parser.add_argument("source_path")
        parser.add_argument("--name", default="")

    def handle(self, *args, **options):
        source = Path(options["source_path"]).expanduser()
        if not source.exists() or not source.is_file():
            raise CommandError(f"No existe el archivo indicado: {source}")
        if source.suffix.lower() not in self.allowed_suffixes:
            raise CommandError("Solo se aceptan archivos .xsd o .xml oficiales RFCE.")

        target_dir = rfce_schema_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = options["name"].strip() or source.name
        target = target_dir / filename
        if target.suffix.lower() not in self.allowed_suffixes:
            raise CommandError("El nombre destino debe terminar en .xsd o .xml.")

        shutil.copyfile(source, target)
        self.stdout.write(self.style.SUCCESS(f"Contrato RFCE cargado: {target}"))
