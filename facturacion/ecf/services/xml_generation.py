"""Service layer for generating, validating and storing e-CF XML."""

from dataclasses import dataclass

from django.db import transaction

from facturacion.models import ECFEventLog, ElectronicFiscalDocument
from facturacion.ecf.state_machine import ECFStateMachine
from facturacion.ecf.services.status_transitions import ECFStatusTransitionService
from facturacion.ecf.mappers.invoice_mapper import InvoiceECFMapper
from facturacion.ecf.validators.business import ECFBusinessValidator
from facturacion.ecf.validators.xsd import ECFXSDValidator
from facturacion.ecf.xml.builders.factory import ECFBuilderFactory
from facturacion.ecf.xml.render import render_xml


@dataclass(frozen=True)
class ECFXMLGenerationResult:
    """Result returned after generating an e-CF XML document."""

    document: ElectronicFiscalDocument
    xml_content: str
    xsd_validated: bool


class ECFXMLGenerationService:
    """Generate DGII e-CF XML from an ElectronicFiscalDocument."""

    def __init__(
        self,
        mapper: InvoiceECFMapper | None = None,
        business_validator: ECFBusinessValidator | None = None,
        xsd_validator: ECFXSDValidator | None = None,
        builder_factory: ECFBuilderFactory | None = None,
    ) -> None:
        self.mapper = mapper or InvoiceECFMapper()
        self.business_validator = business_validator or ECFBusinessValidator()
        self.xsd_validator = xsd_validator or ECFXSDValidator()
        self.builder_factory = builder_factory or ECFBuilderFactory()
        self.state_machine = ECFStateMachine()
        self.status_transitions = ECFStatusTransitionService()

    @transaction.atomic
    def generate(self, document: ElectronicFiscalDocument, user=None, validate_xsd: bool = True) -> ECFXMLGenerationResult:
        """Generate XML, optionally validate XSD, store it and register an event."""
        locked_document = (
            ElectronicFiscalDocument.objects
            .select_for_update()
            .select_related("issuer", "sequence")
            .get(pk=document.pk)
        )

        self.business_validator.validate(locked_document)
        self.status_transitions.fiscal_state_machine.assert_transition(locked_document.fiscal_status, "xml_generated")
        payload = self.mapper.map(locked_document)
        builder = self.builder_factory.get(locked_document.ecf_type)
        root = builder.build(payload)
        xml_content = render_xml(root)

        if validate_xsd:
            self.xsd_validator.validate(locked_document.ecf_type, xml_content)

        transition = self.status_transitions.transition(
            locked_document,
            fiscal_status="xml_generated",
            source="xml_generation",
            reason="XML e-CF generado.",
            extra_update_fields={"xml_content": xml_content},
        )
        locked_document = transition.document

        ECFEventLog.objects.create(
            electronic_document=locked_document,
            event_type="xml_generated",
            message="XML e-CF generado y almacenado.",
            payload={"xsd_validated": validate_xsd},
            created_by=user,
        )

        return ECFXMLGenerationResult(
            document=locked_document,
            xml_content=xml_content,
            xsd_validated=validate_xsd,
        )
