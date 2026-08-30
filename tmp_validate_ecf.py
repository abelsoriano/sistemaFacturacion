import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setting.settings')
import django
django.setup()
from django.db import transaction
from decimal import Decimal
from django.contrib.auth import get_user_model
from facturacion.models import Company, DGIICertificationPlan, DGIICertificationItem, ECFIssuerConfig
from facturacion.services.dgii_certification import DGIICertificationDocumentGenerator
from facturacion.ecf.validators.xsd import ECFXSDValidator

user_model = get_user_model()
with transaction.atomic():
    user = user_model.objects.create_user(username='dgii-validate-xml', password='pass')
    company = Company.objects.create(name='Empresa DGII XML Validate', rnc='401020001')
    plan = DGIICertificationPlan.objects.create(
        company=company,
        source_filename='validate-xml.xlsx',
        file_sha256='0' * 64,
        total_items=2,
        group_counts={'1': 2, '2': 0, '3': 0, '4': 0},
        imported_by=user,
    )
    ECFIssuerConfig.objects.create(
        company=company,
        business_name='Empresa DGII XML Validate Fiscal',
        trade_name=company.name,
        rnc=company.rnc,
        address='Calle DGII 1',
        municipality='010101',
        province='010000',
        phone='809-555-1234',
        email='fiscal@example.com',
        environment='testing',
        is_active=True,
    )

    validator = ECFXSDValidator()
    generator = DGIICertificationDocumentGenerator()
    tests = [
        ('43', 'E430000000008', {
            'FechaVencimientoSecuencia': '31-12-2026',
            'TipoPago': '1',
        }),
        ('33', 'E330000000001', {
            'TipoPago': '1',
            'IndicadorNotaCredito': '0',
            'NCFModificado': 'E320000000010',
            'FechaNCFModificado': '01-01-2026',
            'CodigoModificacion': '5',
        }),
    ]
    for index, (ecf_type, encf, extra) in enumerate(tests, start=1):
        raw_data = {
            'TipoeCF': ecf_type,
            'ENCF': encf,
            'RNCEmisor': company.rnc,
            'RazonSocialEmisor': company.name,
            'NombreComercial': company.name,
            'DireccionEmisor': 'Calle DGII 1',
            'Municipio': '010101',
            'Provincia': '010000',
            'TelefonoEmisor[1]': '809-555-1234',
            'CorreoEmisor': 'fiscal@example.com',
            'FechaEmision': '01-04-2020',
            'MontoExento': '100.00',
            'MontoTotal': '100.00',
            'IndicadorFacturacion[1]': '4',
            'NombreItem[1]': 'Servicio DGII',
            'IndicadorBienoServicio[1]': '1',
            'CantidadItem[1]': '1.00',
            'PrecioUnitarioItem[1]': '100.00',
            'MontoItem[1]': '100.00',
            'RNCComprador': '40222797082',
            'RazonSocialComprador': 'Cliente DGII',
        }
        raw_data.update(extra)
        item = DGIICertificationItem.objects.create(
            plan=plan,
            company=company,
            ecf_type=ecf_type,
            dgii_group=1,
            encf=encf,
            document_type=f'Tipo {ecf_type}',
            amount=Decimal('100.00'),
            receiver_rnc='40222797082',
            receiver_name='Cliente DGII',
            source_sheet='ECF',
            source_row=index + 1,
            raw_data=raw_data,
        )
        document = generator.generate_item(item=item, user=user)
        print('--- DOCUMENT', encf, 'TYPE', ecf_type)
        print(document.xml_content)
        try:
            validator.validate(ecf_type, document.xml_content)
            print('VALIDATION: OK')
        except Exception as exc:
            print('VALIDATION: FAILED')
            print(str(exc))
        print()
    transaction.set_rollback(True)
