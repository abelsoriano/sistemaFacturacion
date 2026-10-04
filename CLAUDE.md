# Sistema de facturación electrónica

ERP de facturación para República Dominicana. El estado de desarrollo cambia; consulta [docs/ESTADO_PROYECTO.md](docs/ESTADO_PROYECTO.md) antes de elegir trabajo.

## Arquitectura

- Backend: Django y Django REST Framework en `facturacion/`; configuración del proyecto en `setting/`.
- Persistencia: modelos Django y migraciones en `facturacion/models.py` y `facturacion/migrations/`.
- Frontend: React en `facturacion_front/src/`; las rutas principales están en `App.js`, las llamadas HTTP en `services/` y las pantallas/componentes en `components/` y `modules/`.
- Procesamiento fiscal asíncrono: Celery con Redis; tareas y colas e-CF viven en `facturacion/ecf/tasks/`, `facturacion/ecf/queues/` y `setting/celery.py`. Compose de referencia: `docker-compose.ecf.yml`.
- e-CF: generación y validación XML, firma XMLDSig, envío y consulta SOAP DGII, estados y reconciliación en `facturacion/ecf/`; configuración de negocio e integración en `facturacion/services/` y `facturacion/api/`.
- Los documentos comerciales usan `Invoice`/`InvoiceDetail`; `Sale`/`SaleDetail` se mantienen como compatibilidad heredada en algunos flujos.

## Convenciones

- Modelos y componentes React: `PascalCase`; funciones, variables, módulos Python y utilidades JS: `snake_case` (Python) o `camelCase` (JS); constantes: `UPPER_SNAKE_CASE`.
- Mantén la lógica de negocio en servicios y deja las vistas/controladores a cargo del contrato HTTP, permisos y validación de entrada.
- Usa serializers y APIs existentes antes de introducir contratos paralelos. Conserva los contratos JSON consumidos por el frontend.
- Las operaciones que asignan secuencias o mutan inventario/documentos deben respetar atomicidad, locks, idempotencia y ámbito de empresa ya establecidos.
- Cada cambio de modelo requiere migración Django revisada. No edites migraciones ya aplicadas como si fueran código descartable.

## Reglas críticas DGII y seguridad

Trata como código fiscal crítico y no lo modifiques sin autorización explícita del usuario y validación apropiada para homologación:

- `facturacion/ecf/signer/` y `facturacion/ecf/services/signing.py`: firma XMLDSig, canonicalización y manejo de certificados.
- `facturacion/ecf/soap/` y `facturacion/ecf/services/dgii_submission.py`: endpoints, namespaces, autenticación y contratos SOAP DGII.
- `facturacion/ecf/schemas/`: esquemas XSD oficiales. No los regeneres ni sustituyas por esquemas inferidos.
- `facturacion/ecf/state_machine.py`, `facturacion/ecf/services/status_transitions.py` y reconciliadores: estados y transiciones fiscales/técnicas.
- `facturacion/services/numbering.py`, modelos y migraciones de secuencias e-NCF: rangos, unicidad y asignación transaccional.
- Validadores y reglas fiscales (`facturacion/ecf/validators/`, `facturacion/services/fiscal_rules.py`), certificados y flujos E34 de notas de crédito.

No registres secretos, contraseñas, claves privadas ni contenido sensible de certificados. Las operaciones de reset, regeneración, refirma o reenvío de evidencia DGII deben respetar servicios, permisos, auditoría y controles de seguridad existentes; no las eludas con escrituras directas.

## Antes de modificar

1. Lee este archivo y `docs/ESTADO_PROYECTO.md`.
2. Ejecuta `git status --short --branch`, `git log --oneline --decorate -30` y revisa los diffs; conserva cambios locales ajenos a tu tarea.
3. Comprueba la implementación y las migraciones actuales antes de asumir que una función existe o falta.
4. Identifica tests existentes del flujo afectado. Para fiscal, numeración, estados, inventario o multiempresa, valida los casos de regresión relevantes antes de cerrar.
5. Para cambios a `models.py` o migraciones, presenta el diff propuesto y espera confirmación explícita antes de aplicarlos.
6. No cambies lógica fiscal crítica ni archivos XSD como parte de tareas de documentación o UI.

## CURRENT PROJECT STATE

El estado dinámico del proyecto está documentado en `docs/ESTADO_PROYECTO.md`.
Antes de comenzar una tarea:
1. leer `CLAUDE.md`
2. leer `docs/ESTADO_PROYECTO.md`
3. revisar `git status`
4. revisar últimos commits
5. validar la próxima tarea
