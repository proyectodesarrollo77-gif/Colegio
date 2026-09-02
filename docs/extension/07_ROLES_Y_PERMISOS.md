# Anexo — Documento de Roles y Permisos

## 1. Cómo funciona la autorización hoy (sin cambios)

El sistema autoriza por **módulo × acción**. Cada uno de los módulos admite seis
acciones independientes:

`view` (Consultar) · `create` (Crear) · `edit` (Editar) · `delete` (Eliminar) ·
`export` (Exportar) · `approve` (Aprobar)

Se aplica en **tres capas**, y ninguna sustituye a las otras:

| Capa | Mecanismo | Efecto |
|---|---|---|
| Páginas HTML | `ModulePermissionRequiredMixin` | 403 en el servidor |
| API REST | `HasModulePermission` | 403 en el servidor |
| Navegación | Construcción del menú | El módulo no aparece |

> **Ocultar el botón nunca es el control.** La validación de las tres capas es
> de servidor; la interfaz solo refleja el resultado.

Existen además **excepciones individuales** por usuario
(`users_user_module_permission`) que conceden o revocan una acción puntual sin
alterar el perfil. Los módulos nuevos las heredan sin código adicional.

---

## 2. Módulos nuevos en el registro

### Grupo «Bienestar» — Incapacidades

| Código | Nombre | Ruta |
|---|---|---|
| `incapacities` | Incapacidades | — (agrupador) |
| `incapacities.dashboard` | Tablero de Incapacidades | `incapacities:dashboard` |
| `incapacities.registro` | Registro de Incapacidades | `incapacities:registry` |
| `incapacities.aprobacion` | Bandeja de Aprobación | `incapacities:approval` |
| `incapacities.confidencial` | **Información Clínica** | `incapacities:clinical` |
| `incapacities.configuracion` | Tipos de Incapacidad | `incapacities:types` |
| `incapacities.reportes` | Reportes de Ausentismo | `incapacities:reports` |

### Grupo «Convivencia» — Convivencia Escolar

Se suma al grupo que **ya existe**, junto a Observador y Tutoría.

| Código | Nombre | Ruta |
|---|---|---|
| `coexistence` | Convivencia Escolar | — (agrupador) |
| `coexistence.dashboard` | Tablero de Convivencia | `coexistence:dashboard` |
| `coexistence.citaciones` | Citaciones | `coexistence:summons` |
| `coexistence.compromisos` | Compromisos | `coexistence:commitments` |
| `coexistence.comite` | Comité de Convivencia | `coexistence:committee` |
| `coexistence.decisiones` | Decisiones y Actas | `coexistence:decisions` |
| `coexistence.alertas` | Alertas Tempranas | `coexistence:alerts` |
| `coexistence.confidencial` | **Evidencia Reservada** | `coexistence:confidential` |
| `coexistence.configuracion` | Reglas de Alerta | `coexistence:rules` |
| `coexistence.reportes` | Reportes de Convivencia | `coexistence:reports` |

**Total: 18 módulos nuevos** (128 → 146).

> Los submódulos `*.confidencial` **no son pantallas**: son llaves de permiso
> que gobiernan qué campos devuelve la API. Se listan en la matriz para que el
> administrador los conceda de forma explícita y auditable.

---

## 3. Perfiles nuevos

Se agregan **cuatro**. Los 14 actuales no se modifican.

| Código | Nombre | Para quién |
|---|---|---|
| `GESTOR_INCAPACIDADES` | Gestor de Incapacidades | Talento humano / bienestar |
| `SALUD_OCUPACIONAL` | Salud Ocupacional | Enfermería, seguridad y salud en el trabajo |
| `GESTOR_CONVIVENCIA` | Gestor de Convivencia | Coordinación de convivencia |
| `MIEMBRO_COMITE` | Miembro del Comité de Convivencia | Integrantes del comité |

---

## 4. Matriz de permisos

Leyenda: **V** view · **C** create · **E** edit · **D** delete · **X** export ·
**A** approve · **—** sin acceso

### 4.1 Incapacidades

| Perfil | dashboard | registro | aprobación | confidencial | configuración | reportes |
|---|---|---|---|---|---|---|
| `SUPER_ADMIN` | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA |
| `RECTOR` | V X | V X A | V X A | V | V | V X |
| `GESTOR_INCAPACIDADES` | V | VCEDX | V X A | V | VCEDX | V X |
| `SALUD_OCUPACIONAL` | V | V E X | V | **V X** | V | V X |
| `COORDINADOR` | V | V C E X | V X A | — | V | V X |
| `SECRETARIA` | V | V C E X | V | — | V | V X |
| `DOCENTE` | — | V C | — | — | — | — |
| `TUTOR` | — | V | — | — | — | — |
| `ACUDIENTE` | — | V C | — | — | — | — |
| `ESTUDIANTE` | — | V | — | — | — | — |
| `AUDITOR_PAE` | V | V X | V X | — | V | V X |

**Lecturas obligadas de la matriz:**

- Solo `SUPER_ADMIN`, `RECTOR`, `GESTOR_INCAPACIDADES` y `SALUD_OCUPACIONAL`
  ven `confidencial`, es decir, el diagnóstico y el código CIE-10. **Ni siquiera
  el coordinador lo ve**, aunque aprueba (RN-I-10).
- Docente, acudiente y estudiante **crean pero no editan**: registran su
  incapacidad y a partir de ahí la gestiona la institución.
- `ACUDIENTE` y `ESTUDIANTE` solo ven **su propio** registro (filtro de
  queryset, no de permiso).
- Ningún perfil salvo `SUPER_ADMIN` y `GESTOR_INCAPACIDADES` tiene `delete`:
  anular una incapacidad aprobada es una acción restringida.

### 4.2 Convivencia Escolar

| Perfil | dashboard | citaciones | compromisos | comité | decisiones | alertas | confidencial | config. | reportes |
|---|---|---|---|---|---|---|---|---|---|
| `SUPER_ADMIN` | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA | VCEDXA |
| `RECTOR` | V X | V X | V X | VCEDXA | VCEXA | V X | **V** | V | V X |
| `GESTOR_CONVIVENCIA` | V X | VCEDX | VCEDX | VCEX A | VCEX A | VCEX | **V** | VCEX | V X |
| `COORDINADOR` | V X | VCEX | VCEX | V X | VCEX | VCEX | **V** | V | V X |
| `MIEMBRO_COMITE` | V | V | V | V C E X | V C E X A | V | **V** | — | V X |
| `ORIENTACION` | V | V C E | VCEX | V | V | VCEX | **V** | — | V X |
| `TUTOR` | V | VCEX | VCEX | — | V | V | — | — | V X |
| `DOCENTE` | — | V | V | — | — | — | — | — | — |
| `ACUDIENTE` | — | V | V | — | V | — | — | — | — |
| `ESTUDIANTE` | — | V | V | — | V | — | — | — | — |
| `AUDITOR_PAE` | V | V X | V X | V X | V X | V X | — | V | V X |

**Lecturas obligadas:**

- **`approve` sobre `decisiones` lo tienen solo cuatro perfiles**: `SUPER_ADMIN`,
  `RECTOR`, `GESTOR_CONVIVENCIA` y `MIEMBRO_COMITE`. Es lo que hace válido el
  escalamiento al comité.
- `DOCENTE` reporta el caso en el observador (permiso que ya tiene), pero **no
  cita, no decide y no cierra**.
- `ACUDIENTE` y `ESTUDIANTE` ven citaciones, compromisos y decisiones **propias**
  (RN-C-11), y nunca la evidencia reservada.
- `delete` está reservado a `SUPER_ADMIN` y `GESTOR_CONVIVENCIA`: anular un caso
  disciplinario afecta el debido proceso.

### 4.3 Perfiles nuevos sobre los módulos existentes

Los perfiles nuevos necesitan lectura de contexto. Bajo **mínimo privilegio**:

| Perfil | Módulos existentes | Acciones |
|---|---|---|
| `GESTOR_INCAPACIDADES` | `dashboard`, `students`, `teachers`, `attendance` | `view`, `export` |
| `SALUD_OCUPACIONAL` | `dashboard`, `students`, `teachers` | `view` |
| `GESTOR_CONVIVENCIA` | `dashboard`, `observer`, `students`, `attendance`, `tutoring` | `view`, `create`, `edit`, `export` |
| `MIEMBRO_COMITE` | `dashboard`, `observer`, `students` | `view` |

Ninguno recibe acceso a evaluaciones, promoción, usuarios ni configuración del
sistema.

---

## 5. Separación de funciones

Dos controles deliberados, para que aprobar no sea un trámite de una sola persona:

1. **Quien verifica no es quien aprueba.** `SECRETARIA` verifica el soporte
   (`edit`) pero **no tiene `approve`**. La aprobación exige coordinación o
   rectoría.
2. **Quien reporta no decide.** `DOCENTE` crea el caso pero no tiene `approve`
   sobre `decisiones`. La sanción la resuelve el comité.

---

## 6. Datos sensibles de salud (Ley 1581 de 2012)

| Control | Implementación |
|---|---|
| Acceso al diagnóstico | Permiso `incapacities.confidencial`, concedido a 4 perfiles |
| Filtrado | En el **serializer**: los campos no viajan en la respuesta |
| Descarga de soportes | Registrada en `audit_log` con usuario, fecha e IP |
| Soportes marcados confidenciales | `is_confidential = true` por defecto |
| Constancia impresa | Omite el diagnóstico si quien imprime no tiene el permiso |
| Retención | Parametrizable en `configuration_parameter` |

---

## 7. Aplicación de la matriz

Se declara en `DEFAULT_ROLE_MATRIX` (`core/configuration/modules.py`) y se
aplica con los comandos existentes:

```bash
python manage.py seed_roles
python manage.py seed_modules
python manage.py seed_permissions
```

`seed_permissions` resuelve por precedencia **exacto > padre > comodín**, de
modo que basta declarar `"incapacities": [...]` para cubrir todos sus
submódulos, y luego afinar los que lo requieran:

```python
"SALUD_OCUPACIONAL": {
    "dashboard": ["view"],
    "incapacities": ["view"],                          # todos los submodulos
    "incapacities.registro": ["view", "edit", "export"],
    "incapacities.confidencial": ["view", "export"],   # la excepcion clave
    "students": ["view"],
    "teachers": ["view"],
},
```

---

## 8. Verificación exigible

Estas pruebas deben pasar antes de dar por buena la matriz:

1. Cada perfil sin `view` sobre un módulo recibe **403** en la página **y** en la API.
2. Un `COORDINADOR` que consulta una incapacidad **no** recibe `diagnosis` en el JSON.
3. Un `ACUDIENTE` que pide el caso de otro estudiante recibe **404**.
4. Un `DOCENTE` que intenta `POST /api/observer-decisions/` recibe **403**.
5. Una `SECRETARIA` que intenta `transition` a `APROBADA` recibe **403**.
6. Un usuario normal que intenta borrar una entrada de la bitácora recibe **403/405**.
7. El menú lateral de cada perfil muestra exactamente los módulos con `view`.
