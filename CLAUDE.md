# Sistema de Facturación Electrónica - Documentación Técnica

## 1. Descripción del Proyecto

Sistema ERP de facturación especializado en la **República Dominicana** con soporte para **Comprobantes Fiscales Electrónicos (e-CF)** bajo regulación de la **Dirección General de Impuestos Internos (DGII)**.

### Estado de Desarrollo
- **Fase**: Desarrollo e integración con DGII
- **Objetivo**: Pasar proceso de **homologación y certificación con DGII**
- **Funcionalidad Principal**: Generación, firma digital, envío y seguimiento de documentos fiscales electrónicos

### Áreas Funcionales
1. **Gestión de Facturación**: Facturas comerciales (E31/E32), cotizaciones, notas de crédito (E34)
2. **Control de Inventario**: Seguimiento de productos con código de barras
3. **Gestión de Clientes**: CRM básico con tipos de cliente
4. **Gestión de Activos/Herramientas**: Registro y seguimiento de activos
5. **Servicios de Mano de Obra**: Registro de servicios con abonos y pagos
6. **Multi-empresa**: Arquitectura SaaS con soporte para múltiples empresas

---

## 2. Stack Técnico

### Backend
| Componente | Versión | Propósito |
|-----------|---------|----------|
| **Django** | 5.2.1 | Framework web principal |
| **Python** | 3.12 | Lenguaje base |
| **PostgreSQL** | - | Base de datos principal |
| **Celery** | 5.4.0 | Procesamiento asincrónico de tareas |
| **Redis** | 5.2.1 | Broker de mensajes y caché |
| **Gunicorn** | 22.0.0 | Servidor WSGI |

### Dependencias Críticas (DGII/Seguridad)
| Librería | Versión | Uso |
|----------|---------|-----|
| **signxml** | 4.4.0 | Firma XMLDSig de documentos fiscales |
| **cryptography** | 48.0.0 | Criptografía y manejo de certificados |
| **zeep** | 4.3.2 | Cliente SOAP para comunicación DGII |
| **lxml** | 6.1.1 | Parsing y generación XML |

### Frontend
| Herramienta | Propósito |
|------------|----------|
| **React** | Framework UI |
| **React Router DOM** | 7.9.6 - Enrutamiento |
| **Lucide React** | Iconografía |
| **React Hot Toast** | Notificaciones |
| **SweetAlert2** | Diálogos modales |

### Infraestructura
- **Docker**: Containerización
- **Docker Compose**: Orquestación local (Redis, Celery, Flower)
- **Flower**: UI de monitoreo Celery

---

## 3. Estructura de Carpetas y Módulos

```
sistemaFacturacion/
├── facturacion/                         # App Django principal
│   ├── models.py                        # Modelos ORM (220+ líneas)
│   ├── views.py                         # Vistas legacy
│   ├── forms.py                         # Formularios Django
│   ├── tasks.py                         # Entrypoint de tareas Celery
│   ├── permissions.py                   # Permisos personalizados
│   ├── serializers.py                   # Serializadores DRF globales
│   ├── urls.py                          # URLs legacy
│   │
│   ├── api/                             # API REST (DRF)
│   │   ├── views/                       # Viewsets por recurso
│   │   │   ├── invoices.py              # API: Facturas
│   │   │   ├── credit_notes.py          # API: Notas de Crédito
│   │   │   ├── ecf_runtime.py           # API: Estados en tiempo real e-CF
│   │   │   ├── ecf_config.py            # API: Configuración DGII/e-CF
│   │   │   ├── dgii_certification.py    # API: Datos de homologación
│   │   │   ├── dgii_commercial_approval.py # API: Autorizaciones comerciales
│   │   │   └── dgii_public.py           # API: Consultas públicas DGII
│   │   ├── serializers/                 # Serializadores por tema
│   │   └── pagination.py                # Paginación personalizada
│   │
│   ├── ecf/                             # Módulo Comprobante Fiscal Electrónico
│   │   ├── ARCHITECTURE_ASYNC.md        # Documentación procesamiento asincrónico
│   │   ├── OPERATIONAL_VALIDATION.md    # Validación operativa y stress testing
│   │   ├── constants.py                 # Constantes DGII (tasa ITBIS, tipos e-CF)
│   │   ├── exceptions.py                # Excepciones personalizadas
│   │   ├── state_machine.py             # Máquina de estados fiscal
│   │   ├── rfce_contract.py             # Contrato/especificación DGII
│   │   │
│   │   ├── services/                    # Servicios principales
│   │   │   ├── xml_generation.py        # ✅ Generación de XML e-CF
│   │   │   ├── signing.py               # ✅ Firma XMLDSig con certificados
│   │   │   ├── dgii_submission.py       # ✅ Envío SOAP a DGII
│   │   │   ├── dgii_status.py           # Consulta estado TrackID
│   │   │   ├── status_transitions.py    # Máquina de estados helpers
│   │   │   ├── document_factory.py      # Factory pattern para e-CF
│   │   │   ├── certificate_policy.py    # Políticas de certificados
│   │   │   └── job_reconciliation.py    # Reconciliación de trabajos async
│   │   │
│   │   ├── xml/                         # Generación y manipulación XML
│   │   │   ├── builders/                # Builders por tipo e-CF
│   │   │   │   └── factory.py           # Factory builders (E31, E32, E34, etc.)
│   │   │   ├── serializers/             # XML serializers para validación
│   │   │   └── render.py                # Renderizado XML a string
│   │   │
│   │   ├── mappers/                     # Mapeo de datos a DTOs XML
│   │   │   └── invoice_mapper.py        # Invoice → ComprobanteFiscalElectronicoPayload
│   │   │
│   │   ├── signer/                      # ✅ Firma digital XMLDSig
│   │   │   └── xml_signer.py            # Implementación XMLDSig con signxml
│   │   │
│   │   ├── soap/                        # ✅ Cliente SOAP DGII
│   │   │   ├── auth.py                  # Autenticación token DGII
│   │   │   ├── environments.py          # Resolución endpoints (testing/prod)
│   │   │   ├── clients/                 # Clientes SOAP por servicio
│   │   │   │   └── dgii.py              # DGIISOAPClient
│   │   │   ├── parsers/                 # Parsers de respuestas SOAP
│   │   │   │   └── dgii.py              # DGIISOAPResponseParser
│   │   │   └── responses/               # DTOs de respuestas
│   │   │
│   │   ├── validators/                  # ✅ Validaciones críticas
│   │   │   ├── xsd.py                   # Validación XSD contra esquemas DGII
│   │   │   ├── business.py              # Reglas de negocio fiscal
│   │   │   ├── signature.py             # Validación de firmas XMLDSig
│   │   │   └── __init__.py
│   │   │
│   │   ├── certificates/                # ✅ Gestión de certificados
│   │   │   └── loader.py                # Cargador PKCS12
│   │   │
│   │   ├── queues/                      # Colas Celery dedicadas
│   │   │   └── routing.py               # Configuración de colas (ecf.xml, ecf.signing, ecf.dgii)
│   │   │
│   │   ├── tasks/                       # ✅ Tareas Celery asincrónicas
│   │   │   ├── xml.py                   # generate_xml (genera e-CF XML)
│   │   │   ├── signing.py               # sign_xml (firma XML con certificado)
│   │   │   ├── dgii.py                  # submit_dgii, check_status, retry_submission
│   │   │   └── __init__.py
│   │   │
│   │   ├── schemas/                     # Esquemas XSD DGII (RFCe)
│   │   │   ├── e-CF 31 v.1.0.xsd        # Factura de Crédito Fiscal Electrónica
│   │   │   ├── e-CF 32 v.1.0.xsd        # Factura de Consumo Electrónica
│   │   │   ├── e-CF 34 v.1.0.xsd        # Nota de Crédito Electrónica
│   │   │   └── ... (E33, E41, E43-47)
│   │   │
│   │   ├── utils/                       # Utilidades
│   │   ├── workers/                     # Workers async (placeholder)
│   │   └── __init__.py
│   │
│   ├── services/                        # Servicios de negocio
│   │   ├── numbering.py                 # Asignación transaccional de números
│   │   ├── fiscal_rules.py              # Cálculo de ITBIS, impuestos
│   │   ├── credit_notes.py              # Lógica de notas de crédito
│   │   ├── dgii_commercial_approval.py  # Sincronización de autorizaciones DGII
│   │   └── ...
│   │
│   ├── management/                      # Comandos Django custom
│   │   └── commands/                    # Management commands
│   │       └── stress_ecf_core.py       # Stress testing concurrencia
│   │
│   ├── migrations/                      # Migraciones Django (0022+)
│   │
│   └── __init__.py
│
├── facturacion_front/                   # Frontend React
│   ├── src/
│   │   ├── App.js                       # Componente raíz
│   │   ├── modules/
│   │   │   ├── ecf/                     # Módulo ECF/Dashboard
│   │   │   │   └── EcfDashboard.js      # Dashboard e-CF (E31/E32/E34 metrics)
│   │   │   └── ...
│   │   ├── components/                  # Componentes React
│   │   ├── services/                    # Clientes HTTP (axios)
│   │   ├── hooks/                       # Custom React hooks
│   │   └── utils/                       # Utilidades JS
│   │
│   └── package.json                     # Dependencias frontend
│
├── setting/                             # Configuración Django
│   ├── settings.py                      # Settings principales
│   ├── celery.py                        # Configuración Celery
│   ├── urls.py                          # URLs raíz
│   ├── wsgi.py                          # WSGI
│   └── asgi.py                          # ASGI
│
├── docker-compose.ecf.yml               # Docker Compose (Redis, Celery, Flower)
├── Dockerfile                           # Imagen Docker
├── manage.py                            # CLI Django
├── requirements.txt                     # Dependencias Python
├── package.json                         # Config monorepo (?)
└── README.md                            # (incompleto)
```

### Módulos Principales

#### **facturacion.ecf** - Motor ECF (CRÍTICO)
Core del procesamiento de comprobantes fiscales electrónicos. Responsable de:
- Generación XML validado contra XSD DGII
- Firma digital XMLDSig con certificados PKCS#12
- Envío SOAP a servicios DGII (pruebas/producción)
- Seguimiento de estados con TrackID
- Idempotencia y recuperación de fallos

#### **facturacion.api** - API REST
Expone endpoints DRF para:
- CRUD de facturas, cotizaciones, notas de crédito
- Monitoreo en tiempo real de e-CF (estado, intentos, errores)
- Configuración de emisores y certificados DGII
- Consultas a DGII (autorización NCF, estado comercial)

#### **facturacion.services** - Lógica de Negocio
- Numeración transaccional (facturas, cotizaciones, NC)
- Cálculo de impuestos (ITBIS 18%, 16%, 0%, exento)
- Gestión de notas de crédito y reversos
- Sincronización de datos con DGII

---

## 4. Convenciones de Código

### Naming Conventions

#### Models
```python
# SingularPascalCase
class Invoice(models.Model): ...
class ElectronicFiscalDocument(models.Model): ...
class ECFIssuerConfig(models.Model): ...
```

#### Fields
```python
# snake_case
invoice_number = models.CharField(...)
electronic_document = models.ForeignKey(...)
created_at = models.DateTimeField(auto_now_add=True)
```

#### Methods & Functions
```python
# snake_case
def allocate_next(cls, issuer, ecf_type): ...
def generate_xml(self, document): ...
def format_encf(self, number): ...
```

#### Constants
```python
# UPPER_CASE
ECF_VERSION = "1.0"
ITBIS_RATE_18 = Decimal("18.00")
SUPPORTED_XML_TYPES = {"31", "32", "34"}
```

#### Django REST Framework
```python
# ViewSet + Serializer pairs
class InvoiceViewSet(viewsets.ModelViewSet): ...
class InvoiceSerializer(serializers.ModelSerializer): ...
```

### Arquitectura de Patrones

#### 1. **Service Layer Pattern**
Servicios encapsulan lógica compleja:
```python
# facturacion/ecf/services/xml_generation.py
class ECFXMLGenerationService:
    def generate(self, document: ElectronicFiscalDocument) -> ECFXMLGenerationResult:
        """Generar XML validado y almacenar."""
```

#### 2. **State Machine Pattern**
Transiciones de estado explícitas:
```python
# facturacion/ecf/state_machine.py
class ECFStateMachine:
    def assert_transition(self, current: str, target: str) -> None:
        # Valida transiciones válidas
```

Estados fiscales: `draft → xml_generated → signed → submitted → processing → accepted|rejected`

#### 3. **Factory Pattern**
Builders polimórficos por tipo e-CF:
```python
# facturacion/ecf/xml/builders/factory.py
class ECFBuilderFactory:
    def get(self, ecf_type: str) -> ECFBuilder:
        # Retorna builder específico (E31, E32, E34, etc.)
```

#### 4. **Dataclass Results**
Resultados tipados de operaciones:
```python
@dataclass(frozen=True)
class ECFXMLGenerationResult:
    document: ElectronicFiscalDocument
    xml_content: str
    xsd_validated: bool
```

#### 5. **Celery Task Queueing**
Procesamiento asincrónico con reintentos:
```python
# facturacion/ecf/tasks/xml.py
@app.task(bind=True, queue='ecf.xml', max_retries=3)
def generate_xml(self, document_id: int):
    # Retry automático con exponential backoff
```

#### 6. **Idempotency via select_for_update()**
Bloqueo de fila para operaciones atómicas:
```python
locked_document = (
    ElectronicFiscalDocument.objects
    .select_for_update()
    .get(pk=document.pk)
)
```

### API Request/Response Patterns

#### Respuestas éxito (200/201)
```json
{
  "id": 123,
  "invoice_number": "F000001",
  "status": "pending",
  "electronic_document": {
    "encf": "E3200000000001",
    "fiscal_status": "xml_generated",
    "track_id": null
  }
}
```

#### Errores (400/422)
```json
{
  "code": "ECF_VALIDATION_ERROR",
  "message": "XML no cumple XSD",
  "details": {
    "field": "ecf_type",
    "reason": "Tipo e-CF 99 no soportado"
  }
}
```

---

## 5. Módulos CRÍTICOS Relacionados con DGII

⚠️ **PRECAUCIÓN**: Modificaciones aquí requieren validación exhaustiva y testing con DGII.

### 5.1 Generación de XML ([xml_generation.py](facturacion/ecf/services/xml_generation.py))
**Criticidad**: 🔴 CRÍTICA

- Responsable de transformar `Invoice` → `e-CF XML` validado
- Llamadas a:
  - `ECFXMLGenerationService.generate()` → transforma modelo → payload → builder → XML
  - `ECFXSDValidator.validate()` → valida contra XSD DGII oficial
- **Campos sensibles**:
  - `IndicadorServicioTodoIncluido` (servicios)
  - `IndicadorNotaCredito` (notas de crédito E34)
  - Cálculo de ITBIS por línea
- **Impact**: Un error aquí rechaza el documento en DGII
- **Testing**: 
  ```bash
  python manage.py test facturacion.tests.ECFXMLValidationTests
  ```

### 5.2 Firma Digital ([signer/xml_signer.py](facturacion/ecf/signer/xml_signer.py))
**Criticidad**: 🔴 CRÍTICA

- Implementa XMLDSig (firma digital certificada)
- Utiliza `signxml` + certificados PKCS#12
- **Campos sensibles**:
  - Certificado subject/issuer matching RNC
  - Algoritmo RSA-SHA256
  - Canonicalización XML (Exclusive)
- **Impact**: Firma inválida = rechazo automático DGII
- **Cambios prohibidos**: Algoritmo, canonicalización, orden de elementos
- **Testing**:
  ```bash
  python manage.py test facturacion.tests.ECFSigningTests
  ```

### 5.3 Comunicación SOAP DGII ([soap/clients/dgii.py](facturacion/ecf/soap/clients/dgii.py))
**Criticidad**: 🔴 CRÍTICA

- Cliente SOAP para endpoints DGII:
  - `Autorizacion` → genera NCF-e/RNC autorizados
  - `Validacion` → envía XML e-CF firmado
  - `Estadistica` → consulta estado TrackID
- **Endpoints**:
  - Testing: `https://uat-dgii.example.com/...` 
  - Producción: `https://dgii.example.com/...`
- **Cambios prohibidos**: URLs, namespaces SOAP, estructura de requests
- **Testing**: Usar environment `testing` antes de cambios en `production`

### 5.4 Validación de Reglas de Negocio ([validators/business.py](facturacion/ecf/validators/business.py))
**Criticidad**: 🟡 ALTA

- Valida antes de generar XML:
  - RNC debe tener 9-11 dígitos
  - Certificado debe coincidir con RNC emisor
  - Secuencias e-NCF disponibles
  - Montos positivos, impuestos correctos
  - Tipo cliente (E31 vs E32)
- **Cambios comunes**: Agregar validaciones nuevas (seguro si mantiene orden)
- **Testing**:
  ```bash
  python manage.py test facturacion.tests.ECFBusinessValidationTests
  ```

### 5.5 Secuencias e-NCF ([models.py - ECFSequence](facturacion/models.py#L1600))
**Criticidad**: 🟡 ALTA

- Rango autorizado DGII por tipo e-CF (E31, E32, E34, E33, E41, E43-47)
- **Método crítico**: `ECFSequence.allocate_next(issuer, ecf_type)`
  - Atomic transaction con `select_for_update()`
  - Nunca duplica e-NCF bajo concurrencia
- **Cambios prohibidos**: Algoritmo de allocate_next
- **Testing concurrencia**:
  ```bash
  python manage.py stress_ecf_core --invoices 200 --workers 16 --enqueue
  ```

### 5.6 Cálculo de ITBIS ([services/fiscal_rules.py](facturacion/services/fiscal_rules.py))
**Criticidad**: 🟡 ALTA

- Calcula impuestos por línea:
  - Tasa 18% (código 1)
  - Tasa 16% (código 2)
  - Tasa 0% (código 3)
  - Exento (código 4)
- **Cambios prohibidos**: Tasas, redondeo, indicadores de ITBIS
- **Testing**: Validar montos totales vs DGII

### 5.7 Estado del Documento ([state_machine.py](facturacion/ecf/state_machine.py))
**Criticidad**: 🟡 ALTA

- Máquina de estados explícita para e-CF:
  - `draft` → `xml_generated` → `signed` → `submitted` → `processing` → `accepted|rejected`
- **Estados terminales**: `accepted`, `rejected`, `cancelled`
- **Cambios prohibidos**: Agregar estados intermedios sin validar con DGII
- **Testing**: Ver `test_e34_credit_note_generates_xsd_valid_reference_xml`

### 5.8 Gestión de Certificados ([models.py - ECFIssuerConfig](facturacion/models.py#L1750))
**Criticidad**: 🟡 ALTA

- Almacenamiento y validación de certificados PKCS#12:
  - Ruta local (legacy), almacenamiento Django, KMS, Vault
  - Validación: fecha vigencia, RNC, fingerprint SHA-256
- **Cambios**: Implementar backend seguro (KMS/Vault) antes de producción
- **Testing**: `ECFCertificateTests`

### 5.9 Notas de Crédito E34 ([models.py - CreditNote](facturacion/models.py#L1560))
**Criticidad**: 🟡 ALTA

- Reverso fiscal de invoices aceptadas:
  - Mantiene referencia `origin_invoice`
  - Reconciliación de inventario
  - Estados: `draft → issued → cancelled`
- **Cambios prohibidos**: Lógica de referencia a factura origen
- **Testing**: 
  ```bash
  python manage.py test facturacion.tests.E34FiscalValidationTests
  ```

### 5.10 Event Log Auditoria ([models.py - ECFEventLog](facturacion/models.py))
**Criticidad**: 🟢 MEDIA

- Trazabilidad completa de cambios e-CF:
  - Evento: `xml_generated`, `signed`, `submitted`, `accepted`, `rejected`, `error`
  - Payload: datos de la operación
  - Error message y auditoria
- **Cambios**: Seguro agregar nuevos tipos de evento
- **Testing**: Verificar logs en `ECFEventLog.objects.filter(...)`

---

## 6. Flujos Principales y Transacciones

### Flujo: Crear y Enviar Factura E32 a DGII
```
1. API POST /api/invoices/
   └─ Crear Invoice + InvoiceDetail(s)
   └─ Validar stock, precios

2. API POST /api/invoices/{id}/electronic-document/
   └─ Crear ElectronicFiscalDocument (status: draft)
   └─ Asignar e-NCF vía ECFSequence.allocate_next()
   └─ Validar reglas fiscales → ECFBusinessValidator

3. API POST /api/electronic-documents/{id}/async-process/
   └─ Encolar: generate_xml → sign_xml → submit_dgii
   └─ Celery task chain: ecf.xml → ecf.signing → ecf.dgii

4. Celery: generate_xml
   └─ Mapear Invoice → ComprobanteFiscalElectronicoPayload
   └─ Builder E32 → XML
   └─ Validar XSD local
   └─ Guardar xml_content + status: xml_generated

5. Celery: sign_xml
   └─ Cargar certificado PKCS#12
   └─ Firmar XML con XMLDSig
   └─ Validar firma → status: signed

6. Celery: submit_dgii
   └─ Llamar SOAP Autorizacion/Validacion DGII
   └─ Recibir TrackID si éxito
   └─ Guardar track_id + status: submitted

7. Monitoreo: check_status (cada N minutos)
   └─ Consultar DGII vía Estadistica(TrackID)
   └─ Actualizar fiscal_status: processing → accepted|rejected

8. Notificación al usuario
   └─ Factura aceptada: estado "accepted"
   └─ Error: estado "error" + last_error detallado
```

### Flujo: Revertir con Nota de Crédito E34
```
1. API POST /api/credit-notes/
   └─ Crear CreditNote referenciando Invoice aceptada
   └─ Validar cantidades vs E34 CreditNoteDetail(s)

2. API POST /api/credit-notes/{id}/electronic-document/
   └─ Crear ElectronicFiscalDocument (ecf_type: 34)
   └─ Mapear CreditNote → ComprobanteFiscalElectronicoPayload
   └─ Agregar IndicadorNotaCredito + InformacionReferencia

3. Procesar E34 igual que E32 (generate → sign → submit)
   └─ XML incluye NCFModificado (e-NCF de factura origen)

4. Si E34 aceptada:
   └─ Restaurar inventario (stock += cantidad)
   └─ Marcar CreditNote.status: confirmed
   └─ Actualizar Invoice.is_fiscally_locked
```

---

## 7. Testing y Validación

### Test Coverage Actual
- `facturacion/tests.py`: Tests unitarios y de integración
- `OPERATIONAL_VALIDATION.md`: Guía de stress testing concurrencia
- Comandos:
  ```bash
  python manage.py test facturacion
  python manage.py stress_ecf_core --invoices 200 --workers 16 --enqueue
  ```

### Validaciones de Certificación
Antes de pasar homologación DGII:
1. ✅ E31/E32/E34 generen XML válido XSD
2. ✅ Firmas digitales verificadas por DGII
3. ✅ Secuencias e-NCF sin duplicados bajo concurrencia
4. ✅ Reversos E34 referencian correctamente origen
5. ✅ ITBIS calculado correctamente (18%, 16%, 0%, exento)
6. ✅ Reintento automático en fallos temporales
7. ✅ Idempotencia: reintentos no crean duplicados

---

## 8. Variables de Entorno Críticas

```bash
# Base de datos
DATABASE_URL=postgresql://user:pass@localhost/facturacion
ALLOWED_HOSTS=localhost,127.0.0.1,mi-dominio.com

# Seguridad
DEBUG=False  # NUNCA True en producción
SECRET_KEY=xxx-super-secreto-xxx

# DGII
DGII_ENVIRONMENT=testing|certification|production
DGII_TOKEN_USER=usuario-dgii
DGII_TOKEN_PASSWORD=xxx
DGII_ENDPOINT_SOAP=https://uat-dgii.example.com/...

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Storage de certificados (legacy)
ECF_CERTIFICATE_PATH=/app/media/ecf_certificates/
```

---

## 9. Documentación Adicional

- [ARCHITECTURE_ASYNC.md](facturacion/ecf/ARCHITECTURE_ASYNC.md) - Detalles flujo async Celery
- [OPERATIONAL_VALIDATION.md](facturacion/ecf/OPERATIONAL_VALIDATION.md) - Stress testing
- API: Documentación OpenAPI en `/api/schema/`
- Migrations: 22+ migraciones en `facturacion/migrations/`

---
## 10. Instrucciones para Claude Code (Agentes IA)

### Reglas de Seguridad No Negociables
- Antes de modificar cualquier archivo en `facturacion/ecf/`, explica el impacto 
  en homologación DGII y espera confirmación explícita.
- NUNCA modifiques sin aprobación explícita del usuario:
  - `signer/xml_signer.py` (algoritmo de firma XMLDSig)
  - `soap/clients/dgii.py` (endpoints, estructura SOAP)
  - `ECFSequence.allocate_next()` en models.py (numeración e-NCF)
  - `schemas/*.xsd` (esquemas oficiales DGII)
  - `state_machine.py` (transiciones de estado fiscal)

### Flujo de Trabajo
- Trabaja siempre en una rama nueva (`git checkout -b fix/nombre-del-fix`), 
  nunca hagas commit directo a `main`.
- Antes de tocar `models.py` o crear migraciones, muestra el diff propuesto 
  y espera aprobación.
- Después de cualquier cambio en el módulo `ecf/`, corre los tests relacionados 
  antes de dar el cambio por terminado:

**Último actualizado**: 2026-07-27  
**Maintainer**: Sistema de Facturación DGII
