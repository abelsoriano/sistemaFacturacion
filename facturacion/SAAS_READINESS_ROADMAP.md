# Stabilization & SaaS Readiness

Este roadmap congela multiempresa hasta estabilizar seguridad, contrato API, consistencia fiscal y arquitectura.

## Fase A1 - Quick wins aplicados

- `SECRET_KEY` obligatorio cuando `DEBUG=False`.
- `DEBUG` y CORS controlados por entorno.
- Hardening HTTPS/cookies/HSTS cuando `DEBUG=False`.
- Media servida por Django solo en `DEBUG`.
- API versionada en `/api/v1/` manteniendo `/api/` temporalmente.
- Paginacion global DRF.
- Handler de errores DRF normalizado.
- Serializer fiscal sin XML firmado, request/response SOAP ni rutas/passwords de certificados.
- Endpoint de auditoria para artefactos sensibles:
  - `GET /api/v1/ecf/documents/{id}/audit-artifact/xml/`
  - `GET /api/v1/ecf/documents/{id}/audit-artifact/signed-xml/`
  - `GET /api/v1/ecf/documents/{id}/audit-artifact/dgii-request/`
  - `GET /api/v1/ecf/documents/{id}/audit-artifact/dgii-response/`
- Calculo fiscal centralizado en backend con `FiscalCalculationService`.
- Frontend deja de permitir tasa ITBIS manual en factura.

## Fase A2 - Refactor backend por dominios

Objetivo: dividir `facturacion/views.py` sin cambiar rutas.

Orden recomendado:

1. `facturacion/api/views/auth.py`
   - `LoginView`, `ProfileView`, `VerifyTokenView`.
2. `facturacion/api/views/catalog.py`
   - categorias, productos, historial, bajo stock.
3. `facturacion/api/views/sales.py`
   - ventas POS, listado, anulaciones comerciales.
4. `facturacion/api/views/invoices.py`
   - facturas, clientes, notas de credito.
5. `facturacion/api/views/ecf.py`
   - emisores, secuencias, documentos, eventos, async monitor.
6. `facturacion/api/views/reports.py`
   - PDFs y dashboard.
7. `facturacion/api/views/printing.py`
   - ZPL y listado de impresoras, con plan para moverlo a agente local.

Cada modulo debe tener tests de rutas antes de extraer la siguiente pieza.

## Fase A3 - Contrato API profesional

- Definir envelope opcional para acciones async: `{data, meta}`.
- Estandarizar errores: `{detail, code, fields}`.
- Documentar filtros y ordering por recurso.
- Separar serializers de escritura/lectura para facturas, e-CF y usuarios.
- Agregar `select_related/prefetch_related` a todos los listados de alto trafico.
- Agregar rate limiting en auth y acciones DGII.

## Fase A4 - Frontend modular

Prioridad por tamano y riesgo:

1. `FastSalesForm.js`
   - `usePosCart`, `useProductSearch`, `PaymentPanel`, `CartTable`, `BarcodeInput`.
2. `InvoiceForm.js`
   - `useInvoiceDraft`, `InvoiceItemsTable`, `FiscalTotalsPanel`, `ClientSelector`.
3. `InvoiceDetail.js`
   - `FiscalStatusPanel`, `CreditNotePanel`, `EventsPanel`, `TotalsPanel`.
4. `ProductForm.js` y `ProductList.js`
   - servicios de catalogo y componentes reutilizables de tabla/filtros.
5. `AssetForm.js`
   - dividir por tabs/secciones; no bloquear SaaS fiscal pero reduce deuda UI.

## Fase A5 - Observabilidad y operacion

- Health checks:
  - `/health/live/`
  - `/health/ready/` con DB, Redis y Celery broker.
- Metricas:
  - documentos por estado
  - retries vencidos
  - edad maxima en `queued`
  - secuencias restantes
  - errores DGII por codigo
- Alertas:
  - `queued` mayor a 10 minutos
  - `pending` sin status check
  - secuencia bajo umbral
  - documentos `error` sin accion

## Fase B - Pre-multiempresa

No iniciar hasta completar A1-A4.

- Agregar modelo `Company/Tenant`.
- Definir ownership en facturas, productos, clientes, emisores, secuencias, documentos y eventos.
- Constraints compuestos por tenant.
- Middleware/contexto tenant.
- Querysets tenant-aware por defecto.
- Tests de aislamiento: usuario A nunca ve datos de empresa B.
