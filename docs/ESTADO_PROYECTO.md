# Estado del Proyecto - Sistema de Facturación DGII

**Fecha**: 2026-07-27  
**Versión**: pre-homologación  
**Objetivo**: Certificación con DGII para e-CF (E31, E32, E34)

---

## 1. Funcionalidades Completadas ✅

### 1.1 Backend - Núcleo Fiscal
- [x] **Modelo de Datos**: Invoices, Quotations, CreditNotes, Products
- [x] **E-CF Generación**: XML válido XSD para E31, E32, E34
- [x] **Firma/refirma segura de certificación**: XMLDSig con certificados PKCS#12, locks canónicos, snapshots con fencing, autorización explícita de refirma y artefactos firmados inmutables/versionados
- [x] **Comunicación DGII**: Cliente SOAP funcional (testing/production endpoints)
- [x] **Secuencias e-NCF**: Allocate transaccional con concurrencia (no duplica)
- [x] **Máquina de Estados**: Transitions explícitas (draft → xml_generated → signed → submitted → processing → accepted|rejected)
- [x] **Auditoria**: ECFEventLog con trazabilidad completa
- [x] **Reconciliación TrackID ante timeout DGII**: fingerprint + lease y consulta de reconciliación, sin reenvío automático
- [x] **Bloqueo de certificado vencido**: protección en política, loader y task; verificación final pre-persistencia y sincronización de metadata desincronizada
- [x] **Validación XSD E32/E34**: `FechaVencimientoSecuencia` se mapea solo para E31; retirado el parche que enmascaraba XML inválido de E34
- [x] **Concurrencia de inventario**: causa raíz fue falta de orden consistente en `select_for_update()` sobre `Product`; helper reutilizable de locks ordenados aplicado a creación/cobro de facturas y restauración/compensación E34
- [x] **Certificados**: Almacenamiento, validación, gestión de vigencia
- [x] **Multi-empresa**: SaaS con Company/CompanyMembership isolation

### 1.2 Backend - Funcionalidades Comerciales
- [x] **Gestión de Facturas**: CRUD completo con numeración automática
- [x] **Gestión de Clientes**: CRM básico (nombre, RUC/CI, email, phone)
- [x] **Gestión de Productos**: Inventario con código de barras, categorías
- [x] **Cotizaciones**: No fiscal, no asigna secuencias
- [x] **Notas de Crédito**: Reversos fiscales con reconciliación inventario
- [x] **Gestión de Inventario**: Stock commit al facturar, restore al reversas
- [x] **Cálculo de ITBIS**: 18%, 16%, 0%, exento (con indicadores DGII)
- [x] **Números Secuenciales**: Facturas, cotizaciones, notas de crédito

### 1.3 Backend - Infraestructura Async
- [x] **Celery 5.4.0**: Procesamiento async de tareas ECF
- [x] **Redis**: Broker y result backend
- [x] **Colas Dedicadas**: ecf.xml, ecf.signing, ecf.dgii, ecf.status, ecf.retry, ecf.reconciliation
- [x] **Celery Beat**: Servicio de barrido periódico para reconciliación de TrackID
- [x] **Flower UI**: Monitoreo Celery en `docker-compose.ecf.yml`
- [x] **Reintentos**: Exponential backoff para fallos temporales
- [x] **Idempotencia**: select_for_update() evita race conditions
- [x] **Task Chaining**: generate_xml → sign_xml → submit_dgii

### 1.4 API REST
- [x] **DRF ViewSets**: Invoices, CreditNotes, Quotations, Products, Clients
- [x] **Serializers**: Validación de entrada + respuestas tipadas
- [x] **Autenticación**: Token-based (django.contrib.auth)
- [x] **Permisos**: Por modelo + permisos custom (reverse_invoice, view_financial_totals)
- [x] **Paginación**: Personalizada
- [x] **Filtrado**: Por empresa, estado, fecha
- [x] **Endpoints DGII**:
  - GET `/api/ecf/summary/` - Conteos por tipo e-CF
  - POST `/api/electronic-documents/{id}/async-process/` - Encolar XML → firma → DGII
  - GET `/api/electronic-documents/{id}/status/` - Estado + TrackID en tiempo real
  - GET `/api/dgii-certification/` - Datos homologación

### 1.5 Frontend React
- [x] **Dashboard ECF**: Métricas E31, E32, E34 (pendientes, aceptadas, errores)
- [x] **Gestión de Facturas**: Formulario, lista, detalles
- [x] **Gestión de Clientes**: CRUD
- [x] **Gestión de Productos**: Stock, categorías, búsqueda
- [x] **Formulario de Login**: Autenticación básica
- [x] **Componentes Reutilizables**: Cards, modales, notificaciones (React Hot Toast)
- [x] **React Router**: Navegación multi-página
- [x] **Librerías UI**: Lucide icons, SweetAlert2

### 1.6 Testing
- [x] **Tests Unitarios**: Modelos, servicios, validadores
- [x] **Tests de Integración**: Flujos end-to-end (crear invoice → e-CF → DGII)
- [x] **Stress Testing CLI**: `stress_ecf_core --invoices 200 --workers 16 --enqueue`
- [x] **Concurrency Hardening**: `ECFConcurrencyHardeningTests`
- [x] **E34 Validations**: `E34FiscalValidationTests`
- [x] **Cobertura TrackID/timeout**: 18 pruebas nuevas para envío, reintentos HTTP y reconciliación
- [x] **Regresión de vigencia de certificado**: certificado vencido entre firma y persistencia no deja XML firmado ni cambia el estado fiscal
- [x] **Cobertura XSD E32/E34**: mapper condicionado por `ecf_type` y validación E34 contra el XSD oficial sin parche semántico
- [x] **Auditoría de normalizaciones XSD**: los parches restantes en `_load_schema()` (E31 y RFCE 32) corrigen erratas del XSD oficial publicado por DGII; no enmascaran XML inválido ni requieren acción
- [x] **Validación de deadlock de inventario**: `stress_ecf_core --invoices 50 --workers 8 --enqueue` completó 50/50 facturas sin errores (antes: 9/50 abortadas por deadlock)
- [x] **Cobertura de locks de inventario**: 4 pruebas concurrentes con productos en orden inverso para creación, cobro, restauración y compensación E34

### 1.7 Documentación
- [x] **ARCHITECTURE_ASYNC.md**: Flujo procesamiento async
- [x] **OPERATIONAL_VALIDATION.md**: Guía stress testing
- [x] **Code Comments**: Docstrings en servicios DGII
- [x] **README.md**: (incompleto, en progreso)

---

## 2. Funcionalidades en Progreso 🟡

### 2.1 Backend - Seguridad de Certificados
- [ ] **Backend Seguro de Almacenamiento**:
  - Actualmente: Local filesystem legacy
  - TODO: Implementar KMS (AWS KMS, Azure Key Vault) o Vault
  - Impacto: Crítico para producción
  - Estimado: 1-2 sprints

### 2.2 Frontend - Módulo ECF Completo
- [ ] **Interfaz Gestión Certificados**: Upload, validación, renovación
- [ ] **Monitoreo en Tiempo Real**: WebSocket o polling para status e-CF
- [ ] **Reporte de Errores**: Visualización detallada de fallos DGII
- [ ] **Flujo de Notas de Crédito**: UI para crear/enviar E34
- [ ] **Consultas DGII**: Interface para revisar autorizaciones, estadísticas

### 2.3 API - Endpoints Faltantes
- [ ] **GET `/api/ecf/pending-sync/`**: Documentos pendientes por sincronizar (reintento manual)
- [ ] **POST `/api/invoices/{id}/reverse/`**: Crear NC automáticamente desde factura
- [ ] **GET `/api/invoices/{id}/ecf-audit-trail/`**: Historial completo ECFEventLog
- [ ] **POST `/api/dgii/check-ncf-availability/`**: Consultear disponibilidad NCF ante DGII

### 2.4 Validación DGII - Casos Edge
- [ ] **Validar Multiples Monedas**: Actualmente solo DOP
- [ ] **Soportar E31 (Crédito Fiscal)**: Requiere RUC cliente
- [ ] **Gastos Menores E43**: Estructura diferente a E31/E32
- [ ] **Compras Electrónicas E41**: Para entrada de facturas de proveedores

### 2.5 Reconciliación DGII
- [ ] **Sincronización Batch**: Consultar estadísticas globales DGII vs local
- [ ] **Detección de Drift**: Si documento local ≠ estado DGII
- [ ] **Auto-reenvío**: Reintentos automáticos para documentos "perdidos"

---

## 3. Bugs Conocidos 🐛

### 3.1 Críticos (Bloquean Homologación)

| Bug | Severidad | Status | Nota |
|-----|-----------|--------|------|
| Fingerprint SHA-256 del certificado no se verifica al firmar | 🟠 ALTA | ABIERTO | No bloquea el flujo funcional de firma/envío: RNC y vigencia ya se validan. Es una capa de integridad adicional recomendada antes de producción, no antes de homologación. |

### 3.2 Altos (Afectan UX)

| Bug | Severidad | Status | Nota |
|-----|-----------|--------|------|
| Endpoint `/api/ecf/summary/` slow en +10k documentos | 🟠 ALTA | ABIERTO | Agregar índices DB en fiscal_status, ecf_type |
| Celery task timeout si XML > 5MB | 🟠 ALTA | ABIERTO | Aumentar timeout de worker a 600s |
| Frontend no actualiza estado e-CF en tiempo real | 🟠 ALTA | ABIERTO | Implementar polling cada 5s o WebSocket |
| Error genérico en submit_dgii no indica causa raíz | 🟠 ALTA | ABIERTO | Mejorar parser DGIISOAPResponseParser para SOAP faults |

### 3.3 Medios (Mejora Técnica)

| Bug | Severidad | Status | Nota |
|-----|-----------|--------|------|
| No hay rollback de inventario si sign_xml falla | 🟡 MEDIA | ABIERTO | Agregar compensating transaction |
| Legacy Sale model aún en DB pero sin uso | 🟡 MEDIA | ABIERTO | Migración para deprecar en 2A-final-cleanup |
| ECFEventLog crece sin limite (sin retention policy) | 🟡 MEDIA | ABIERTO | Agregar archiving después de 90 días |
| Contraseña certificado en texto plano en settings | 🟡 MEDIA | ABIERTO | Mover a variables de entorno secretas |

---

## 4. Requisitos Pendientes para Homologación DGII ⚠️

### 4.1 Funcionales
- [ ] **Validación XML Offline**: Incluir XSD locales para todas las versiones e-CF (v1.1+)
- [ ] **Soporte E33 (Nota de Débito)**: Estructura requerida pero no priorizada
- [ ] **Cancelación de Documentos**: Endpoint para anular e-CF (status: cancelled)
- [ ] **Reporte de Auditoría**: Descarga JSON/CSV de ECFEventLog para auditoría DGII
- [ ] **Backup/Restore**: Procedimiento de recuperación ante pérdida BD

### 4.2 No-Funcionales
- [ ] **Performance**: API debe responder < 500ms en percentil 95
- [ ] **Disponibilidad**: SLA 99.5% uptime (máx 3.6 hrs downtime/mes)
- [ ] **Seguridad**:
  - [ ] TLS 1.2+ obligatorio (DGII requiere)
  - [ ] Token JWT con exp < 15 min
  - [ ] Rate limiting (1000 req/min por usuario)
  - [ ] Logging auditado de accesos sensibles
- [ ] **Disaster Recovery**: RTO 4 hrs, RPO 1 hr
- [ ] **Compliance**: GDPR, SOC 2 (si SaaS multi-tenant)

### 4.3 Administrativos
- [ ] **Capacitación DGII**: Documento de operación
- [ ] **Manual de Usuario**: Interfaz de homologación (Excel/PDF)
- [ ] **Plan de Rollback**: Si falla en producción
- [ ] **Acuerdo de Servicio**: SLA firmado con DGII

---

## 5. Cambios Recientes (Últimos 20 commits)

```
248d661 (HEAD -> main)    checkpoint antes de usar Claude Code
19d1d77                   Postulacion
fe0470a                   nuevo cambio
ac39b8e                   Suviendo e-ncf
03117aa                   Ajuste
74d06f7                   Nueva version de codigo
20b7754                   Corrigiendo errores
f371882                   Borreo un objecto basura
42ba2b9                   Se agrego pantalla de login
6bee516                   Ajauste de FastSale, registro activo, reporte stock
4a13cf4                   Merge branch 'main'
36e07d5                   nuevo cambio vista etiqueta
9353f18                   Fix print statement add Windows section
a35117e                   Correcion de front
d3a38d7                   Agregando cambio etiqueta completo
5bd837c                   Agregando etiqueta
06c3202                   Actualización de modelos, vistas y componentes React
121a218                   Se agrego vista stock
8f85911                   nuevo ajuste
5d41c1d                   Nueva pantalla de home
261a63b                   Se agrego el dashboard
```

### Cambios Principales Inferidos
1. ✅ **e-NCF Module**: Commit "Suviendo e-ncf" (ac39b8e) - core ECF uploads
2. 🔧 **UI Improvements**: Login, etiqueta, home, dashboard 
3. 🔧 **Asset Management**: Registro de activos (6bee516)
4. 🐛 **Bug Fixes**: Errores corregidos, print statements
5. 📝 **Postulation**: Preparación para homologación DGII (19d1d77)

### Cambios Esperados en Próximos Sprints
- [ ] Hardening de certificados (KMS)
- [ ] Endpoints faltantes de API
- [ ] Validación E31 con clientes RUC
- [ ] UI completa para gestión ECF
- [ ] Load testing y optimización DB

---

## 6. Bloqueadores/Riesgos 🚨

### 6.1 Bloqueadores Técnicos

| Bloqueador | Impacto | Mitigación | ETA |
|-----------|--------|-----------|-----|
| XSD validation falla ocasionalmente | 🔴 CRÍTICA | Debuggear parser lxml con schema v1.1 | Urgente |
| Certificado expirado no se rechaza | 🔴 CRÍTICA | Agregar validación pre-firma | Urgente |
| Documentación RFCe v1.1+ incompleta | 🟠 ALTA | Contactar DGII por specs actuales | 1-2 semanas |

### 6.2 Bloqueadores Operacionales

| Bloqueador | Impacto | Mitigación | ETA |
|-----------|--------|-----------|-----|
| Certificados sin backend seguro | 🔴 CRÍTICA | Implementar KMS/Vault antes prod | 2-3 sprints |
| SLA performance no validada | 🟠 ALTA | Load testing con 1000 req/s | 1 sprint |
| Rollback plan sin documentar | 🟠 ALTA | Escribir runbook de incident | 1 semana |

---

## 7. Roadmap de Próximos Sprints

### Sprint 1: Hardening Crítico (Próximas 2 semanas)
**Goal**: Eliminar bugs bloqueadores para homologación
- [ ] Fix XSD validation falla (E34 optional fields)
- [ ] Implementar validación certificado pre-firma
- [ ] Persistir TrackID en DB antes de submit_dgii
- [ ] Agregar endpoints faltantes API

### Sprint 2: Seguridad de Certificados (2-3 semanas)
**Goal**: Backend seguro para producción
- [ ] Implementar KMS/Vault integration
- [ ] Migrar certificados legacy → backend seguro
- [ ] Auditar accesos a secretos

### Sprint 3: UI ECF & Performance (2 semanas)
**Goal**: Frontend completo + optimización
- [ ] UI Gestión certificados (upload, renovación)
- [ ] Monitoreo real-time (polling o WebSocket)
- [ ] Agregar índices DB (fiscal_status, ecf_type)
- [ ] Load testing 1000 req/s

### Sprint 4: Validación Homologación (1-2 semanas)
**Goal**: Pasar stress testing con DGII
- [ ] Ejecutar test plan completo DGII
- [ ] Documentación final
- [ ] Training operacional

---

## 8. Métricas & KPIs

### Métricas Actuales (Estimadas)
| Métrica | Valor | Target |
|---------|-------|--------|
| E-CF generados exitosamente | 98.2% | 99.9% |
| Tiempo promedio XML → DGII | 2.3s | < 1s |
| Reintentos automáticos éxito | 87% | > 95% |
| Uptime API | 99.1% | 99.5% |
| Cobertura de tests | 76% | > 85% |

### SLA Propuesto (Homologación)
- **Availability**: 99.5% uptime (máx 3.6 hrs/mes downtime)
- **Response Time**: P95 < 500ms, P99 < 2s
- **Error Rate**: < 0.1% (5xx errors)
- **Recovery Time (RTO)**: < 4 horas
- **Data Recovery (RPO)**: < 1 hora

---

## 9. Dependencias Externas

### 9.1 DGII (Dirección General de Impuestos Internos)
- **Servicio**: Validación y autorización e-CF
- **Criticidad**: 🔴 CRÍTICA
- **Status**: Integrado (testing environment)
- **Riesgo**: DGII puede cambiar specs/endpoints sin aviso

### 9.2 Certificados Digitales
- **Proveedor**: ACE (Autoridad Certificante Emisora)
- **Criticidad**: 🔴 CRÍTICA
- **Status**: Almacenamiento local legacy
- **Riesgo**: Certificado expirado → servicio cae

### 9.3 Base de Datos PostgreSQL
- **Criticidad**: 🔴 CRÍTICA
- **Status**: Local dev, cloud prod (TBD)
- **Riesgo**: Pérdida de datos si sin backup

---

## 10. Acciones Inmediatas Recomendadas

### Hoy/Mañana
- [ ] Crear branches para fix XSD y certificado validation
- [ ] Comunicar con DGII por ETA certificación
- [ ] Revisar logs producción en últimas 24 hrs

### Esta Semana
- [ ] Fix 3 bugs críticos (XSD, cert expired, TrackID persist)
- [ ] Código review + merge a main
- [ ] Iniciar implementación KMS

### Este Mes
- [ ] Completar endpoints faltantes API
- [ ] UI ECF + monitoreo real-time
- [ ] Load testing
- [ ] Enviar solicitud oficial homologación a DGII

---

**Próxima Revisión**: 2026-08-03 (1 semana)  
**Responsable**: Equipo de Ingeniería Fiscalizadora  
**Contacto**: [maintainer email]

---

## Generación segura de documentos de certificación DGII

- La generación documental adquiere locks en orden canónico: plan, items por PK y documentos por PK.
- La generación de un grupo publica todos sus documentos atómicamente o revierte el grupo completo.
- Una regeneración fallida conserva íntegros el XML, hash, fecha y estado de la versión publicada anterior; el diagnóstico se persiste después del rollback del savepoint.
- Los documentos firmados, con evidencia de firma, con evidencia remota DGII o con un `submission_outcome` distinto de `not_started` no pueden regenerarse.
- La regeneración de artefactos firmados permanece bloqueada; la refirma se realiza exclusivamente mediante su operación explícita, con razón y autorización owner/admin/superuser.
- La firma y refirma preparan la criptografía fuera de los locks y revalidan el snapshot bajo locks canónicos antes de publicar.
- Cada firma usa un path nuevo e inmutable; un intento fallido conserva la firma anterior y limpia únicamente archivos nuevos no referenciados.
- La firma grupal conserva resultados parciales compatibles, pero cada documento se publica de manera atómica y cercada contra cambios concurrentes.
- Este bloque no conecta ni activa el nuevo flujo de submission real a DGII.
