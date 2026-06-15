# Arquitectura asincronica e-CF

## Flujo recomendado

1. La API crea el `ElectronicFiscalDocument` y responde rapido.
2. `process-async` encola `generate_xml -> sign_xml -> submit_dgii`.
3. `submit_dgii` agenda `check_status` si DGII entrega `TrackID`.
4. Los errores temporales reintentan con exponential backoff.
5. Los errores permanentes quedan en `error` con auditoria y `last_error`.

## Colas

- `ecf.xml`: generacion y validacion XSD.
- `ecf.signing`: firma XMLDSig.
- `ecf.dgii`: envio DGII.
- `ecf.status`: consulta por TrackID.
- `ecf.retry`: reenvios operativos controlados.

## Idempotencia y bloqueo

- Cada task toma `select_for_update()` antes de decidir si debe trabajar.
- `submit_dgii` y `retry_submission` no envian si ya existe `track_id`.
- Los reenvios operativos se reservan para errores sin `TrackID`.
- Los estados terminales `accepted`, `rejected` y `cancelled` no se reprocesan.
- La auditoria queda en `ECFEventLog` con `task_id`, etapa, reintentos y error.

## Operacion

- Redis es broker y result backend.
- Flower queda preparado en `docker-compose.ecf.yml`.
- La API expone `async-monitor` para conteos por estado, intentos y ultimos errores.
