# Entregable 2 — Diseño Funcional

---

# MÓDULO 1 — GESTIÓN DE INCAPACIDADES

## 1. Objetivos

**General:** centralizar el registro, la aprobación y el seguimiento de las
incapacidades médicas de estudiantes, docentes y personal administrativo,
integrándolas automáticamente con la asistencia, el expediente y las
notificaciones que la plataforma ya opera.

**Específicos:**

1. Registrar la incapacidad con sus soportes médicos verificables.
2. Aplicar un flujo de aprobación con trazabilidad completa.
3. **Justificar automáticamente** las ausencias del periodo incapacitado.
4. Notificar a docentes y acudientes sin intervención manual.
5. Conservar el historial y producir reportes exportables.
6. Proteger el dato de salud según la Ley 1581 de 2012.

## 2. Alcance

### Incluido

- Incapacidades de **estudiantes, docentes y administrativos**.
- Tipos parametrizables (enfermedad general, accidente, licencia de
  maternidad/paternidad, cita médica, cuarentena).
- Soportes múltiples por incapacidad, con validación de archivo.
- Flujo `PENDIENTE → EN_REVISION → APROBADA / RECHAZADA`, más `ANULADA`.
- Solicitud de correcciones con devolución al solicitante.
- Justificación automática y **reversible** de la asistencia.
- Registro del soporte en el expediente del estudiante.
- Vinculación con la novedad docente para la asignación de suplentes.
- Reportes, tablero e indicadores; exportación PDF y Excel.

### Excluido (fuera de alcance, se declara explícitamente)

- Liquidación económica de la incapacidad ante la EPS o ARL.
- Interoperabilidad con sistemas externos de salud.
- Nómina y descuentos.
- Historia clínica: solo se custodia el **certificado**, no el expediente médico.

## 3. Actores

| Actor | Perfil del sistema | Responsabilidad |
|---|---|---|
| Solicitante | `ACUDIENTE`, `DOCENTE`, `ESTUDIANTE` | Registra la incapacidad y adjunta el soporte |
| Secretaría | `SECRETARIA` | Recibe, verifica el soporte y pasa a revisión |
| Aprobador | `COORDINADOR`, `RECTOR`, `GESTOR_INCAPACIDADES` | Aprueba, rechaza o solicita corrección |
| Enfermería / Bienestar | `SALUD_OCUPACIONAL` | Consulta el dato clínico y hace seguimiento |
| Docente | `DOCENTE` | Recibe la notificación y ve la ausencia ya justificada |
| Auditor | `AUDITOR`, `AUDITOR_PAE` | Consulta la trazabilidad. No modifica |
| Sistema | — | Justifica asistencia, notifica, calcula indicadores |

## 4. Casos de uso

### CU-I-01 · Registrar incapacidad

- **Actor:** Solicitante · **Precondición:** sesión iniciada, año lectivo vigente
- **Flujo principal:**
  1. Selecciona el tipo de sujeto y la persona (estudiante, docente o administrativo).
  2. Indica tipo de incapacidad, fecha inicial y final, entidad emisora y folio.
  3. Adjunta al menos un soporte (PDF o imagen, máx. 10 MB).
  4. El sistema calcula los días y valida el traslape (RN-I-03).
  5. Guarda en estado `PENDIENTE` y notifica a Secretaría.
- **Postcondición:** incapacidad creada y auditada.

**Flujos alternativos**

- *A1 — Sin soporte:* si el tipo lo exige (RN-I-02) se rechaza el guardado y se
  indica el campo faltante.
- *A2 — Fechas invertidas:* error de validación en `end_date`.
- *A3 — Traslape:* se muestra la incapacidad vigente y se ofrece **prorrogarla**
  en lugar de crear una nueva.
- *A4 — Sujeto inactivo:* estudiante retirado o docente inactivo → rechazo con
  el motivo.

### CU-I-02 · Verificar y pasar a revisión

- **Actor:** Secretaría
- **Flujo:** abre la incapacidad `PENDIENTE`, verifica el soporte, marca
  `soporte verificado` y la pasa a `EN_REVISION`; el sistema notifica al aprobador.
- **Alternativo A1 — Soporte ilegible:** solicita corrección → estado
  `PENDIENTE` con observación; se notifica al solicitante.

### CU-I-03 · Aprobar incapacidad

- **Actor:** Aprobador · **Precondición:** estado `EN_REVISION`, permiso `approve`
- **Flujo principal:**
  1. Revisa datos y soportes.
  2. Confirma la aprobación.
  3. El sistema, **en una sola transacción**:
     - cambia el estado a `APROBADA` y registra aprobador y fecha;
     - **justifica la asistencia** del rango (solo registros `AUSENTE`);
     - recalcula `attendance_summary`;
     - si es estudiante, registra el soporte en `student_document`;
     - si es docente, **crea o vincula** `teacher_absence`;
     - notifica a docentes del grupo y al acudiente principal;
     - registra la operación en `audit_log`.
- **Postcondición:** ausencias justificadas y partes notificadas.

**Flujos alternativos**

- *A1 — Sin permiso de aprobación:* HTTP 403; el estado no cambia.
- *A2 — Sin sesiones de asistencia en el rango:* se aprueba igual y se informa
  que no hubo ausencias que justificar.
- *A3 — Falla al notificar:* la aprobación **se conserva**; la notificación se
  reintenta y el fallo queda en el log (nunca interrumpe la operación de negocio).

### CU-I-04 · Rechazar incapacidad

- **Actor:** Aprobador
- **Flujo:** indica el **motivo obligatorio** (RN-I-05) → estado `RECHAZADA` →
  notifica al solicitante. **No se toca la asistencia.**

### CU-I-05 · Solicitar corrección

- **Actor:** Secretaría o Aprobador
- **Flujo:** describe qué debe corregirse → vuelve a `PENDIENTE` → notifica.
  Cada solicitud queda en el historial.

### CU-I-06 · Anular incapacidad aprobada

- **Actor:** Aprobador con permiso `delete` · **Precondición:** estado `APROBADA`
- **Flujo:** registra el motivo → estado `ANULADA` → el sistema **revierte** las
  justificaciones aplicadas usando `incapacity_attendance_link`, recalcula el
  consolidado, marca la novedad docente y notifica.
- **Alternativo A1 — Periodo académico cerrado:** no se revierte la asistencia;
  se advierte y queda constancia en el historial.

### CU-I-07 · Consultar historial

- **Actor:** cualquier perfil con `view` · Filtros por sujeto, tipo, estado,
  rango de fechas y sede. **Sin permiso `incapacities.confidencial` no se
  devuelve el diagnóstico.**

### CU-I-08 · Generar reportes

- **Actor:** Aprobador, Auditor · Exportación XLSX/CSV con `ExportMixin` y
  constancia PDF imprimible. Cada exportación se audita.

## 5. Reglas de negocio

| # | Regla | Validación |
|---|---|---|
| **RN-I-01** | La fecha final no puede ser anterior a la inicial | `end_date >= start_date` |
| **RN-I-02** | Los tipos marcados `requires_support` exigen al menos un soporte antes de pasar a `EN_REVISION` | Servicio + API |
| **RN-I-03** | Un sujeto no puede tener dos incapacidades **vigentes** con fechas traslapadas | Consulta de traslape excluyendo `RECHAZADA` y `ANULADA` |
| **RN-I-04** | Solo se aprueba desde `EN_REVISION`, y solo con permiso `approve` | Máquina de estados + permiso |
| **RN-I-05** | Rechazar, solicitar corrección o anular **exige motivo** | Campo obligatorio |
| **RN-I-06** | La justificación automática **solo** modifica registros `AUSENTE` | Filtro explícito |
| **RN-I-07** | Toda transición deja historial con usuario, fecha, estado anterior y motivo | Servicio + señal |
| **RN-I-08** | Al anular se revierten las justificaciones que la incapacidad aplicó | Vínculo trazable |
| **RN-I-09** | Los días se calculan automáticamente y no son editables | `editable=False` |
| **RN-I-10** | El diagnóstico solo se expone con permiso `incapacities.confidencial` | Filtrado en el serializer |
| **RN-I-11** | La incapacidad de docente aprobada crea o vincula **una sola** novedad docente | Relación 1:1 |
| **RN-I-12** | Una incapacidad `APROBADA` no se edita; se anula y se registra de nuevo | Máquina de estados |

### Máquina de estados

```
                 ┌──────────────┐
                 │  PENDIENTE   │◄────── solicitar corrección ──────┐
                 └──────┬───────┘                                   │
                        │ verificar soporte                         │
                        ▼                                           │
                 ┌──────────────┐                                   │
                 │ EN_REVISION  │───────────────────────────────────┘
                 └──┬────────┬──┘
             aprobar│        │rechazar
                    ▼        ▼
            ┌───────────┐  ┌───────────┐
            │ APROBADA  │  │ RECHAZADA │
            └─────┬─────┘  └───────────┘
                  │ anular (con motivo)
                  ▼
            ┌───────────┐
            │  ANULADA  │
            └───────────┘
```

| Desde | Hacia | Acción requerida |
|---|---|---|
| `PENDIENTE` | `EN_REVISION` | `edit` |
| `EN_REVISION` | `PENDIENTE` | `edit` (corrección) |
| `EN_REVISION` | `APROBADA` | **`approve`** |
| `EN_REVISION` | `RECHAZADA` | **`approve`** |
| `APROBADA` | `ANULADA` | **`delete`** |
| `RECHAZADA` / `ANULADA` | — | terminal |

---

# MÓDULO 2 — CONVIVENCIA ESCOLAR

> **Extiende `core/observer`.** El caso disciplinario sigue siendo
> `observer_entry`; se agregan citación, comité, acta, decisión, compromiso
> con seguimiento, evidencias múltiples y alertas tempranas.

## 1. Objetivos

**General:** completar el observador existente hasta cubrir el debido proceso
del Sistema Nacional de Convivencia Escolar (Ley 1620 de 2013), sin duplicar el
historial disciplinario ya en producción.

**Específicos:**

1. Estructurar citaciones a acudientes con confirmación de asistencia.
2. Formalizar el escalamiento al comité con actas, quórum y decisiones.
3. Convertir los compromisos de texto libre en acuerdos con seguimiento y vencimiento.
4. Permitir evidencias múltiples con control de acceso.
5. Generar alertas tempranas con umbrales **parametrizables**.
6. Registrar reconocimientos positivos con la misma trazabilidad.

## 2. Alcance

### Incluido

- Citaciones con fecha, medio, asistentes y acta de atención.
- Comité de Convivencia Escolar: conformación, sesiones, quórum, actas y decisiones.
- Compromisos con responsable, plazo, seguimiento y verificación de cumplimiento.
- Evidencias múltiples por caso.
- Estado `ESCALADO_COMITE` en el flujo existente.
- Alertas tempranas por reincidencia, inasistencia y bajo rendimiento.
- Reconocimientos positivos y ruta de atención integral.
- Reportes, exportación y actas imprimibles.

### Excluido

- Reemplazar el observador actual (se **extiende**).
- Reportes al SIUCE u otros sistemas externos.
- Gestión psicológica clínica (solo la remisión).

## 3. Actores

| Actor | Perfil | Responsabilidad |
|---|---|---|
| Docente | `DOCENTE` | Reporta la situación |
| Director de grupo | `TUTOR` | Atiende, cita al acudiente y hace seguimiento |
| Coordinador de convivencia | `COORDINADOR`, `GESTOR_CONVIVENCIA` | Clasifica, escala y decide |
| Comité de Convivencia | `MIEMBRO_COMITE` | Sesiona, deja acta y decide |
| Orientación escolar | `ORIENTACION` | Remisión y acompañamiento |
| Rector | `RECTOR` | Preside el comité y firma decisiones |
| Acudiente | `ACUDIENTE` | Es citado y firma compromisos |
| Estudiante | `ESTUDIANTE` | Consulta su historial y compromisos |
| Sistema | — | Alertas, notificaciones, indicadores |

## 4. Casos de uso

### CU-C-01 · Registrar caso disciplinario

Usa `observer_entry` **ya existente**. Se agregan: evidencias múltiples y
compromisos estructurados. Sin cambios en el flujo actual del docente.

**Alternativos:** *A1* categoría `requires_guardian` → propone citación
automáticamente. *A2* categoría `TIPO_III` → alerta inmediata a rectoría.

### CU-C-02 · Adjuntar evidencias

- **Actor:** Docente, Coordinador
- **Flujo:** adjunta uno o varios archivos con descripción y fecha de captura;
  el sistema valida extensión, tipo y tamaño.
- **Alternativo A1 — Evidencia reservada:** se marca `is_confidential` y solo
  la ven los perfiles con `coexistence.confidencial`.

### CU-C-03 · Programar citación

- **Actor:** Director de grupo, Coordinador
- **Flujo:** define fecha, hora, lugar, medio y motivo; el sistema notifica al
  acudiente y al estudiante y genera la citación imprimible.
- **Postcondición:** citación en estado `PROGRAMADA`.
- **Alternativos:** *A1* acudiente no asiste → `NO_ASISTIO`, se habilita
  reprogramación y queda constancia (relevante para el debido proceso).
  *A2* sin acudiente registrado → advertencia y remisión a Estudiantes.

### CU-C-04 · Registrar compromiso

- **Actor:** Coordinador, Director de grupo
- **Flujo:** describe el compromiso, responsable (estudiante, acudiente o
  institución), fecha límite e indicador de cumplimiento → estado `VIGENTE`.
- **Alternativo A1 — Vencido sin verificar:** el sistema lo marca `INCUMPLIDO`
  y genera alerta.

### CU-C-05 · Escalar al comité

- **Actor:** Coordinador · **Precondición:** caso `ABIERTA` o `EN_SEGUIMIENTO`
- **Flujo:** justifica el escalamiento → estado `ESCALADO_COMITE` → se asocia a
  una sesión del comité y se notifica a sus miembros.
- **Alternativos:** *A1* sin comité conformado en el año lectivo → se exige
  conformarlo. *A2* categoría `TIPO_I` → se advierte que el manual no lo
  contempla y se exige justificación reforzada.

### CU-C-06 · Sesionar y levantar acta

- **Actor:** Comité
- **Flujo:** registra fecha, asistentes y orden del día; el sistema **valida el
  quórum** (RN-C-06); se consignan desarrollo, decisiones y compromisos; el acta
  queda numerada e imprimible.
- **Alternativo A1 — Sin quórum:** no se permite registrar decisiones; la sesión
  se marca `SIN_QUORUM` y se reprograma.

### CU-C-07 · Registrar decisión

- **Actor:** Comité, Rector
- **Flujo:** tipifica la decisión (formativa, correctiva, remisión, absolución),
  la sustenta en el artículo del manual, fija vigencia y notifica.
- **Alternativo A1 — Recurso de reposición:** se registra el recurso y su
  resolución sobre la misma decisión.

### CU-C-08 · Cerrar el caso

- **Actor:** Coordinador · **Precondición:** compromisos verificados y, si hubo
  escalamiento, decisión registrada (RN-C-08)
- **Flujo:** consigna la conclusión → estado `CERRADA`.

### CU-C-09 · Registrar reconocimiento positivo

Usa `observer_entry` con categoría `POSITIVA`. Alimenta el indicador de clima
escolar y es visible para el acudiente.

### CU-C-10 · Alertas tempranas

- **Actor:** Sistema
- **Flujo:** evalúa periódicamente las reglas activas (reincidencia,
  inasistencia, bajo rendimiento, compromisos incumplidos) y genera la alerta
  con nivel y destinatario.
- **Alternativo A1 — Alerta atendida:** se marca con la acción tomada; no se
  vuelve a generar por el mismo hecho.

## 5. Reglas de negocio

| # | Regla | Validación |
|---|---|---|
| **RN-C-01** | Toda situación tipo II o III **exige** citación al acudiente | Servicio, según `requires_guardian` |
| **RN-C-02** | Toda situación tipo III **exige** escalamiento al comité | Servicio |
| **RN-C-03** | Un caso solo se cierra con todos sus compromisos verificados | Validación al cerrar |
| **RN-C-04** | Un caso escalado no se cierra sin decisión del comité | Validación al cerrar |
| **RN-C-05** | La evidencia confidencial solo se expone con permiso específico | Filtrado en el serializer |
| **RN-C-06** | Una sesión sin quórum no puede registrar decisiones | Validación en la sesión |
| **RN-C-07** | El compromiso vencido sin verificar se marca `INCUMPLIDO` | Comando programado |
| **RN-C-08** | Toda decisión debe citar el artículo del manual de convivencia | Campo obligatorio |
| **RN-C-09** | Toda transición de estado deja historial | Servicio + señal |
| **RN-C-10** | Los umbrales de alerta son parametrizables, nunca fijos en código | `observer_alert_rule` |
| **RN-C-11** | El estudiante y el acudiente ven el caso propio, nunca el de terceros | Filtro por sujeto en el queryset |
| **RN-C-12** | La citación no asistida queda registrada como tal (debido proceso) | Estado `NO_ASISTIO` |

### Máquina de estados del caso

```
   ┌──────────┐  seguimiento  ┌────────────────┐
   │ ABIERTA  │──────────────►│ EN_SEGUIMIENTO │
   └────┬─────┘               └───┬────────┬───┘
        │                         │        │
        │      escalar            │        │ cerrar
        └────────────┬────────────┘        │
                     ▼                     │
          ┌────────────────────┐           │
          │  ESCALADO_COMITE   │───────────┤
          └────────────────────┘  decisión │
                                           ▼
                                    ┌───────────┐
                                    │  CERRADA  │
                                    └───────────┘
      (ANULADA: disponible desde cualquier estado, con motivo y permiso delete)
```

| Desde | Hacia | Acción |
|---|---|---|
| `ABIERTA` | `EN_SEGUIMIENTO`, `ESCALADO_COMITE`, `CERRADA` | `edit` / `approve` |
| `EN_SEGUIMIENTO` | `ESCALADO_COMITE`, `CERRADA` | `edit` / `approve` |
| `ESCALADO_COMITE` | `EN_SEGUIMIENTO`, `CERRADA` | `approve` |
| `CERRADA` | `EN_SEGUIMIENTO` (reapertura motivada) | `approve` |
| cualquiera | `ANULADA` | `delete` |

---

## 6. Integración entre los dos módulos

Una incapacidad aprobada **suprime las alertas tempranas por inasistencia** en
el rango cubierto: el estudiante no puede ser alertado por faltas que están
médicamente justificadas. Es la única dependencia entre ambos módulos y opera
por consulta, sin acoplamiento de código.
