# ERP Domain Refactor Plan

Objetivo: limpiar el dominio comercial/fiscal antes de multiempresa SaaS, evitando duplicidad entre POS, Sales e Invoices.

## Diagnostico actual

- `Sale` representa una venta simple, pero `SaleCreateView` tambien crea una `Invoice` y dispara e-CF.
- `FastSalesForm` y `SalesForm` son dos experiencias POS/comercial que terminan llamando `/sales/`.
- `Invoice` es el documento fiscal principal y ya concentra e-CF, bloqueo fiscal y notas de credito.
- No existe flujo no fiscal de cotizacion.
- La navegacion expone `Sales`, `FastSales` e `Invoices` como si fueran modulos independientes, pero funcionalmente se pisan.

## Arquitectura funcional objetivo

### 1. POS / Venta Rapida

Proposito: mostrador, consumidor final, cobro inmediato, impresion rapida.

- UI objetivo: `POS`.
- Endpoint objetivo: `POST /api/v1/pos/sales/`.
- Documento comercial: `Invoice` con `receipt_type=ticket` o `invoice` segun politica fiscal.
- Cliente: opcional; por defecto consumidor final.
- Fiscal: E32 automatico cuando se genera factura fiscal.
- Inventario: descuenta inmediatamente.
- Pago: contado.
- Impresion: ticket rapido desde frontend o agente local, no desde servidor SaaS.

Decision: `FastSales` debe convertirse formalmente en `POS`.

### 2. Facturacion Formal

Proposito: factura a cliente registrado, RNC, credito fiscal, cuentas por cobrar.

- UI objetivo: `Facturacion`.
- Endpoint objetivo: `POST /api/v1/invoices/`.
- Documento comercial/fiscal: `Invoice`.
- Cliente: requerido para E31.
- Fiscal:
  - RNC valido -> E31 automatico.
  - consumidor final -> E32 automatico.
- Estados comerciales:
  - `draft` o `pending`
  - `issued`
  - `paid`
  - `cancelled`
  - `refunded`
- Cuentas por cobrar:
  - factura pendiente puede tener saldo.
  - pago posterior no debe regenerar e-CF.

Decision: `Invoice` queda como flujo fiscal principal.

### 3. Cotizaciones / Estimates

Proposito: documento comercial no fiscal previo a venta.

- Modelo nuevo recomendado: `Quotation`.
- Detalles: `QuotationDetail`.
- Estados:
  - `draft`
  - `sent`
  - `approved`
  - `rejected`
  - `expired`
- No descuenta inventario.
- No genera e-CF.
- No consume e-NCF.
- No firma XML.
- Conversion:
  - `quotation -> invoice`
  - copia cliente, items, descuentos y notas.
  - al convertir, recien se descuenta inventario y se evalua E31/E32.
  - la cotizacion queda vinculada a la factura generada.

Endpoint objetivo:

- `GET/POST /api/v1/quotations/`
- `POST /api/v1/quotations/{id}/send/`
- `POST /api/v1/quotations/{id}/approve/`
- `POST /api/v1/quotations/{id}/reject/`
- `POST /api/v1/quotations/{id}/convert-to-invoice/`

### 4. Nota de Credito

Proposito: reverso fiscal/comercial de factura emitida.

- Modelo actual `CreditNote` se mantiene.
- Siempre nace desde `Invoice`.
- E34 automatico.
- Reversa inventario segun politica.
- No debe editarse ni borrarse.

## Que eliminar o unificar

### Mantener

- `Invoice`: documento fiscal/comercial principal.
- `CreditNote`: reverso fiscal.
- `ElectronicFiscalDocument`: documento fiscal electronico.
- `FastSalesForm`, renombrado funcionalmente a POS.

### Deprecar gradualmente

- `Sale` y `SaleDetail` como modelos de negocio primario.
- `/sales/` como endpoint principal.
- `SalesForm` si duplica POS e Invoice.

### Mantener temporalmente por compatibilidad

- `/sales/` debe seguir funcionando como alias legacy hacia POS.
- `SaleList` puede convertirse en vista historica de tickets POS mientras se migra.
- Reportes de ventas deben migrar a consultar `Invoice` y pagos, no `Sale`.

## Mapa de flujo recomendado

### POS

1. Usuario abre POS.
2. Escanea/agrega productos.
3. Cobra.
4. Backend crea `Invoice` pagada.
5. Backend descuenta inventario.
6. Backend crea E32 si aplica.
7. Backend encola e-CF.
8. UI imprime ticket y muestra estado fiscal.

### Factura Formal

1. Usuario selecciona cliente registrado.
2. Agrega items.
3. Define contado/credito.
4. Backend calcula totales fiscales.
5. Backend crea `Invoice`.
6. RNC valido genera E31.
7. Si contado, marca pagada; si credito, queda pendiente/cxc.
8. e-CF se procesa async.

### Cotizacion

1. Usuario crea cotizacion `draft`.
2. La envia: `sent`.
3. Cliente aprueba: `approved`.
4. Usuario convierte a factura.
5. Solo en conversion se descuenta inventario y se genera e-CF.

## Migracion sin romper sistema actual

### Paso 1 - Naming y UX

- Renombrar menu `FastSales` a `POS`.
- Ocultar o marcar `Sales` como legacy.
- Mantener rutas antiguas con redirects:
  - `/Fastsales` -> `/pos`
  - `/sales` -> `/pos` o flujo legacy temporal.

### Paso 2 - Servicio POS

- Crear `POSCheckoutService`.
- Internamente puede usar `InvoiceCreationService`.
- Respuesta estandar: invoice, fiscal document, payment, print payload.
- `/sales/` llama al nuevo servicio como adapter legacy.

### Paso 3 - Cotizaciones

- Agregar `Quotation` y `QuotationDetail`.
- Agregar servicio `QuotationConversionService`.
- Conversion usa `InvoiceCreationService` con `auto_ecf=True`.
- Tests: cotizacion no crea e-CF; conversion si.

### Paso 4 - Reportes

- Migrar dashboard/reportes desde `Sale` a `Invoice`.
- Mantener `Sale` solo como tabla historica hasta migracion completa.

### Paso 5 - Remocion legacy

- Cuando no haya reportes ni UI dependiendo de `Sale`, congelar escritura a `Sale`.
- Mantener lectura historica por una version.
- Luego migrar datos o archivar.

## UX objetivo

Menu recomendado:

- Ventas
  - POS
  - Facturas
  - Cotizaciones
  - Notas de credito
- Catalogo
  - Productos
  - Clientes
- Fiscal
  - e-CF
  - Secuencias
  - Emisores
- Operaciones
  - Inventario
  - Reportes

Estados visibles:

- Cotizacion: draft/sent/approved/rejected/expired.
- Factura: pending/paid/cancelled/refunded.
- Fiscal: draft/queued/xml_generated/signed/pending/accepted/rejected/error.
- Nota credito: issued/cancelled.

## Prioridad de implementacion

1. Crear modulo `quotations` sin tocar ventas existentes.
2. Crear `POSCheckoutService` y adaptar `/sales/`.
3. Renombrar UX a POS y reducir duplicidad.
4. Migrar reportes a `Invoice`.
5. Deprecar `Sale` como escritura primaria.
