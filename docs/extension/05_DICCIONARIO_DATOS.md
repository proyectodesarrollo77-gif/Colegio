# Entregable 5 — Diccionario de Datos

**Motor:** PostgreSQL 14+ · **Codificación:** UTF-8

## Columnas heredadas de `BaseModel`

Presentes en **todas** las tablas nuevas. No se repiten en cada ficha.

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `id` | bigint | — | Sí | Llave primaria autoincremental | PK |
| `created_at` | timestamptz | — | Sí | Fecha de creación | — |
| `updated_at` | timestamptz | — | Sí | Última modificación | — |
| `deleted_at` | timestamptz | — | No | Marca de borrado lógico | Sí |
| `deleted_by_id` | bigint | — | No | Quién borró → `users_user` | FK |
| `created_by_id` | bigint | — | No | Quién creó → `users_user` | FK |
| `updated_by_id` | bigint | — | No | Quién modificó → `users_user` | FK |
| `uuid` | uuid | — | Sí | Identificador público | UNIQUE |
| `is_active` | boolean | — | Sí | Registro activo (def. `true`) | Sí |

---

# MÓDULO 1 — INCAPACIDADES

## 1.1 `incapacity_type` — Tipo de incapacidad (catálogo parametrizable)

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `code` | varchar | 32 | Sí | Código único del tipo | UNIQUE |
| `name` | varchar | 180 | Sí | Nombre visible | — |
| `description` | text | — | No | Descripción | — |
| `order` | smallint | — | Sí | Orden de presentación (def. 0) | Sí |
| `applies_to` | varchar | 16 | Sí | `ESTUDIANTE`\|`DOCENTE`\|`ADMINISTRATIVO`\|`TODOS` (def. `TODOS`) | Sí |
| `requires_support` | boolean | — | Sí | Exige soporte médico (def. `true`) — RN-I-02 | — |
| `requires_diagnosis` | boolean | — | Sí | Exige diagnóstico (def. `false`) | — |
| `justifies_attendance` | boolean | — | Sí | Justifica ausencias al aprobar (def. `true`) — RN-I-06 | — |
| `max_days` | smallint | — | No | Días máximos sin autorización especial | — |
| `color` | varchar | 20 | Sí | Color del distintivo (def. `#0EA5E9`, ya en el tema) | — |

> **Valores iniciales:** `ENF_GENERAL`, `ACCIDENTE_TRABAJO`, `ACCIDENTE_ESCOLAR`,
> `MATERNIDAD`, `PATERNIDAD`, `CITA_MEDICA`, `AISLAMIENTO`, `OTRA`.

## 1.2 `incapacity` — Incapacidad

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `number` | varchar | 32 | Sí | Consecutivo automático `INC-AAAA-NNNNN` | UNIQUE |
| `subject_type` | varchar | 16 | Sí | `ESTUDIANTE`\|`DOCENTE`\|`ADMINISTRATIVO` | Sí |
| `student_id` | bigint | — | No | → `student` (si es estudiante) | FK, Sí |
| `teacher_id` | bigint | — | No | → `teacher` (si es docente) | FK, Sí |
| `subject_user_id` | bigint | — | No | → `users_user` (si es administrativo) | FK |
| `incapacity_type_id` | bigint | — | Sí | → `incapacity_type` | FK |
| `school_year_id` | bigint | — | Sí | → `academic_school_year` | FK, Sí |
| `campus_id` | bigint | — | No | → `institution_campus` (alcance por sede) | FK |
| `start_date` | date | — | Sí | Fecha inicial | Sí |
| `end_date` | date | — | Sí | Fecha final — RN-I-01 | Sí |
| `days` | smallint | — | Sí | Días calendario, **calculado y no editable** — RN-I-09 | — |
| `working_days` | smallint | — | Sí | Días hábiles según calendario institucional | — |
| `issuer` | varchar | 180 | No | EPS, ARL o IPS que expide | — |
| `folio` | varchar | 60 | No | Número del certificado médico | Sí |
| `diagnosis` | varchar | 240 | No | **Dato sensible** — RN-I-10 | — |
| `cie10_code` | varchar | 10 | No | **Dato sensible** — código CIE-10 | — |
| `is_extension` | boolean | — | Sí | Es prórroga de otra (def. `false`) | — |
| `parent_id` | bigint | — | No | → `incapacity` (incapacidad prorrogada) | FK |
| `status` | varchar | 12 | Sí | `PENDIENTE`\|`EN_REVISION`\|`APROBADA`\|`RECHAZADA`\|`ANULADA` | Sí |
| `support_verified` | boolean | — | Sí | Soporte verificado por secretaría (def. `false`) | — |
| `verified_by_id` | bigint | — | No | → `users_user` | FK |
| `verified_at` | timestamptz | — | No | Fecha de verificación | — |
| `approved_by_id` | bigint | — | No | → `users_user` | FK |
| `approved_at` | timestamptz | — | No | Fecha de aprobación | — |
| `rejection_reason` | text | — | No | Motivo del rechazo — RN-I-05 | — |
| `cancellation_reason` | text | — | No | Motivo de la anulación — RN-I-05 | — |
| `attendance_applied` | boolean | — | Sí | Ya se justificó la asistencia (def. `false`) | — |
| `attendance_applied_at` | timestamptz | — | No | Cuándo se aplicó | — |
| `teacher_absence_id` | bigint | — | No | → `teacher_absence` — RN-I-11 | FK, UNIQUE |
| `student_document_id` | bigint | — | No | → `student_document` (soporte en expediente) | FK |
| `reported_by_id` | bigint | — | No | → `users_user` (quién registró) | FK |
| `observations` | text | — | No | Observaciones generales | — |

**Restricciones:** `ck_incapacity_subject` (sujeto único),
`ck_incapacity_dates` (`end_date >= start_date`), `ck_incapacity_days`
(`days >= 1`).

## 1.3 `incapacity_attachment` — Soporte médico

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `incapacity_id` | bigint | — | Sí | → `incapacity` (CASCADE) | FK, Sí |
| `name` | varchar | 200 | Sí | Nombre del documento | — |
| `file` | varchar | 100 | Sí | Ruta del archivo (máx. 10 MB) | — |
| `kind` | varchar | 20 | Sí | `CERTIFICADO`\|`EPICRISIS`\|`ORDEN`\|`FORMULA`\|`OTRO` | — |
| `file_size` | integer | — | Sí | Tamaño en bytes (no editable) | — |
| `content_type` | varchar | 120 | No | Tipo MIME (no editable) | — |
| `is_confidential` | boolean | — | Sí | Reservado (def. `true`) | Sí |
| `uploaded_at` | timestamptz | — | Sí | Fecha de carga | — |
| `downloads` | integer | — | Sí | Descargas registradas (def. 0) | — |

## 1.4 `incapacity_history` — Trazabilidad de estados

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `incapacity_id` | bigint | — | Sí | → `incapacity` (CASCADE) | FK, Sí |
| `previous_status` | varchar | 12 | No | Estado anterior (vacío al crear) | — |
| `new_status` | varchar | 12 | Sí | Estado nuevo | Sí |
| `reason` | text | — | No | Motivo o comentario — RN-I-05 | — |
| `changed_at` | timestamptz | — | Sí | Fecha del cambio | Sí |
| `changed_by_id` | bigint | — | No | → `users_user` | FK |

## 1.5 `incapacity_attendance_link` — Justificación aplicada

> Tabla puente que hace **reversible** la justificación automática (RN-I-08).

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `incapacity_id` | bigint | — | Sí | → `incapacity` (CASCADE) | FK, Sí |
| `attendance_record_id` | bigint | — | Sí | → `attendance_record` (CASCADE) | FK, Sí |
| `previous_status` | varchar | 10 | Sí | Estado antes de justificar (normalmente `AUSENTE`) | — |
| `applied_at` | timestamptz | — | Sí | Cuándo se justificó | — |
| `reverted_at` | timestamptz | — | No | Cuándo se revirtió (al anular) | Sí |

**Restricción:** `UNIQUE (incapacity_id, attendance_record_id)` — idempotencia.

---

# MÓDULO 2 — CONVIVENCIA ESCOLAR

## 2.1 `observer_evidence` — Evidencia del caso

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `entry_id` | bigint | — | Sí | → `observer_entry` (CASCADE) | FK, Sí |
| `kind` | varchar | 16 | Sí | `FOTOGRAFIA`\|`DOCUMENTO`\|`ACTA`\|`TESTIMONIO`\|`AUDIO`\|`VIDEO`\|`OTRO` | — |
| `name` | varchar | 200 | Sí | Nombre de la evidencia | — |
| `description` | text | — | No | Descripción | — |
| `file` | varchar | 100 | Sí | Ruta del archivo (máx. 10 MB) | — |
| `file_size` | integer | — | Sí | Tamaño en bytes (no editable) | — |
| `content_type` | varchar | 120 | No | Tipo MIME (no editable) | — |
| `captured_at` | timestamptz | — | Sí | Fecha del hecho registrado | — |
| `is_confidential` | boolean | — | Sí | Reservada (def. `false`) — RN-C-05 | Sí |

## 2.2 `observer_summons` — Citación

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `entry_id` | bigint | — | Sí | → `observer_entry` (CASCADE) | FK, Sí |
| `guardian_id` | bigint | — | No | → `student_guardian` (a quién se cita) | FK |
| `number` | varchar | 32 | Sí | Consecutivo `CIT-AAAA-NNNNN` | UNIQUE |
| `scheduled_at` | timestamptz | — | Sí | Fecha y hora de la citación | Sí |
| `place` | varchar | 160 | No | Lugar | — |
| `channel` | varchar | 12 | Sí | `PRESENCIAL`\|`VIRTUAL`\|`TELEFONICA`\|`CORREO` | — |
| `reason` | text | — | Sí | Motivo de la citación | — |
| `status` | varchar | 14 | Sí | `PROGRAMADA`\|`ATENDIDA`\|`NO_ASISTIO`\|`REPROGRAMADA`\|`CANCELADA` — RN-C-12 | Sí |
| `attended_at` | timestamptz | — | No | Fecha real de atención | — |
| `attendees` | text | — | No | Asistentes | — |
| `notes` | text | — | No | Desarrollo y acuerdos | — |
| `guardian_signed` | boolean | — | Sí | Firmada por el acudiente (def. `false`) | — |
| `student_signed` | boolean | — | Sí | Firmada por el estudiante (def. `false`) | — |
| `rescheduled_from_id` | bigint | — | No | → `observer_summons` (citación previa) | FK |
| `notified_at` | timestamptz | — | No | Cuándo se notificó | — |

## 2.3 `observer_commitment` — Compromiso

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `entry_id` | bigint | — | Sí | → `observer_entry` (CASCADE) | FK, Sí |
| `summons_id` | bigint | — | No | → `observer_summons` (si nace de una citación) | FK |
| `description` | text | — | Sí | Compromiso adquirido | — |
| `responsible_kind` | varchar | 14 | Sí | `ESTUDIANTE`\|`ACUDIENTE`\|`INSTITUCION`\|`DOCENTE` | — |
| `responsible_name` | varchar | 180 | No | Nombre del responsable | — |
| `responsible_user_id` | bigint | — | No | → `users_user` | FK |
| `indicator` | varchar | 200 | No | Indicador de cumplimiento | — |
| `start_date` | date | — | Sí | Fecha de inicio | — |
| `due_date` | date | — | Sí | Fecha límite — RN-C-07 | Sí |
| `status` | varchar | 12 | Sí | `VIGENTE`\|`CUMPLIDO`\|`INCUMPLIDO`\|`ANULADO` | Sí |
| `verified_at` | timestamptz | — | No | Fecha de verificación | — |
| `verified_by_id` | bigint | — | No | → `users_user` | FK |
| `verification_note` | text | — | No | Constancia de la verificación | — |

## 2.4 `observer_committee` — Comité de Convivencia Escolar

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `school_year_id` | bigint | — | Sí | → `academic_school_year` | FK, Sí |
| `campus_id` | bigint | — | No | → `institution_campus` | FK |
| `name` | varchar | 180 | Sí | Nombre del comité | — |
| `constitution_act` | varchar | 60 | No | Acta de conformación | — |
| `constituted_on` | date | — | No | Fecha de conformación | — |
| `quorum_minimum` | smallint | — | Sí | Asistentes mínimos (def. 3) — RN-C-06 | — |
| `status` | varchar | 12 | Sí | `VIGENTE`\|`DISUELTO` | Sí |
| `observations` | text | — | No | Observaciones | — |

**Restricción:** un solo comité `VIGENTE` por `(school_year_id, campus_id)`.

## 2.5 `observer_committee_member` — Miembro del comité

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `committee_id` | bigint | — | Sí | → `observer_committee` (CASCADE) | FK, Sí |
| `user_id` | bigint | — | Sí | → `users_user` | FK, Sí |
| `role` | varchar | 24 | Sí | `PRESIDENTE`\|`PERSONERO`\|`DOCENTE`\|`ORIENTADOR`\|`PADRE`\|`ESTUDIANTE`\|`OTRO` | — |
| `is_active` | boolean | — | Sí | Miembro activo (heredado) | — |
| `joined_on` | date | — | No | Fecha de vinculación | — |
| `left_on` | date | — | No | Fecha de retiro | — |

**Restricción:** `UNIQUE (committee_id, user_id)`.

## 2.6 `observer_committee_session` — Sesión del comité

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `committee_id` | bigint | — | Sí | → `observer_committee` (CASCADE) | FK, Sí |
| `number` | varchar | 32 | Sí | Número del acta | Sí |
| `session_date` | timestamptz | — | Sí | Fecha y hora | Sí |
| `place` | varchar | 160 | No | Lugar | — |
| `kind` | varchar | 12 | Sí | `ORDINARIA`\|`EXTRAORDINARIA` | — |
| `agenda` | text | — | No | Orden del día | — |
| `development` | text | — | No | Desarrollo de la sesión | — |
| `conclusions` | text | — | No | Conclusiones | — |
| `attendees_count` | smallint | — | Sí | Asistentes (def. 0) — RN-C-06 | — |
| `has_quorum` | boolean | — | Sí | Quórum alcanzado (calculado) | Sí |
| `status` | varchar | 14 | Sí | `PROGRAMADA`\|`REALIZADA`\|`SIN_QUORUM`\|`CANCELADA` | Sí |
| `minutes_file` | varchar | 100 | No | Acta firmada escaneada | — |

**Restricción:** `UNIQUE (committee_id, number)`.

## 2.7 `observer_decision` — Decisión

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `entry_id` | bigint | — | Sí | → `observer_entry` (CASCADE) | FK, Sí |
| `session_id` | bigint | — | No | → `observer_committee_session` | FK, Sí |
| `kind` | varchar | 16 | Sí | `FORMATIVA`\|`CORRECTIVA`\|`REMISION`\|`ABSOLUCION`\|`OTRA` | Sí |
| `description` | text | — | Sí | Decisión adoptada | — |
| `manual_article` | varchar | 120 | Sí | Artículo del manual — RN-C-08 | — |
| `effective_from` | date | — | No | Vigente desde | — |
| `effective_to` | date | — | No | Vigente hasta | — |
| `decided_by_id` | bigint | — | No | → `users_user` | FK |
| `decided_at` | timestamptz | — | Sí | Fecha de la decisión | — |
| `notified_at` | timestamptz | — | No | Cuándo se notificó | — |
| `appeal_filed` | boolean | — | Sí | Se interpuso recurso (def. `false`) | — |
| `appeal_text` | text | — | No | Recurso de reposición | — |
| `appeal_resolution` | text | — | No | Resolución del recurso | — |

## 2.8 `observer_status_log` — Trazabilidad del caso

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `entry_id` | bigint | — | Sí | → `observer_entry` (CASCADE) | FK, Sí |
| `previous_status` | varchar | 16 | No | Estado anterior | — |
| `new_status` | varchar | 16 | Sí | Estado nuevo | Sí |
| `reason` | text | — | No | Justificación — RN-C-09 | — |
| `changed_at` | timestamptz | — | Sí | Fecha del cambio | Sí |
| `changed_by_id` | bigint | — | No | → `users_user` | FK |

## 2.9 `observer_alert_rule` — Regla de alerta temprana

> **Parametrizable — RN-C-10.** Los umbrales nunca están fijos en el código.

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `code` | varchar | 32 | Sí | Código único | UNIQUE |
| `name` | varchar | 180 | Sí | Nombre de la regla | — |
| `rule_type` | varchar | 24 | Sí | `REINCIDENCIA`\|`INASISTENCIA`\|`RENDIMIENTO`\|`COMPROMISO_INCUMPLIDO`\|`TIPO_III` | Sí |
| `threshold` | numeric(8,2) | — | Sí | Umbral que dispara la alerta | — |
| `window_days` | smallint | — | Sí | Ventana de observación en días (def. 30) | — |
| `severity` | varchar | 12 | Sí | `INFO`\|`ADVERTENCIA`\|`CRITICA` | — |
| `notify_role` | varchar | 40 | No | Perfil destinatario | — |
| `description` | text | — | No | Qué detecta | — |
| `is_active` | boolean | — | Sí | Regla activa (heredado) | Sí |

## 2.10 `observer_alert` — Alerta temprana generada

| Campo | Tipo | Long. | Oblig. | Descripción | Índice |
|---|---|---|---|---|---|
| `rule_id` | bigint | — | Sí | → `observer_alert_rule` | FK, Sí |
| `student_id` | bigint | — | Sí | → `student` | FK, Sí |
| `entry_id` | bigint | — | No | → `observer_entry` (si nace de un caso) | FK |
| `school_year_id` | bigint | — | Sí | → `academic_school_year` | FK |
| `level` | varchar | 12 | Sí | `INFO`\|`ADVERTENCIA`\|`CRITICA` | Sí |
| `title` | varchar | 200 | Sí | Título de la alerta | — |
| `message` | text | — | No | Detalle y valor medido | — |
| `measured_value` | numeric(8,2) | — | No | Valor que superó el umbral | — |
| `status` | varchar | 12 | Sí | `ABIERTA`\|`ATENDIDA`\|`DESCARTADA` | Sí |
| `attended_by_id` | bigint | — | No | → `users_user` | FK |
| `attended_at` | timestamptz | — | No | Fecha de atención | — |
| `action_taken` | text | — | No | Acción tomada | — |

**Restricción:** `UNIQUE (rule_id, student_id, school_year_id)` sobre alertas
`ABIERTA` — evita alertar dos veces por el mismo hecho.

---

## Resumen

| Módulo | Tablas | Campos propios | FK a tablas existentes | Índices |
|---|---|---|---|---|
| Incapacidades | 5 | 71 | 14 | 10 |
| Convivencia | 9 | 108 | 27 | 28 |
| **Total** | **14** | **179** | **41** | **38** |
