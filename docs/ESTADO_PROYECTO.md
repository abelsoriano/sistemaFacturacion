# Estado del proyecto

## Estado actual

- **Actualizado:** 2026-10-03
- **Branch:** `fix/cert-expirado-y-xsd`
- **HEAD:** `dc069c7` (`dark mode: e-CF/DGII, Reportes (fallback), Equipo completados`)
- **Checkpoint de onboarding anterior:** `2bb8afb`; quedó superado por `d61f108` y `dc069c7`.
- **Objetivo:** mantener y completar el ERP de facturación dominicano, incluyendo los flujos comerciales multiempresa y la integración/certificación de e-CF con DGII.
- **Estado general:** el backend tiene cobertura funcional extensa para facturación, secuencias, notas E34, multiempresa y operaciones de certificación. La rama incluye hardening de la entrega de certificación y trabajo de UI en curso. No se puede afirmar que homologación DGII esté completada solo a partir del repositorio.
- **Árbol local:** existen modificaciones sin commit en dos documentos y cinco archivos frontend. No se atribuyen a `HEAD`; preservarlas al continuar.

## Completado recientemente y confirmado en el código

Los siguientes puntos existen en código, migraciones y/o pruebas. El estado “completado” aquí describe implementación en repositorio, no certificación externa ni despliegue productivo.

| Estado | Trabajo | Evidencia actual |
|---|---|---|
| Completado | Separación de estado fiscal y estado de procesamiento asíncrono, con eventos auditables | `ElectronicFiscalDocument.fiscal_status`, `job_status`, `ECFStatusEvent`; migración `0016`; pruebas de compatibilidad y transiciones en `facturacion/tests.py` |
| Completado | Secuencias transaccionales con alcance por empresa, incluidos números comerciales y códigos internos | `NumberSequence`, migraciones `0015`, `0032`–`0034`, servicio `facturacion/services/numbering.py`; pruebas de concurrencia y rollback |
| Completado | Multiempresa para miembros, documentos y configuración e-CF con restricciones/migraciones de datos | `Company`, `CompanyMembership`; migraciones `0020`–`0034`; filtros de empresa y pruebas de aislamiento en API/dashboard |
| Completado | Creación comercial centralizada; los endpoints y serializers de `Sale` heredado delegan al servicio de facturación | `facturacion/services/invoicing.py`, `api/views/sales_legacy.py`, serializers y `SaleLegacyAdapterTests` |
| Completado | Métricas comerciales del endpoint `/dashboard/` calculadas desde `Invoice`/`InvoiceDetail`, con permisos y respuesta JSON compatible | `facturacion/api/views/reports.py`; clase `DashboardInvoiceReportingTests` prueba origen Invoice, métricas y permisos |
| Completado | Flujos E34 con creación, restauración idempotente de inventario, reconciliación/compensación y trazabilidad | `services/credit_notes.py`, `services/credit_note_reconciliation.py`, migraciones `0017`–`0018`; `E34FiscalValidationTests` |
| Completado | E34 y reglas/documentos de certificación cubiertos por pruebas de contrato/validación existentes | `facturacion/tests.py`, `test_certification_*.py`, `management/commands/test_rfce_contract.py`; revisar estado de ejecución abajo |
| Completado en HEAD | Reconciliación de envíos de certificación DGII y seguridad frente a caídas al publicar | Migraciones `0054`–`0057`; `certification_submission.py`, `certification_reset.py`; pruebas de envío, migración crash y reset |

## En progreso

- **Tema oscuro en frontend (cambios locales, no incluidos en HEAD):** los diffs actuales adaptan los estilos de `DGIICertificationWizard`, formulario POS, formulario de factura y notificaciones/diálogos a variables `saas-*`. Hay además ediciones de texto con espacios finales en el wizard y ambos documentos. Aún no se han validado con build, tests de frontend ni revisión visual; no declararlo terminado.
- **Certificación/homologación DGII:** el código contiene flujos, fixtures XML, XSD y pruebas de certificación; el resultado de aceptación en el portal/ambiente DGII es **REQUIERE VERIFICACIÓN** externa.

## NEXT TASK

### Completar y validar los cambios locales de tema oscuro en pantallas de facturación/POS y wizard DGII

- **Objetivo:** cerrar de forma revisable el trabajo de tema oscuro que ya aparece en el árbol local, manteniendo los contratos y la lógica de facturación intactos.
- **Archivos/módulos afectados:** `facturacion_front/src/css/DGIICertificationWizard.css`, `facturacion_front/src/css/FastSalesForm.css`, `facturacion_front/src/css/facturaForm.css`, `facturacion_front/src/css/index.css` y, solo si la revisión lo requiere, `facturacion_front/src/components/DGIICertificationWizard.js`.
- **Qué ya existe:** tokens de tema oscuro y reglas CSS locales; el estado actual exacto se ve con `git diff` y `git status`.
- **Qué falta:** revisar el diff completo; eliminar cambios accidentales de presentación/texto (incluidos espacios finales si no son intencionales); comprobar que todos los controles, tablas, modales y notificaciones afectados contrasten correctamente en tema claro y oscuro; corregir solo defectos demostrados; ejecutar verificación frontend.
- **Criterio de terminado:** cambios locales revisados y sin regresiones visuales observables en pantallas afectadas; `npm run build` finaliza correctamente; tests frontend aplicables pasan (o se documenta con precisión que no existen/no son ejecutables); ningún cambio de lógica fiscal, API o datos forma parte de esta tarea.
- **Tests que deben ejecutarse:** desde `facturacion_front/`, `npm test -- --watchAll=false` y `npm run build`. En este entorno, antes de cerrar, comprobar también si las dependencias/scripts permiten ejecutarlos.

## Pendientes posteriores

1. Verificar estado real de homologación DGII con evidencia externa y documentar certificaciones aceptadas/rechazadas.
2. Revisar el flujo/ruta de “Venta rápida”: sigue existiendo `FastSalesForm` en `/Fastsales`; la afirmación de que se eliminó ese flujo es falsa en el estado actual.
3. Confirmar estado de producción, almacenamiento seguro de certificados, copias de seguridad, SLA y observabilidad. No hay evidencia suficiente en este snapshot para declararlos resueltos.
4. Mantener las pruebas de regresión de concurrencia y multiempresa al modificar secuencias, facturas, notas de crédito o permisos.

## Comprobación de los trabajos señalados como referencia

| Trabajo | Estado comprobado |
|---|---|
| Hardening previo a multiempresa | Completado en código, con pruebas de permisos/aislamiento; “previo” es histórico. Migraciones `0012` y `0020`–`0034`. |
| `NumberSequence` y operaciones transaccionales | Completado en código; servicio, restricciones/migraciones y pruebas de concurrencia presentes. |
| Cambios de código de producto | Completado en código: secuencia `product_internal_code` y tests de unicidad concurrente. |
| Separación `fiscal_status` / `job_status` | Completado en código y tests; migración `0016`. |
| `ECFStatusEvent` | Completado en modelo/migración y usado por transiciones. |
| Mejoras E34 | Parcial en sentido de certificación externa; implementación de creación, validación/reconciliación y pruebas está presente. Aceptación DGII: REQUIERE VERIFICACIÓN. |
| Reconciliación/restauración de inventario E34 | Completado en código con restauración idempotente y compensación/reconciliación probadas. |
| `Sale` delegando creación a `InvoiceCreationService` | Completado como adaptador compatible; rutas `/sales/` siguen existiendo. |
| Eliminación de “Venta rápida” | Pendiente/no realizado: `/Fastsales` y `FastSalesForm` siguen en `App.js`. |
| Nueva ruta de ventas | Completado parcialmente: `/sales` redirige a `/salesList`, `/Fastsales` aún está disponible; confirmar intención funcional antes de retirar rutas. |
| Dashboard `Sale/SaleDetail` → `Invoice/InvoiceDetail` conservando `/dashboard/` | Completado para las métricas comerciales; `reports.py` consulta `Invoice` y tests verifican la respuesta y permisos. Persisten referencias a `SaleDetail` en compatibilidad y reconciliación; eso no prueba que el dashboard dependa de ellas. |

## Problemas conocidos confirmados

- No se pudo ejecutar la prueba backend seleccionada: `.venv` usa Python 3.14.6 y no tiene Django instalado (`ModuleNotFoundError`). El `Dockerfile` fija Python 3.12 y `requirements.txt` fija Django 5.2.1; recrear el entorno local con Python 3.12 e instalar esas dependencias antes de ejecutar pruebas.
- Hay cambios locales sin commit en `CLAUDE.md`, este archivo y cuatro hojas de estilo más `DGIICertificationWizard.js` (siete rutas en total). Revisar y conservarlos; no asumir autoría o propósito más allá del diff presente.
- El repositorio contiene `facturacion/__pycache__/models.cpython-314.pyc` versionado y alterado en el commit HEAD. Es un artefacto generado confirmado por Git; no se ha cambiado durante esta actualización.

## Tests

- **Suites existentes:** `facturacion/tests.py` y módulos `facturacion/test_certification_*.py`; pruebas del comando RFCE en `facturacion/management/commands/test_rfce_contract.py`. Incluyen dashboard, adaptador Sale, Invoice, E34, secuencias concurrentes, multiempresa, certificados y ciclo de certificación.
- **Ejecutado durante esta actualización:** `.\.venv\Scripts\python.exe manage.py test facturacion.tests.DashboardInvoiceReportingTests`.
- **Resultado:** no iniciado; falló la carga del runner antes de descubrir tests porque Django no está instalado en `.venv` (`ModuleNotFoundError: No module named 'django'`). El venv fue creado con Python 3.14.6, mientras que el runtime declarado por Docker es Python 3.12.
- **No ejecutados:** resto de tests backend; `npm test -- --watchAll=false`; `npm run build`; pruebas visuales/manuales. No se afirma que pasen o fallen.
- **Estado previo de ejecución de tests:** REQUIERE VERIFICACIÓN; Git y los archivos prueban que existen, no que hayan pasado recientemente.

Para reproducir localmente, usar Python 3.12 (alineado con `Dockerfile`), crear un entorno virtual e instalar `requirements.txt`; luego volver a ejecutar el test indicado. No se recreó ni modificó `.venv` en esta actualización.

## Última actualización

2026-10-03. Auditoría basada en código, migraciones, pruebas, Git y diffs locales. No se modificó lógica de producto.

# HANDOFF PARA EL SIGUIENTE AGENTE

### ¿Dónde estamos?

HEAD es `dc069c7` en `fix/cert-expirado-y-xsd`. El backend tiene implementaciones y regresiones amplias para facturación, multiempresa, numeración, e-CF/E34 y el dashboard basado en Invoice. El árbol de trabajo tiene cambios locales, principalmente tema oscuro frontend, todavía no validados.

### ¿Qué acabamos de terminar?

La auditoría y actualización de `CLAUDE.md` y `docs/ESTADO_PROYECTO.md`. El dashboard Invoice y los demás hitos de referencia se marcaron según evidencia encontrada, no por el checkpoint viejo. La prueba de dashboard se intentó, pero no pudo arrancar por falta de Django en `.venv`.

### ¿Qué NO debemos volver a hacer?

- No rehacer la migración comercial del dashboard desde Sale a Invoice: el código y `DashboardInvoiceReportingTests` ya la cubren.
- No volver a implementar secuencias por empresa, adaptador de creación Invoice desde Sale ni restauración/reconciliación E34 sin que una regresión concreta lo requiera.
- No eliminar el flujo `/Fastsales` suponiendo que ya fue retirado; la ruta sigue presente y esa decisión necesita alcance funcional explícito.
- No descartar ni sobrescribir diffs locales sin inspeccionarlos.

### ¿Cuál es la próxima tarea?

Completar y validar el tema oscuro en los formularios de facturación/POS y wizard DGII, conforme a la sección **NEXT TASK**.

### ¿Qué archivos probablemente deben tocarse?

- `facturacion_front/src/css/DGIICertificationWizard.css`
- `facturacion_front/src/css/FastSalesForm.css`
- `facturacion_front/src/css/facturaForm.css`
- `facturacion_front/src/css/index.css`
- `facturacion_front/src/components/DGIICertificationWizard.js` (solo si la revisión del diff demuestra que hace falta)

### ¿Qué archivos NO tocar sin aprobación?

- `facturacion/ecf/signer/`, `facturacion/ecf/services/signing.py`
- `facturacion/ecf/soap/`, `facturacion/ecf/services/dgii_submission.py`
- `facturacion/ecf/schemas/`
- `facturacion/ecf/state_machine.py`, `facturacion/ecf/services/status_transitions.py`
- `facturacion/services/numbering.py`, modelos fiscales y migraciones
- Cualquier archivo de certificados, claves privadas o secretos

### ¿Cómo saber si la tarea quedó terminada?

Diff local revisado; pantallas afectadas legibles en ambos temas; `npm test -- --watchAll=false` y `npm run build` ejecutados correctamente o sus bloqueos documentados; sin cambios en lógica/API fiscal.

### Comando inicial recomendado

```bash
git status --short --branch
git log --oneline --decorate -30
git diff --stat
git diff -- CLAUDE.md docs/ESTADO_PROYECTO.md facturacion_front/src/components/DGIICertificationWizard.js facturacion_front/src/css/DGIICertificationWizard.css facturacion_front/src/css/FastSalesForm.css facturacion_front/src/css/facturaForm.css facturacion_front/src/css/index.css
cd facturacion_front
npm test -- --watchAll=false
npm run build
```
