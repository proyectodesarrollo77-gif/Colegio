# Extensión nativa — Incapacidades y Convivencia Escolar

Diseño de integración de dos módulos en PL_SGE bajo el concepto de **extensión
nativa**: se aprovecha la arquitectura, la base de datos, las APIs, el diseño
visual y la seguridad que ya existen.

> ## Hallazgo que define el diseño
>
> **Buena parte de lo solicitado ya está en producción.** `core/observer`
> implementa el núcleo de Convivencia Escolar (caso, tipificación
> Tipo I/II/III, seguimiento, reconocimientos, historial) y `teacher_absence`
> ya registra incapacidades docentes.
>
> Construirlos como módulos nuevos e independientes habría violado sus
> condiciones 4 y 5 —no duplicar información, no crear entidades que ya
> existan— y habría dejado **dos historiales disciplinarios paralelos** en la
> misma base.
>
> Por eso: **Convivencia se extiende sobre `observer`**, e **Incapacidades es
> un módulo nuevo que se integra con** `teacher_absence`, `attendance_record` y
> `student_document`.

---

## Entregables

| # | Documento | Contenido |
|---|---|---|
| 1 | [Análisis de Integración](01_ANALISIS_INTEGRACION.md) | Inventario de solapamiento, reutilización, cambios mínimos, impacto, dependencias, 10 riesgos, estrategia en 11 fases |
| 2 | [Diseño Funcional](02_DISENO_FUNCIONAL.md) | Objetivos, alcance, actores, 18 casos de uso con flujos alternativos, 24 reglas de negocio, máquinas de estado |
| 3 | [Historias de Usuario](03_HISTORIAS_USUARIO.md) | 25 historias con criterios de aceptación Dado/Cuando/Entonces |
| 4 | [Modelo Entidad-Relación](04_MODELO_ENTIDAD_RELACION.md) | Diagramas, cardinalidades, llaves, 38 índices recomendados |
| 5 | [Diccionario de Datos](05_DICCIONARIO_DATOS.md) | 14 tablas, 179 campos con tipo, longitud, obligatoriedad, descripción e índices |
| 6 | [Scripts SQL](../../database/extension/) | [Migración](../../database/extension/10_incapacidades_convivencia.sql) y [rollback](../../database/extension/11_rollback.sql) |
| 7 | [Diseño API REST](06_API_REST.md) | Endpoints, JSON de petición y respuesta, validaciones, códigos HTTP |

## Anexos solicitados

| Anexo | Dónde |
|---|---|
| Documento de roles y permisos | [07_ROLES_Y_PERMISOS.md](07_ROLES_Y_PERMISOS.md) |
| Esquema de la base actual (`schema.sql`) | [`database/02_esquema.sql`](../../database/02_esquema.sql) |
| Diagrama ER existente | [08_ANEXOS_SISTEMA_ACTUAL.md](08_ANEXOS_SISTEMA_ACTUAL.md#2-diagrama-er-existente--zona-de-integración) |
| Estructura de carpetas backend | [08_ANEXOS_SISTEMA_ACTUAL.md](08_ANEXOS_SISTEMA_ACTUAL.md#3-estructura-de-carpetas-del-backend) |
| Estructura de carpetas frontend | [08_ANEXOS_SISTEMA_ACTUAL.md](08_ANEXOS_SISTEMA_ACTUAL.md#4-estructura-de-carpetas-del-frontend) |
| Pantallas del sistema actual | [08_ANEXOS_SISTEMA_ACTUAL.md](08_ANEXOS_SISTEMA_ACTUAL.md#5-pantallas-del-sistema-actual) — inventario verificado de 138 pantallas. **No hay capturas de imagen**: el panel de navegador no está disponible en este entorno. El anexo indica cómo generarlas en dos minutos |

---

## Cumplimiento de las 17 condiciones obligatorias

| # | Condición | Cómo se cumple |
|---|---|---|
| 1 | No modificar la arquitectura principal | Se usan las mismas capas y clases base |
| 2 | No modificar la experiencia actual | Ninguna pantalla existente cambia |
| 3 | No reemplazar componentes | Solo se consumen los existentes |
| 4 | No duplicar información | Estudiantes, docentes, acudientes, asistencia y expediente se referencian |
| 5 | No crear entidades que ya existan | El caso sigue siendo `observer_entry`; la novedad docente sigue siendo `teacher_absence` |
| 6 | No alterar funcionalidades productivas | 0 columnas modificadas, 0 `DROP`, 0 `RENAME` |
| 7 | Compatible con actualizaciones futuras | Extensión por composición, sin monkey-patching |
| 8 | Mismo framework frontend | HTML5 + CSS3 + JS ES6 nativo |
| 9 | Mismo framework backend | Django 5.2 + DRF 3.18 |
| 10 | Mismos componentes visuales | 17 componentes reutilizados, 0 nuevos |
| 11 | Mismas librerías | 0 dependencias nuevas |
| 12 | Mismos estilos y tema | 0 colores nuevos; todo sale de `variables.css` |
| 13 | Responsive actual | Se hereda `responsive.css` sin tocarlo |
| 14 | Convenciones de nomenclatura | Prefijos `incapacity_*` y `observer_*` según el dominio |
| 15 | Auditoría completa | Todas las tablas heredan `BaseModel`; `AuditLog` automático |
| 16 | Sistema de roles actual | Matriz módulo × acción; 4 perfiles nuevos, 14 intactos |
| 17 | Integridad referencial | 41 FK reales; sujeto polimórfico con FK + `CHECK`, no id genérico |

---

## Cifras

| Indicador | Valor |
|---|---|
| Tablas nuevas | 14 |
| Tablas productivas modificadas | **0** |
| Columnas productivas modificadas | **0** |
| Llaves foráneas nuevas | 41 |
| Índices nuevos | 38 |
| Librerías nuevas | **0** |
| Colores nuevos | **0** |
| Módulos de menú nuevos | 18 (128 → 146) |
| Perfiles nuevos | 4 (14 → 18) |
| Casos de uso | 18 |
| Reglas de negocio | 24 |
| Historias de usuario | 25 |

---

## Verificación ejecutada

Los scripts SQL **no son teóricos**: se aplicaron y revirtieron en una base
PostgreSQL real construida desde `02_esquema.sql` + `03_datos_iniciales.sql`.

| Prueba | Resultado |
|---|---|
| Migración sobre base limpia | **OK** — 15 tablas, 85 FK, 76 índices |
| Restricción de sujeto único (3 casos) | **Rechaza** correctamente |
| Fechas invertidas | **Rechaza** |
| Estado y `subject_type` fuera de dominio | **Rechazan** |
| Número de incapacidad duplicado | **Rechaza** |
| Un solo comité `VIGENTE` por año | **Rechaza** el segundo, permite el `DISUELTO` |
| Acta con número repetido en el comité | **Rechaza** |
| Quórum cero y ventana de alerta cero | **Rechazan** |
| Decisión sin artículo del manual | **Rechaza** |
| `ESCALADO_COMITE` cabe en `observer_entry.status` | **Sí** — sin `ALTER TABLE` |
| Rollback: reversión de asistencia | `EXCUSA` → `AUSENTE` **correcto** |
| Rollback: caso escalado | `ESCALADO_COMITE` → `EN_SEGUIMIENTO` **correcto** |
| Rollback: tablas | 172 → 157, **sistema base intacto** |

---

## Estado de la entrega

Lo entregado es el **diseño completo y documentado** más los **scripts SQL
probados**. La implementación del código Django (modelos, servicios,
serializers, ViewSets, plantillas y pruebas) es la fase siguiente y sigue el
plan de 11 fases del Entregable 1.
