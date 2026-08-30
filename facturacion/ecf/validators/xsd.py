"""XSD validation for generated e-CF XML."""

from pathlib import Path

from django.conf import settings
from lxml import etree

from facturacion.ecf.exceptions import ECFValidationError


class ECFXSDValidator:
    """Validate e-CF XML against official DGII XSD files."""

    schema_files = {
        "31": "e-CF 31 v.1.0.xsd",
        "32": "e-CF 32 v.1.0.xsd",
        "33": "e-CF 33 v.1.0.xsd",
        "34": "e-CF 34 v.1.0.xsd",
        "41": "e-CF 41 v.1.0.xsd",
        "43": "e-CF 43 v.1.0.xsd",
        "44": "e-CF 44 v.1.0.xsd",
        "45": "e-CF 45 v.1.0.xsd",
        "46": "e-CF 46 v.1.0.xsd",
        "47": "e-CF 47 v.1.0.xsd",
        "RFCE": "rfce/RFCE 32 v.1.0.xsd",
    }

    def __init__(self, schemas_dir: Path | None = None) -> None:
        self.schemas_dir = schemas_dir or Path(settings.BASE_DIR) / "facturacion" / "ecf" / "schemas"

    def validate(self, ecf_type: str, xml_content: str) -> None:
        """Raise ECFValidationError when XML does not match the DGII XSD."""
        schema_path = self._schema_path(ecf_type)
        if not schema_path.exists():
            raise ECFValidationError(f"No existe XSD local para e-CF tipo {ecf_type}: {schema_path}")

        parser = etree.XMLParser(remove_blank_text=True)
        schema_doc = self._load_schema(schema_path, parser)
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.fromstring(xml_content.encode("utf-8"), parser)

        if not schema.validate(xml_doc):
            messages = [str(error) for error in schema.error_log]
            raise ECFValidationError("XML no válido contra XSD DGII: " + " | ".join(messages))

    def _schema_path(self, ecf_type: str) -> Path:
        filename = self.schema_files.get(ecf_type)
        if not filename:
            raise ECFValidationError(f"No hay XSD configurado para e-CF tipo {ecf_type}.")
        return self.schemas_dir / filename

    def _load_schema(self, schema_path: Path, parser: etree.XMLParser) -> etree._ElementTree:
        """Load a DGII XSD and normalize known published typos in memory."""
        content = schema_path.read_text(encoding="utf-8")
        content = content.replace(
            'name=" IndicadorServicioTodoIncluidoType"',
            'name="IndicadorServicioTodoIncluidoType"',
        )
        content = content.replace('[12][$0-9]', '[12][0-9]')
        content = content.replace('((?:19|20)\\d{2})', '((19|20)[0-9]{2})')
        content = content.replace('(?:.[0-9]{2})?', '(.[0-9]{2})?')
        return etree.ElementTree(etree.fromstring(content.encode("utf-8"), parser))
