# Base de datos — PL_SGE

Scripts SQL de la **Plataforma Web Integral de Gestión Académica Institucional**.

| Archivo | Contenido |
|---|---|
| `01_crear_base_datos.sql` | Crea el rol `pl_sge_app` y la base de datos `pl_sge` |
| `02_esquema.sql` | Esquema completo: **157 tablas · 1.593 índices · 785 llaves foráneas** |
| `03_datos_iniciales.sql` | 14 perfiles, 128 módulos, 671 permisos, institución, estructura académica, configuración del PAE y Super Admin |
| `04_verificacion.sql` | Consulta de comprobación de la instalación |
| `99_reiniciar.sql` | Elimina y recrea la base vacía (**irreversible**) |
| `../scripts/generar_sql.py` | Regenera `02`, `03` y `04` desde una base recién migrada |
| `respaldos/` | Carpeta donde se guardan los respaldos `.backup` |

---

## 1. Instalación desde los scripts SQL

Requiere PostgreSQL 14 o superior con `psql` disponible en el `PATH`.

```bash
psql -U postgres -d postgres -f 01_crear_base_datos.sql
psql -U postgres -d pl_sge   -f 02_esquema.sql
psql -U postgres -d pl_sge   -f 03_datos_iniciales.sql
psql -U postgres -d pl_sge   -f 04_verificacion.sql
```

En Windows, si `psql` no está en el `PATH`:

```bat
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d postgres -f 01_crear_base_datos.sql
```

### Alternativa recomendada

La misma base se construye desde Django, que además mantiene el historial de
migraciones sincronizado:

```bash
python manage.py migrate
python manage.py initialize_platform
```

Ambas rutas producen exactamente el mismo esquema: `02_esquema.sql` se generó con
`pg_dump` a partir de una base migrada con Django, e incluye la tabla
`django_migrations` con las 78 migraciones aplicadas, de modo que después de
restaurar los scripts SQL `python manage.py migrate` no encuentra nada pendiente.

---

## 2. Qué incluye `03_datos_iniciales.sql`

| Elemento | Cantidad |
|---|---|
| Perfiles institucionales | 14 (8 académicos `SUPER_ADMIN` … `ACUDIENTE` + 6 del PAE) |
| Módulos y submódulos | 128 (105 académicos + 23 del PAE) |
| Permisos por perfil | 671 |
| Institución | 1 (con sede principal y 3 jornadas) |
| Año lectivo | 1 con 4 periodos |
| Escala valorativa | 1 con 4 niveles de desempeño |
| Dimensiones valorativas | 3 |
| Niveles educativos | 4 (Preescolar → Media) |
| Grados | 12 (Transición → Once) |
| Grupos | 24 |
| Áreas / Asignaturas | 10 / 16 |
| Ítems de convivencia | 5 |
| Tipos de observación | 6 |
| Parámetros del sistema | 10 |
| Catálogo de reportes | 14 |
| Normativa del PAE | 2 versiones (estado `POR_VALIDAR`) |
| Catálogos parametrizables del PAE | 85 elementos en 12 catálogos |
| Modalidades / tipos de complemento | 3 / 6 |
| Listas de verificación del PAE | 3 con 26 criterios |
| Usuario Super Admin | `admin@datly.local` / `Admin123*` |

> El script desactiva temporalmente los disparadores
> (`SET session_replication_role = 'replica'`) porque `users_user` tiene llaves
> foráneas circulares hacia sí misma (`created_by_id`, `updated_by_id`).

---

## 3. Datos de demostración

No se distribuyen como SQL porque dependen del año lectivo vigente. Se generan con:

```bash
python manage.py seed_demo --students-per-group 21 --teachers 14
python manage.py seed_pae_demo
```

`seed_demo` produce 504 estudiantes, 14 docentes, 384 asignaciones académicas, notas
de proceso, asistencia, agenda, observador, énfasis, un proceso electoral y una cuenta
de acceso por cada perfil (contraseña `Demo123*`).

`seed_pae_demo` añade la operación del programa sobre esos mismos estudiantes —no crea
estudiantes nuevos—: 3 sedes, 350 beneficiarios, un operador, un contrato, 3 planes,
un ciclo de menú de 5 días, 120 programaciones con sus entregas, novedades, visitas
con hallazgos, planes de mejoramiento, PQRS, acta de participación, documentos e
indicadores. Toda la información es ficticia.

---

## 4. Respaldo y restauración

Desde el menú `PL_SGE.bat` (opciones 6 y 7) o por línea de comandos:

```bash
python scripts/respaldar_bd.py             # genera database/respaldos/pl_sge_AAAAMMDD_HHMMSS.backup
python scripts/respaldar_bd.py --listar    # lista los respaldos existentes
python scripts/restaurar_bd.py             # selección interactiva
python scripts/restaurar_bd.py --ultimo    # restaura el más reciente
```

Los scripts detectan automáticamente la versión de PostgreSQL del servidor y usan
el `pg_dump` / `pg_restore` de esa misma versión, evitando advertencias de
compatibilidad entre versiones.

Equivalente manual:

```bash
pg_dump  -U postgres -d pl_sge -Fc --no-owner --no-privileges -f respaldo.backup
pg_restore -U postgres -d pl_sge --clean --if-exists --no-owner --no-privileges respaldo.backup
```

---

## 5. Reinicio total

**Elimina toda la información de forma irreversible.** Genere un respaldo antes.

```bash
psql -U postgres -d postgres -f 99_reiniciar.sql
psql -U postgres -d pl_sge   -f 02_esquema.sql
psql -U postgres -d pl_sge   -f 03_datos_iniciales.sql
```

O desde el menú: `PL_SGE.bat` → opción **8**.

---

## 6. Regeneración de los scripts

Los archivos `02`, `03` y `04` no se editan a mano: se generan de una base recién
migrada, de modo que nunca queden desfasados respecto de las migraciones.

```bash
python scripts/generar_sql.py
```

El comando crea una base temporal, aplica `migrate`, `initialize_platform` y
`seed_pae`, vuelca el resultado y elimina la base temporal.

---

## 7. Modelo de datos

Las 157 tablas se agrupan por dominio con el prefijo del módulo:

| Prefijo | Dominio |
|---|---|
| `users_*` | Usuarios, roles, módulos, matriz de permisos, credenciales |
| `auth_*` | 2FA, tokens de seguridad, intentos de acceso, sesiones |
| `institution*` | Institución, sedes, jornadas, calendario |
| `configuration_*` | Encabezado de reportes, décimas de notas, parámetros |
| `academic_*` | Año lectivo, periodos, escalas, niveles, grados, grupos, áreas, asignaturas |
| `student*` | Estudiantes, acudientes, matrículas, admisiones, documentos, certificados |
| `teacher*` | Docentes, asignaciones, horarios, procesos, novedades |
| `evaluation_*` | Notas de proceso, de asignatura y de área, juicios, bilingüe |
| `attendance_*` | Sesiones, registros y consolidados de asistencia |
| `tutoring_*` | Tutores, juicios, convivencia, bloqueo de boletín |
| `observer_*` | Tipologías, anotaciones y seguimientos |
| `promotion_*` | Cierres, promoción, boletines, comisiones |
| `recovery_*` | Planes, actividades, inscripciones y entregas |
| `emphasis*` | Énfasis, grupos y matrículas |
| `document_*` | Plantillas y documentos emitidos |
| `report_*` | Catálogo, ejecuciones e indicadores |
| `agenda_*` | Eventos, actividades y circulares |
| `classroom_*` | Cursos, unidades, materiales, actividades, entregas, progreso |
| `election*` | Procesos, cargos, candidatos, votos, censo, resultados |
| `extension_*` | Formularios, campos, respuestas y espacios virtuales |
| `notification` | Centro de notificaciones |
| `audit_log` | Bitácora de auditoría |
| `pae_*` | Programa de Alimentación Escolar (39 tablas) |

### Programa de Alimentación Escolar

Las 39 tablas `pae_*` se apoyan en las que ya existen en lugar de duplicarlas:
`pae_vigencia` referencia `academic_school_year`, `pae_beneficiario` referencia
`student` y `student_enrollment`, y las sedes y jornadas provienen de
`institution_campus` e `institution_shift`. `pae_catalogo` concentra en una sola
tabla las doce listas parametrizables del programa mediante la columna
`catalog_type`, y `pae_normativa` guarda la versión normativa bajo la cual se
produjo cada registro.

Todas las tablas de dominio comparten las columnas de trazabilidad
`created_at`, `updated_at`, `created_by_id`, `updated_by_id`,
`deleted_at`, `deleted_by_id`, `is_active` y `uuid`: el borrado es **lógico**
y cada registro conserva quién lo creó y modificó.
