# Validacion operativa fiscal antes de multiempresa SaaS

Esta fase valida el nucleo fiscal con una sola empresa antes de introducir aislamiento multiempresa.
El objetivo es demostrar que secuencias, XML, firma, envio DGII, reversos e inventario soportan concurrencia real.

## Alcance

- E31/E32/E34 con XSD local.
- Asignacion concurrente de e-NCF.
- Idempotencia de documento fiscal, XML, firma y envio DGII.
- Reversos parciales E34 concurrentes.
- Retries y recuperacion de errores DGII/Celery/Redis.
- Observabilidad basica: logs estructurados, eventos `ECFEventLog`, estado Celery y metricas por consulta.

## Pruebas automatizadas

Ejecutar:

```powershell
python manage.py test facturacion
```

Cobertura agregada:

- `E34FiscalValidationTests.test_e34_credit_note_generates_xsd_valid_reference_xml`
  valida que una nota de credito E34 genere XML con `IndicadorNotaCredito`, `InformacionReferencia`,
  `NCFModificado` y pase el XSD `e-CF 34 v.1.0.xsd`.
- `E34FiscalValidationTests.test_concurrent_partial_reversals_cannot_exceed_origin_quantity`
  valida que los reversos parciales no excedan la cantidad de la factura origen.
- `ECFConcurrencyHardeningTests.test_concurrent_sequence_allocation_has_no_duplicate_encf`
  valida que `ECFSequence.allocate_next()` no duplique e-NCF bajo concurrencia.
- `ECFConcurrencyHardeningTests.test_concurrent_document_creation_for_same_invoice_is_idempotent`
  valida que varios intentos simultaneos sobre la misma factura creen un solo `ElectronicFiscalDocument`.

## Stress testing local

Ejecutar contra una base Postgres de pruebas, no contra produccion:

```powershell
python manage.py stress_ecf_core --invoices 200 --workers 16 --items 8 --reversals 40
```

Por defecto el comando no encola Celery para aislar locks DB, secuencias e inventario. Para incluir Redis/Celery:

```powershell
python manage.py stress_ecf_core --invoices 200 --workers 16 --items 8 --reversals 40 --enqueue
```

El reporte JSON debe cumplir:

- `invoice_stress.errors` vacio.
- `invoice_stress.duplicate_encfs` vacio.
- `idempotency_probe.duplicate_documents` en `false`.
- `document_integrity.invoice_duplicate_documents` vacio.
- `document_integrity.credit_note_duplicate_documents` vacio.
- En reversos, `successful` no debe exceder la cantidad disponible de la factura origen.

## Escenarios manuales de resiliencia

1. Redis caido antes de encolar:
   - Detener Redis.
   - Crear una factura fiscal con auto e-CF.
   - Esperado: factura y `ElectronicFiscalDocument` persisten; `last_error` registra indisponibilidad de Celery/Redis; no se pierde e-NCF.

2. Worker caido despues de encolar:
   - Encender Redis, detener workers.
   - Crear lotes con `--enqueue`.
   - Encender workers.
   - Esperado: documentos en `queued` avanzan sin doble XML, doble firma ni doble envio.

3. Timeout DGII:
   - Configurar mock/cliente DGII para lanzar timeout temporal.
   - Esperado: `next_retry_at` poblado, evento `retry_scheduled`, backoff exponencial y estado no terminal hasta agotar retries.

4. Reintento operador:
   - Documento firmado sin `track_id`.
   - Ejecutar retry desde endpoint/comando que use `enqueue_retry_submission`.
   - Esperado: si ya hay `track_id`, se omite; si no hay XML firmado, firma y reintenta.

5. Recuperacion post-fallo:
   - Buscar documentos `error`, `queued` antiguos o `pending` sin avance.
   - Reprocesar solo los que no tengan `track_id` o que requieran consulta de estado.

## Riesgos detectados

- `Invoice.invoice_number` y `CreditNote.credit_note_number` aun usan el ultimo ID para numeracion interna.
  Tienen `unique=True`, pero bajo concurrencia podrian requerir retry si la DB rechaza duplicado. No afecta e-NCF,
  pero conviene moverlos a una tabla de secuencias internas antes de SaaS.
- `select_for_update()` protege correctamente en Postgres. SQLite no representa la misma concurrencia; estas pruebas
  deben ejecutarse contra Postgres.
- Los XML E34 dependen de que la factura origen ya tenga e-CF fiscalmente emitido (`signed`, `submitted`,
  `processing` o `accepted`) y e-NCF persistido.
- Si Celery queda en `acks_late` con workers matados a mitad de firma/envio, la idempotencia esta en DB; aun asi
  hay que monitorear documentos con `queued` viejo.

## Hardening recomendado antes de SaaS

- Crear secuencias internas transaccionales para `invoice_number` y `credit_note_number`.
- Agregar comando de recuperacion operacional para reencolar documentos atascados por estado y edad.
- Exponer metricas Prometheus: documentos por estado, retries pendientes, edad maxima en cola, tasa de rechazos,
  secuencias restantes por tipo e-CF.
- Definir alertas: `next_retry_at` vencido, `queued` mayor a 10 minutos, `pending` sin status check, secuencia menor
  a umbral, rechazos DGII por encima de baseline.
- Mantener `CELERY_WORKER_PREFETCH_MULTIPLIER=1` y colas separadas (`ecf.xml`, `ecf.signing`, `ecf.dgii`,
  `ecf.status`) para reducir starvation.
- Antes de multiempresa, agregar `company/tenant` a emisor, secuencias, documentos, eventos, facturas y notas,
  con constraints compuestos por tenant.
