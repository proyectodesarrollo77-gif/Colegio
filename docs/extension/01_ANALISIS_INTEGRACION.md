# Entregable 1 — Análisis de Integración

**Módulos:** Gestión de Incapacidades · Convivencia Escolar
**Sistema:** PL_SGE — Plataforma Web Integral de Gestión Académica Institucional
**Enfoque:** extensión nativa. No se construye un sistema nuevo.

---

## 0. Hallazgo principal del análisis

> **Buena parte de lo solicitado ya existe en el sistema.** El análisis del
> código en producción muestra que el módulo `core/observer` ya implementa el
> núcleo de Convivencia Escolar, y que `teacher_absence` ya registra
> incapacidades docentes.

Diseñar los dos módulos como aplicaciones nuevas e independientes **violaría
las condiciones 4 y 5** que usted mismo fijó (no duplicar información, no crear
entidades que ya existan), y produciría dos historiales disciplinarios
paralelos en la misma base de datos.

La propuesta de este documento es, en consecuencia:

| Módulo | Estrategia | Justificación |
|---|---|---|
| **Convivencia Escolar** | **Extender** `core/observer` | El 60 % del alcance ya está implementado y en uso |
| **Incapacidades** | **Módulo nuevo** `core/incapacities` que **se integra con** `teacher_absence` y `attendance_record` | No existe una entidad transversal de incapacidad, pero sí los puntos de integración |

---

## 1. Arquitectura existente analizada

### 1.1 Capas

| Capa | Pieza | Ubicación |
|---|---|---|
| Backend | Django 5.2.17 + DRF 3.18.0 | `config/settings.py` |
| Autenticación | Sesión + JWT (SimpleJWT) + TOTP RFC 6238 | `core/authentication/` |
| Autorización | Motor por **módulo × acción** con caché | `config/permissions.py` |
| API | `BaseModelViewSet` / `ReadOnlyBaseViewSet` | `config/viewsets.py` |
| Páginas CRUD | `ResourceView` declarativa → JSON → `crud.js` | `config/resource.py` |
| Modelos base | `BaseModel`, `CatalogModel` (auditoría + borrado lógico + UUID) | `config/models_base.py` |
| Navegación | `MODULE_REGISTRY` + `DEFAULT_ROLE_MATRIX` | `core/configuration/modules.py` |
| Frontend | HTML5 + CSS3 con tokens + JavaScript ES6 nativo, **sin frameworks** | `static/` |
| Gráficas | SVG propias, **sin librerías externas** | `static/js/modules/charts.js` |
| Auditoría | `AuditLog` + middleware | `core/audit/` |
| Notificaciones | `Notification.push()` | `core/notifications/models.py` |
| Exportación | `ExportMixin` → XLSX / CSV | `config/viewsets.py` |

### 1.2 Base de datos

- PostgreSQL 14+, **157 tablas**, 1.593 índices, 785 llaves foráneas.
- Toda tabla de dominio comparte: `id`, `created_at`, `updated_at`,
  `deleted_at`, `deleted_by_id`, `created_by_id`, `updated_by_id`, `uuid`,
  `is_active`.
- **El borrado es lógico** en todo el sistema (`deleted_at`), nunca físico.

### 1.3 Convención de nomenclatura observada

| Elemento | Convención |
|---|---|
| App Django | inglés, plural: `students`, `teachers`, `observer` |
| Tabla | prefijo del dominio: `student`, `student_document`, `observer_entry` |
| Módulo de permisos | `dominio.submodulo`: `observer.records` |
| Ruta HTML | español: `/observador/`, `/asistencia/` |
| Ruta API | inglés, kebab-case plural: `/api/observer-entries/` |
| Estados | mayúsculas con guion bajo: `EN_SEGUIMIENTO` |

Los módulos nuevos respetan esta convención sin excepción.

---

## 2. Inventario de solapamiento

### 2.1 Convivencia Escolar vs. `core/observer` (existente)

| Funcionalidad solicitada | ¿Ya existe? | Dónde |
|---|---|---|
| Crear caso disciplinario | **Sí** | `observer_entry` |
| Registrar novedad | **Sí** | `observer_entry` |
| Clasificar faltas (LEVE/GRAVE/MUY_GRAVE) | **Sí** | `observer_category.severity` = `TIPO_I` / `TIPO_II` / `TIPO_III` |
| Registrar seguimiento | **Sí** | `observer_follow_up` |
| Reconocimientos positivos | **Sí** | `observer_category.severity` = `POSITIVA` |
| Consultar historial disciplinario | **Sí** | `observer:history` |
| Reportes y exportación PDF/Excel | **Sí** | `ExportMixin` + plantillas de impresión |
| Integración con auditoría | **Sí** | `AuditLog` automático |
| Adjuntar evidencias | **Parcial** | `observer_entry.attachment` — **un solo archivo** |
| Registrar compromisos | **Parcial** | `observer_entry.commitments` — **texto libre, sin seguimiento** |
| Programar citaciones | **No** | Existe la bandera `requires_guardian`, no la citación |
| Escalar a comité | **No** | — |
| Registrar actas | **No** | — |
| Registrar decisiones | **No** | — |
| Alertas tempranas | **No** | — |

**Estados solicitados vs. existentes:**

| Solicitado | Existente | Acción |
|---|---|---|
| `ABIERTO` | `ABIERTA` | Ya existe |
| `EN_SEGUIMIENTO` | `EN_SEGUIMIENTO` | Ya existe |
| `CERRADO` | `CERRADA` | Ya existe |
| `ESCALADO_COMITE` | — | **Agregar** |
| — | `ANULADA` | Conservar (borrado lógico con trazabilidad) |

> **Nota terminológica:** el sistema usa `TIPO_I` / `TIPO_II` / `TIPO_III`, que
> es la tipificación de la **Ley 1620 de 2013 y su Decreto 1965 de 2013**
> (Sistema Nacional de Convivencia Escolar). Es más precisa que
> LEVE/GRAVE/MUY_GRAVE y ya está en producción. **Se conserva**, y la interfaz
> muestra la equivalencia: Tipo I = Leve, Tipo II = Grave, Tipo III = Muy grave.

**Conclusión:** Convivencia Escolar **no es un módulo nuevo**: es la maduración
del observador existente. Se agregan 9 tablas que cuelgan de `observer_entry` y
**no se toca ninguna columna en producción**.

### 2.2 Incapacidades vs. entidades existentes

| Funcionalidad solicitada | ¿Ya existe? | Dónde |
|---|---|---|
| Incapacidad de docente | **Parcial** | `teacher_absence.kind = 'INCAPACIDAD'` |
| Aprobación | **Parcial** | `teacher_absence.approved` — **booleano, sin estados** |
| Justificación de ausencias | **Sí, el punto de integración** | `attendance_record.status = 'EXCUSA'` + `excuse_document` |
| Conteo de justificadas | **Sí** | `attendance_summary.justified` |
| Documento médico en expediente | **Sí** | `student_document.kind = 'CERTIFICADO_MEDICO'` |
| Notificación a docentes y acudientes | **Sí** | `Notification.push()` |
| Auditoría | **Sí** | `AuditLog` |
| Incapacidad de estudiante | **No** | — |
| Incapacidad de administrativo | **No** | — |
| Estados PENDIENTE…ANULADA | **No** | — |
| Soportes múltiples | **No** | — |
| Historial de cambios de estado | **No** | — |

**Brecha estructural detectada:** el sistema modela **`Student`**, **`Teacher`**
y **`Guardian`**, pero **no tiene una entidad de personal administrativo**. La
única representación de un administrativo es su `users_user`.

**Decisión de diseño:** la incapacidad usa un **sujeto polimórfico ligero** —
`subject_type` + tres llaves foráneas anulables (`student_id`, `teacher_id`,
`user_id`) con un `CHECK` que garantiza exactamente una. Esto:

- reutiliza las tres entidades existentes sin duplicarlas;
- **evita crear una entidad `Empleado`** que competiría con `Teacher` y
  fragmentaría la nómina;
- mantiene integridad referencial real (FK, no un campo `objeto_id` genérico).

**Decisión sobre `teacher_absence`:** no se duplica. Cuando una incapacidad de
docente se **aprueba**, el sistema **crea o vincula** el registro de
`teacher_absence` correspondiente, de modo que la asignación de suplentes y la
carga académica siguen funcionando exactamente como hoy.

---

## 3. Reutilización identificada

### 3.1 Entidades reutilizadas (cero duplicación)

| Entidad exigida | Tabla existente | Uso en los módulos nuevos |
|---|---|---|
| usuarios | `users_user` | Autor, aprobador, sujeto administrativo |
| roles | `users_role` | Los 14 perfiles actuales + 4 nuevos |
| permisos | `users_role_permission`, `users_user_module_permission` | Matriz módulo × acción |
| estudiantes | `student` | Sujeto de incapacidad y de caso |
| docentes | `teacher` | Sujeto de incapacidad, reportante |
| acudientes | `student_guardian`, `student_guardian_link` | Destinatario de citaciones y notificaciones |
| matrículas | `student_enrollment` | Contexto del caso y de la incapacidad |
| grados / cursos / grupos | `academic_grade`, `academic_subject`, `academic_group` | Filtros y reportes |
| periodos académicos | `academic_period` | Corte de reportes e indicadores |
| asistencia | `attendance_record`, `attendance_summary` | **Justificación automática** |
| calificaciones | `subject_grade` | Consulta para alerta temprana |
| expedientes | `student_document` | Registro del soporte médico |
| notificaciones | `notification` | Avisos a docentes y acudientes |
| archivos / documentos | `FileField` + `config/imports.validate_document_upload` | Soportes y evidencias |
| auditoría / logs | `audit_log` | Trazabilidad automática |
| sedes | `institution_campus` | Alcance por sede |
| configuración | `configuration_parameter` | Parámetros de alertas y plazos |

### 3.2 Componentes reutilizados (cero componente nuevo)

| Componente | Reutilización |
|---|---|
| `BaseModel` / `CatalogModel` | Todas las tablas nuevas |
| `BaseModelViewSet` | Todos los ViewSets: auditoría, borrado lógico, exportación, `options/`, `stats/` |
| `ExportMixin` | Exportación XLSX/CSV sin escribir código |
| `ResourceView` + `crud.js` | Todas las pantallas de listado y formulario |
| `templates/layouts/dashboard.html` | Mismo layout, menú y encabezado |
| `partials/print_header.html`, `print_toolbar.html` | Actas y constancias imprimibles |
| `charts.js` | Gráficas de los tableros |
| `Notification.push()` | Todas las notificaciones |
| `config/imports.py` | Importación masiva y validación de archivos |
| `variables.css` | **Mismos colores y tema**: cero color nuevo |

### 3.3 Servicios reutilizados

| Servicio | Uso |
|---|---|
| `config.permissions.user_has_permission` | Validación en backend |
| `config.permissions.HasModulePermission` | Autorización DRF |
| `config.permissions.ModulePermissionRequiredMixin` | Autorización de páginas |
| `core.audit.services.register_audit` | Registro explícito de acciones de negocio |
| `Notification.push` | Notificaciones |
| `config.imports.validate_document_upload` | Extensión, tipo y tamaño de adjuntos |

---

## 4. Cambios mínimos requeridos sobre el sistema en producción

Son **seis**, todos aditivos. **Ninguno altera una columna existente ni rompe
compatibilidad.**

| # | Cambio | Tipo | Riesgo | DDL |
|---|---|---|---|---|
| 1 | Registrar `core.incapacities` en `LOCAL_APPS` | Configuración | Nulo | No |
| 2 | Agregar el árbol de módulos al `MODULE_REGISTRY` | Configuración | Nulo | No |
| 3 | Agregar 4 perfiles al `DEFAULT_ROLE_MATRIX` y a `seed_roles` | Configuración | Nulo | No |
| 4 | Incluir las rutas en `config/urls.py` y `config/api.py` | Enrutamiento | Nulo | No |
| 5 | Agregar `ESCALADO_COMITE` a `ObserverEntry.STATUS_CHOICES` | Modelo | **Bajo** | **No** — `choices` es validación de Django, no restricción de PostgreSQL |
| 6 | Crear 14 tablas nuevas | Migración | Bajo | Sí, solo `CREATE TABLE` |

> **El cambio 5 no genera DDL.** `status` es `character varying(16)` sin
> `CHECK`; agregar un valor a `choices` produce una migración `AlterField`
> que PostgreSQL resuelve sin reescribir la tabla. El valor nuevo cabe en 16
> caracteres (`ESCALADO_COMITE` = 15).

**No se ejecuta ningún `ALTER TABLE ... DROP`, `RENAME` ni cambio de tipo.**

---

## 5. Impacto en la arquitectura

| Dimensión | Impacto | Detalle |
|---|---|---|
| Arquitectura principal | **Ninguno** | Se usan las mismas capas y clases base |
| Experiencia de usuario | **Aditivo** | Dos grupos nuevos en el menú lateral; ninguna pantalla actual cambia |
| Componentes | **Ninguno reemplazado** | Solo consumo de los existentes |
| Base de datos | **Aditivo** | 14 tablas nuevas; cero columnas modificadas |
| Integridad referencial | **Reforzada** | 41 llaves foráneas nuevas hacia tablas existentes |
| Rendimiento | **Bajo** | 38 índices nuevos; las consultas actuales no cambian de plan |
| Auditoría | **Ampliada** | Las operaciones nuevas se registran con el mecanismo actual |
| Roles | **Ampliado** | 4 perfiles nuevos; los 14 actuales no cambian |
| Actualizaciones futuras | **Compatible** | Sin monkey-patching ni herencia de modelos de terceros |
| Responsive | **Heredado** | Se usa `responsive.css` sin modificarlo |

---

## 6. Dependencias

### 6.1 Dependencias técnicas

**No se agrega ninguna librería.** Todo se resuelve con lo que ya está en
`requirements.txt`: Django, DRF, `openpyxl` (Excel), `xhtml2pdf`/`reportlab`
(PDF), `pillow` (imágenes).

### 6.2 Dependencias entre módulos

```
incapacities ──► students, teachers, users        (sujeto)
             ──► attendance                        (justificación automática)
             ──► academic                          (año lectivo, periodo)
             ──► notifications, audit              (avisos y trazabilidad)

observer(+)  ──► students, academic                (ya existentes)
             ──► users                             (comité, citaciones)
             ──► notifications, audit
             ──► attendance, evaluations           (solo lectura: alerta temprana)
```

**No hay dependencia circular.** Incapacidades depende de Asistencia; el
observador extendido **lee** Asistencia y Evaluaciones pero no las modifica.

### 6.3 Dependencia de orden en el despliegue

`incapacities` requiere que `students`, `teachers`, `attendance` y `academic`
estén migrados — se cumple siempre, porque son módulos productivos.

---

## 7. Riesgos y mitigación

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **Historial disciplinario duplicado** si Convivencia se implementa como módulo aparte | Alta | **Crítico** | Extender `observer`. Es la decisión central de este diseño |
| R2 | La justificación automática sobrescribe asistencia ya digitada por el docente | Media | Alto | Solo se modifican registros `AUSENTE`; nunca `PRESENTE`, `TARDE` ni `EXCUSA` previa. Cada cambio queda en `incapacity_attendance_link` y es reversible al anular |
| R3 | Anular una incapacidad aprobada deja asistencia justificada sin soporte | Media | Alto | La anulación **revierte** los registros mediante el vínculo, y exige motivo |
| R4 | Fuga de datos de salud (dato sensible, Ley 1581 de 2012) | Media | **Crítico** | Diagnóstico y CIE-10 solo visibles con permiso `view` sobre `incapacities.confidencial`; los demás perfiles ven fechas y estado. Descarga de soportes auditada |
| R5 | Doble registro de la incapacidad docente en `teacher_absence` | Media | Medio | Vínculo 1:1 `incapacity.teacher_absence_id`; al aprobar se crea o se reutiliza, nunca se duplica |
| R6 | Alertas tempranas con exceso de falsos positivos | Alta | Medio | Umbrales **parametrizables** en `observer_alert_rule`, no fijos en código |
| R7 | Crecimiento de la tabla de evidencias | Baja | Medio | Límite de 10 MB por archivo, validación de extensión, índice por caso |
| R8 | Conflicto con futuras actualizaciones del sistema | Baja | Alto | Cero modificación de tablas productivas; extensión por composición, no por herencia |
| R9 | Fechas solapadas de incapacidad para el mismo sujeto | Media | Medio | Regla RN-I-03 y validación en `services.py`; índice funcional para detección |
| R10 | Escalamiento al comité sin quórum válido | Baja | Medio | El acta exige registrar asistentes y valida quórum antes de permitir la decisión |

---

## 8. Consideraciones técnicas

### 8.1 Datos sensibles de salud

El diagnóstico médico es **dato sensible** bajo la Ley 1581 de 2012. Diseño
adoptado:

- Submódulo de permisos propio: `incapacities.confidencial`.
- Los serializers **omiten** `diagnosis` y `cie10_code` cuando el usuario no
  tiene ese permiso — filtrado en el **backend**, no ocultamiento en pantalla.
- La descarga de cada soporte médico se registra en `audit_log`.
- Retención y anonimización configurables por parámetro del sistema.

### 8.2 Transaccionalidad

La aprobación de una incapacidad es una operación compuesta (cambiar estado +
justificar asistencia + crear novedad docente + notificar + auditar). Se
ejecuta dentro de `@transaction.atomic`: **o se aplica completa, o no se aplica**.

### 8.3 Idempotencia

Aprobar dos veces la misma incapacidad no duplica justificaciones: el vínculo
`incapacity_attendance_link` tiene `UNIQUE (incapacity_id, attendance_record_id)`.

### 8.4 Zona horaria y cálculo de días

Se usa `timezone.localdate()` con `America/Bogota`, igual que el resto del
sistema. Los días de incapacidad se cuentan **calendario**, y los hábiles se
derivan del `institutional_calendar` existente.

### 8.5 Rendimiento

- Consultas siempre acotadas por `school_year` y `deleted_at IS NULL`.
- Índices compuestos por `(student_id, -date)` siguiendo el patrón de
  `observer_entry`.
- Las alertas tempranas se calculan en un comando programable, no en cada
  carga de página.

---

## 9. Estrategia de implementación

Despliegue **incremental, sin ventana de indisponibilidad**. Cada fase deja el
sistema funcionando.

| Fase | Contenido | Reversible |
|---|---|---|
| **F0** | Respaldo (`scripts/respaldar_bd.py`) y verificación (`smoke_test.py`) | — |
| **F1** | Migración de las 14 tablas (solo `CREATE TABLE`) | Sí — script de rollback |
| **F2** | Modelos, servicios y reglas de negocio | Sí |
| **F3** | API REST y permisos | Sí |
| **F4** | Registro de módulos, perfiles y matriz de permisos | Sí |
| **F5** | Pantallas sobre `ResourceView` | Sí |
| **F6** | Integración con asistencia, expediente y notificaciones | Sí — bandera de configuración |
| **F7** | Alertas tempranas y tableros | Sí |
| **F8** | Reportes, exportación PDF/Excel y actas imprimibles | Sí |
| **F9** | Pruebas (unitarias, integración, permisos, seguridad) | — |
| **F10** | Datos de configuración inicial (`seed_incapacities`, `seed_coexistence`) | Sí |
| **F11** | Documentación y capacitación | — |

### Criterios de aceptación del despliegue

1. `python manage.py check` sin incidencias.
2. `python smoke_test.py` responde correctamente en **todas** las rutas previas
   y nuevas.
3. La suite existente (177 pruebas del PAE + las nuevas) pasa completa.
4. Ninguna pantalla productiva cambia de comportamiento.
5. `python manage.py migrate --check` limpio tras restaurar los scripts SQL.

### Plan de reversión

`database/extension/11_rollback.sql` elimina las 14 tablas en orden inverso de
dependencia. Como **no se modificó ninguna tabla productiva**, la reversión es
completa y no deja rastro. La única acción adicional es retirar `core.incapacities`
de `LOCAL_APPS` y el árbol del `MODULE_REGISTRY`.

---

## 10. Resumen ejecutivo

| Indicador | Valor |
|---|---|
| Tablas nuevas | 14 (5 Incapacidades + 9 Convivencia) |
| Tablas productivas modificadas | **0** |
| Columnas productivas modificadas | **0** |
| Llaves foráneas nuevas hacia tablas existentes | 41 |
| Librerías nuevas | **0** |
| Componentes visuales nuevos | **0** |
| Colores nuevos | **0** |
| Entidades duplicadas | **0** |
| Módulos de menú nuevos | 2 grupos, 18 opciones |
| Perfiles nuevos | 4 |
| Migraciones con `ALTER`/`DROP` destructivo | **0** |
