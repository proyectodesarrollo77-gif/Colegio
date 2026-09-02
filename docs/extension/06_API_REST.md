# Entregable 7 — Diseño de la API REST

Los endpoints siguen **exactamente** las convenciones de la API actual: rutas en
inglés kebab-case plural, paginación, filtros, ordenamiento, `options/`,
`stats/` y `export/` heredados de `BaseModelViewSet`.

**Base:** `/api/` · **Autenticación:** sesión o `Authorization: Bearer <JWT>`
**Autorización:** `HasModulePermission` (módulo × acción)

## Mapeo método → acción de permiso

| Método | Acción | Ejemplo |
|---|---|---|
| `GET` | `view` | Listar y consultar |
| `POST` | `create` | Crear |
| `PUT` / `PATCH` | `edit` | Modificar |
| `DELETE` | `delete` | Borrado lógico |
| `GET .../export/` | `export` | Exportar |
| `POST .../approve/`, `.../transition/` | `approve` | Aprobar |

## Códigos HTTP

| Código | Cuándo |
|---|---|
| `200` | Consulta o acción correcta |
| `201` | Recurso creado |
| `204` | Borrado lógico correcto |
| `400` | Validación de negocio o de datos |
| `401` | Sin autenticar |
| `403` | Autenticado sin permiso sobre el módulo o la acción |
| `404` | No existe, borrado lógicamente o fuera del alcance por sede |
| `409` | Conflicto de estado (transición no permitida, traslape) |
| `413` | Archivo supera el límite |
| `422` | Archivo con extensión o tipo no permitido |
| `500` | Error no controlado (registrado en la bitácora) |

## Formato de error (el del sistema, sin cambios)

```json
{
  "success": false,
  "error": "validation_error",
  "detail": { "end_date": ["La fecha final no puede ser anterior a la inicial."] }
}
```

---

# MÓDULO 1 — INCAPACIDADES

## 1.1 Recursos

| Prefijo | Módulo de permisos | Descripción |
|---|---|---|
| `/api/incapacity-types/` | `incapacities.configuracion` | Tipos parametrizables |
| `/api/incapacities/` | `incapacities.registro` | Incapacidades |
| `/api/incapacity-attachments/` | `incapacities.registro` | Soportes médicos |
| `/api/incapacity-history/` | `incapacities.registro` | Historial (solo lectura) |

## 1.2 `GET /api/incapacities/`

**Filtros:** `subject_type`, `student`, `teacher`, `status`, `incapacity_type`,
`school_year`, `campus`, `start_date__gte`, `end_date__lte`
**Búsqueda:** `?search=` sobre `number`, `folio`, `issuer`
**Orden:** `?ordering=-start_date` · **Paginación:** `?page=1&page_size=25`

```http
GET /api/incapacities/?status=EN_REVISION&subject_type=ESTUDIANTE&page_size=25
```

```json
{
  "count": 42, "num_pages": 2, "next": "...?page=2", "previous": null,
  "results": [
    {
      "id": 118,
      "number": "INC-2026-00118",
      "subject_type": "ESTUDIANTE",
      "subject_name": "Maria Fernanda Gomez Rojas",
      "subject_document": "1012345678",
      "student": 512, "teacher": null, "subject_user": null,
      "incapacity_type": 1, "incapacity_type_name": "Enfermedad general",
      "school_year": 3, "campus": 1, "campus_name": "Sede Principal",
      "start_date": "2026-03-02", "end_date": "2026-03-06",
      "days": 5, "working_days": 5,
      "issuer": "EPS Ejemplo", "folio": "CM-99887",
      "status": "EN_REVISION", "status_display": "En revision",
      "support_verified": true,
      "attachments_count": 2,
      "attendance_applied": false,
      "allowed_transitions": [
        { "status": "APROBADA",  "action": "approve" },
        { "status": "RECHAZADA", "action": "approve" },
        { "status": "PENDIENTE", "action": "edit" }
      ],
      "created_at": "2026-03-02T09:14:22-05:00"
    }
  ]
}
```

> **`diagnosis` y `cie10_code` no aparecen** salvo que el usuario tenga
> `view` sobre `incapacities.confidencial` (RN-I-10). El filtrado ocurre en el
> serializer, en el servidor.

## 1.3 `POST /api/incapacities/`

```json
{
  "subject_type": "ESTUDIANTE",
  "student": 512,
  "incapacity_type": 1,
  "start_date": "2026-03-02",
  "end_date": "2026-03-06",
  "issuer": "EPS Ejemplo",
  "folio": "CM-99887",
  "observations": "Reposo domiciliario"
}
```

**Validaciones:** RN-I-01 (fechas), RN-I-03 (traslape), sujeto único y activo,
`incapacity_type.applies_to` compatible con `subject_type`.

`201 Created` devuelve el objeto con `number`, `days` y `working_days`
calculados. `days` y `working_days` **se ignoran si se envían**.

**409 Conflict — traslape (RN-I-03):**

```json
{
  "success": false,
  "error": "conflict",
  "detail": { "start_date": ["Ya existe una incapacidad vigente del 2026-03-01 al 2026-03-10 (INC-2026-00110)."] },
  "conflicting": { "id": 110, "number": "INC-2026-00110" }
}
```

## 1.4 `POST /api/incapacities/{id}/transition/`

Única puerta para cambiar de estado. Acción requerida según la transición.

```json
{ "status": "APROBADA", "reason": "Soporte verificado" }
```

**200 OK**

```json
{
  "success": true,
  "status": "APROBADA",
  "attendance": { "justified": 5, "skipped": 2, "detail": "2 registros no se modificaron por no estar en AUSENTE" },
  "teacher_absence": null,
  "student_document": 3391,
  "notifications": 4
}
```

- `403` sin permiso `approve`.
- `409` transición no permitida:

```json
{ "success": false, "error": "invalid_transition",
  "detail": { "status": ["Transicion no permitida: PENDIENTE -> APROBADA. Permitidas: EN_REVISION."] } }
```

- `400` al rechazar o anular sin motivo (RN-I-05).

## 1.5 `POST /api/incapacities/{id}/attachments/`

`multipart/form-data`: `file`, `name`, `kind`, `is_confidential`.
Máx. **10 MB**; extensiones `.pdf .png .jpg .jpeg .webp`.

- `413` supera el tamaño · `422` extensión o tipo no permitido.

## 1.6 `GET /api/incapacity-attachments/{id}/download/`

Devuelve el archivo y **registra la descarga en la bitácora** con usuario, fecha
e IP. `403` si es confidencial y falta `incapacities.confidencial`.

## 1.7 `GET /api/incapacities/{id}/history/`

```json
{ "results": [
  { "previous_status": "EN_REVISION", "new_status": "APROBADA",
    "reason": "Soporte verificado", "changed_at": "2026-03-02T10:41:07-05:00",
    "changed_by_name": "Coordinador Academico" }
] }
```

## 1.8 `GET /api/incapacities/dashboard/`

```json
{
  "totals": { "active": 18, "pending": 7, "days_accumulated": 143, "students": 12, "teachers": 5, "staff": 1 },
  "charts": {
    "by_type":    { "labels": ["Enfermedad general", "Cita medica"], "data": [24, 9] },
    "by_month":   { "labels": ["Ene", "Feb", "Mar"], "data": [4, 11, 18] },
    "by_campus":  { "labels": ["Sede Principal", "Sede B"], "data": [21, 12] }
  },
  "alerts": [
    { "level": "warning", "code": "pendientes", "title": "7 incapacidades pendientes de revision",
      "url": "/incapacidades/registro/?status=PENDIENTE", "count": 7 }
  ]
}
```

## 1.9 Otros

| Endpoint | Función |
|---|---|
| `GET /api/incapacities/export/?format=xlsx` | Exportar (`export`) |
| `GET /api/incapacities/options/` | Pares id/label |
| `GET /api/incapacities/stats/` | Conteos por estado |
| `POST /api/incapacities/import/` | Importación masiva con errores por fila y columna |
| `GET /api/incapacities/{id}/certificate/` | Constancia PDF imprimible |

---

# MÓDULO 2 — CONVIVENCIA ESCOLAR

> `/api/observer-entries/` **ya existe y no cambia**. Se agregan recursos que
> cuelgan de él y una acción de transición.

## 2.1 Recursos

| Prefijo | Módulo de permisos |
|---|---|
| `/api/observer-evidences/` | `observer.records` |
| `/api/observer-summons/` | `coexistence.citaciones` |
| `/api/observer-commitments/` | `coexistence.compromisos` |
| `/api/observer-committees/` | `coexistence.comite` |
| `/api/observer-committee-members/` | `coexistence.comite` |
| `/api/observer-committee-sessions/` | `coexistence.comite` |
| `/api/observer-decisions/` | `coexistence.decisiones` |
| `/api/observer-alert-rules/` | `coexistence.configuracion` |
| `/api/observer-alerts/` | `coexistence.alertas` |

## 2.2 `POST /api/observer-entries/{id}/transition/`

```json
{ "status": "ESCALADO_COMITE", "reason": "Situacion tipo II reiterada", "session": 12 }
```

**200 OK**

```json
{ "success": true, "status": "ESCALADO_COMITE", "session": 12, "notifications": 6 }
```

**400 — cierre con compromisos pendientes (RN-C-03):**

```json
{ "success": false, "error": "validation_error",
  "detail": { "status": ["No se puede cerrar: 2 compromisos sin verificar."],
              "pending_commitments": [88, 91] } }
```

**400 — cierre sin decisión tras escalamiento (RN-C-04):**

```json
{ "success": false, "error": "validation_error",
  "detail": { "status": ["El caso fue escalado al comite y no tiene decision registrada."] } }
```

## 2.3 `POST /api/observer-summons/`

```json
{
  "entry": 774, "guardian": 233,
  "scheduled_at": "2026-03-10T14:00:00-05:00",
  "place": "Coordinacion de convivencia",
  "channel": "PRESENCIAL",
  "reason": "Socializacion de la situacion y firma de compromisos"
}
```

`201` devuelve `number` (`CIT-2026-00045`) y `status: "PROGRAMADA"`; notifica al
acudiente y al estudiante.

### `POST /api/observer-summons/{id}/attend/`

```json
{ "attendees": "Madre y estudiante", "notes": "Se acuerda acompanamiento",
  "guardian_signed": true, "student_signed": true }
```

### `POST /api/observer-summons/{id}/reschedule/`

```json
{ "scheduled_at": "2026-03-14T14:00:00-05:00", "reason": "El acudiente no asistio" }
```

Marca la anterior como `NO_ASISTIO` y crea una nueva enlazada por
`rescheduled_from` — **ambas quedan en el historial** (RN-C-12).

## 2.4 `POST /api/observer-commitments/{id}/verify/`

```json
{ "status": "CUMPLIDO", "verification_note": "Se evidencia mejora sostenida" }
```

`400` si se intenta verificar un compromiso `ANULADO`.

## 2.5 `POST /api/observer-committee-sessions/{id}/close/`

```json
{ "attendees_count": 5, "development": "...", "conclusions": "..." }
```

**200 OK**

```json
{ "success": true, "status": "REALIZADA", "has_quorum": true, "quorum_minimum": 3 }
```

**409 — sin quórum (RN-C-06):**

```json
{ "success": false, "error": "no_quorum",
  "detail": { "attendees_count": ["Asistieron 2 miembros y el quorum minimo es 3."] },
  "status": "SIN_QUORUM" }
```

Con `SIN_QUORUM`, `POST /api/observer-decisions/` sobre esa sesión responde
`409`.

## 2.6 `POST /api/observer-decisions/`

```json
{
  "entry": 774, "session": 12, "kind": "FORMATIVA",
  "description": "Acompanamiento pedagogico durante cuatro semanas",
  "manual_article": "Articulo 45, literal c",
  "effective_from": "2026-03-15", "effective_to": "2026-04-15"
}
```

`400` si `manual_article` viene vacío (RN-C-08).

### `POST /api/observer-decisions/{id}/appeal/`

```json
{ "appeal_text": "Se interpone recurso de reposicion..." }
```

## 2.7 `GET /api/observer-alerts/`

```json
{ "count": 9, "results": [
  { "id": 40, "rule": 2, "rule_name": "Reincidencia en situaciones tipo II",
    "student": 512, "student_name": "Maria Fernanda Gomez Rojas",
    "level": "CRITICA", "title": "2 situaciones tipo II en 60 dias",
    "measured_value": 2.0, "status": "ABIERTA",
    "created_at": "2026-03-08T06:00:11-05:00" }
] }
```

### `POST /api/observer-alerts/{id}/attend/`

```json
{ "status": "ATENDIDA", "action_taken": "Remision a orientacion escolar" }
```

### `POST /api/observer-alerts/evaluate/`

Ejecuta las reglas activas. Requiere `create` sobre `coexistence.alertas`.

```json
{ "success": true, "evaluated_rules": 6, "created": 3, "skipped_existing": 2,
  "skipped_by_incapacity": 1 }
```

> `skipped_by_incapacity` refleja la integración entre módulos: no se alerta por
> inasistencia cubierta por una incapacidad **aprobada**.

## 2.8 `GET /api/observer-entries/{id}/dossier/`

Expediente consolidado del caso en una sola llamada.

```json
{
  "entry": { "id": 774, "status": "ESCALADO_COMITE", "category_name": "Situacion tipo II - Grave" },
  "evidences": [ { "id": 91, "name": "Acta de descargos", "is_confidential": false } ],
  "summons": [ { "id": 45, "number": "CIT-2026-00045", "status": "ATENDIDA" } ],
  "commitments": [ { "id": 88, "status": "VIGENTE", "due_date": "2026-04-10" } ],
  "decisions": [],
  "follow_ups": [ { "id": 61, "result": "PARCIAL" } ],
  "status_log": [ { "previous_status": "ABIERTA", "new_status": "EN_SEGUIMIENTO" } ]
}
```

Las evidencias confidenciales **se omiten** sin el permiso correspondiente.

## 2.9 `GET /api/coexistence/dashboard/`

```json
{
  "totals": { "open_cases": 23, "escalated": 4, "commitments_due": 7,
              "open_alerts": 9, "positive_records": 41 },
  "charts": {
    "by_severity": { "labels": ["Tipo I", "Tipo II", "Tipo III"], "data": [52, 14, 3] },
    "by_status":   { "labels": ["Abierta", "En seguimiento", "Escalado", "Cerrada"], "data": [12, 11, 4, 42] },
    "by_grade":    { "labels": ["Sexto", "Septimo"], "data": [18, 24] },
    "monthly":     { "labels": ["Ene", "Feb", "Mar"], "data": [9, 21, 39] }
  },
  "alerts": [
    { "level": "danger", "code": "compromisos_vencidos",
      "title": "7 compromisos vencidos sin verificar", "url": "/convivencia/compromisos/", "count": 7 }
  ]
}
```

---

## 3. Validaciones transversales

| Validación | Dónde | Respuesta |
|---|---|---|
| Autenticación | `IsAuthenticated` | `401` |
| Permiso módulo × acción | `HasModulePermission` | `403` |
| Alcance por sede | `get_queryset()` | `404` |
| Acudiente solo ve a su estudiante (RN-C-11) | `get_queryset()` | `404` |
| Campos calculados enviados por el cliente | `read_only_fields` | Se ignoran silenciosamente |
| Archivo | `validate_document_upload` | `413` / `422` |
| Reglas de negocio | `services.py` | `400` / `409` |
| Borrado | Lógico (`deleted_at`) | `204` |

## 4. Registro en la bitácora

| Operación | Acción registrada |
|---|---|
| `POST` | `CREATE` |
| `PUT` / `PATCH` | `UPDATE` (con estado anterior) |
| `DELETE` | `DELETE` |
| `transition` a `APROBADA` | `APPROVE` |
| `export` | `EXPORT` |
| `import` | `PROCESS` |
| Descarga de soporte confidencial | `EXPORT` |

Consultable con `GET /api/audit-logs/?module_prefix=incapacities` y
`?module_prefix=coexistence`.

## 5. Compatibilidad

- **No se modifica ningún endpoint existente.** `/api/observer-entries/`
  conserva su contrato; solo gana campos nuevos de solo lectura
  (`evidences_count`, `summons_count`, `commitments_count`), lo que es
  retrocompatible.
- **No se versiona la API**: al ser aditivo, los clientes actuales siguen
  funcionando sin cambios.
