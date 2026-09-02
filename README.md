# KINDORA — Aplicación de Instituciones Académicas

> Nombre técnico del proyecto: `PL_SGE`. **KINDORA** es el nombre visible del producto.

Plataforma web modular, segura y responsive para centralizar los procesos académicos,
administrativos, disciplinarios, documentales y de comunicación de una institución educativa.

| | |
|---|---|
| **Backend** | Python 3.12 · Django 5.2 · Django REST Framework 3.18 |
| **Frontend** | HTML5 · CSS3 (design system propio) · JavaScript ES6+ (módulos nativos, sin frameworks) |
| **Base de datos** | PostgreSQL 14+ |
| **Autenticación** | Sesión Django · JWT (SimpleJWT) · TOTP / Google Authenticator (RFC 6238) |
| **Arquitectura** | MVT + API REST · modular por dominio · permisos por módulo y acción |

---

## 1. Puesta en marcha

### 1.1 Requisitos

- Python 3.11 o superior
- PostgreSQL 14 o superior
- pip / virtualenv

### 1.2 Instalación

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 1.3 Base de datos

```bash
psql -U postgres -c "CREATE DATABASE pl_sge WITH ENCODING 'UTF8';"
```

Copie `.env.example` a `.env` y ajuste las credenciales, o exporte las variables:

```bash
export DB_NAME=pl_sge DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5432
```

> Para desarrollo sin PostgreSQL, `DB_ENGINE=sqlite` usa `database/pl_sge.sqlite3`.

### 1.4 Migraciones e inicialización

```bash
python manage.py migrate
python manage.py initialize_platform
python manage.py seed_pae
```

`initialize_platform` deja la plataforma operativa: perfiles, módulos, matriz de permisos,
institución, año lectivo con periodos, escala valorativa, niveles, grados, grupos, áreas,
asignaturas, parámetros del sistema, encabezado de reportes y catálogo de reportes.

Opcionalmente, cargue datos de demostración (docentes, estudiantes, matrículas, notas,
asistencia, agenda, observador, énfasis y proceso electoral):

```bash
python manage.py seed_demo --students-per-group 21 --teachers 14
python manage.py seed_pae_demo
```

### 1.5 Ejecución

```bash
python manage.py runserver
```

Abra `http://localhost:8000/`.

### 1.5.1 Ejecutables (alternativa sin línea de comandos)

En la raíz del proyecto hay lanzadores listos para usar:

| Windows | Linux / macOS | Función |
|---|---|---|
| `PL_SGE.bat` | — | Menú principal con las 14 operaciones |
| `INSTALAR.bat` | `./instalar.sh` | Instalación completa (entorno, dependencias, base de datos) |
| `INICIAR.bat` | `./iniciar.sh` | Arranca el servidor y abre el navegador |
| — | `./datos_demo.sh` | Carga datos de demostración |
| — | `./respaldar_bd.sh` | Respaldo de la base de datos |

`INICIAR.bat 8080` arranca en otro puerto. Ver la guía completa en
[`COMO_INGRESAR.md`](COMO_INGRESAR.md) y, para trasladar la plataforma a otro
computador, [`docs/INSTALAR_EN_OTRO_EQUIPO.md`](docs/INSTALAR_EN_OTRO_EQUIPO.md).

Los scripts auxiliares viven en `scripts/`:

| Script | Función |
|---|---|
| `scripts/instalar.bat` | Instalación paso a paso con verificación |
| `scripts/datos_demo.bat` | Datos de demostración |
| `scripts/detener.bat` | Detiene el servidor (acepta puerto) |
| `scripts/crear_admin.bat` | Crea otro administrador |
| `scripts/respaldar_bd.bat` | Respaldo con marca de tiempo |
| `scripts/restaurar_bd.bat` | Restauración desde respaldo |
| `scripts/reiniciar_bd.bat` | Reinicio total (pide confirmación) |
| `scripts/verificar.bat` | Verificación integral de la instalación |
| `scripts/migrar.bat` | Migraciones pendientes |
| `scripts/estaticos.bat` | `collectstatic` para producción |
| `scripts/consola.bat` | Consola interactiva de Django |
| `scripts/pae.bat` | Módulo PAE: configuración, demostración, indicadores y pruebas |
| `scripts/generar_sql.bat` | Regenera los scripts SQL de `database/` |

### 1.6 Credenciales iniciales

| Campo | Valor |
|---|---|
| Nombre | Super Admin |
| Rol | `SUPER_ADMIN` |
| Email | `admin@datly.local` |
| Contraseña | `Admin123*` |
| Estado | Activo |

### 1.7 Usuarios de demostración

Tras ejecutar `seed_demo` quedan disponibles cuentas para recorrer la plataforma
desde cada perfil (contraseña común: `Demo123*`):

| Perfil | Correo | Módulos visibles |
|---|---|---|
| `RECTOR` | `rector@datly.local` | 105 |
| `COORDINADOR` | `coordinador@datly.local` | 84 |
| `SECRETARIA` | `secretaria@datly.local` | 36 |
| `DOCENTE` | `docente@datly.local` | 49 |
| `TUTOR` | `tutor@datly.local` | 33 |
| `ESTUDIANTE` | `estudiante@datly.local` | 14 |
| `ACUDIENTE` | `acudiente@datly.local` | 13 |

Los seis perfiles del PAE (`RESPONSABLE_PAE`, `COORDINADOR_SEDE`, `OPERADOR_PAE`,
`SUPERVISOR_PAE`, `AUDITOR_PAE`, `CONSULTA_PAE`) quedan creados con su matriz de
permisos; para probarlos, asigne el perfil a un usuario desde
**Usuarios › Gestión de Usuarios**.

---

## 2. Estructura del proyecto

```
PL_SGE/
├── manage.py
├── requirements.txt
├── smoke_test.py               Prueba de humo de todas las rutas y endpoints
│
├── config/                     Núcleo de configuración e infraestructura
│   ├── settings.py             Configuración completa (PostgreSQL, DRF, JWT, seguridad)
│   ├── urls.py                 Enrutamiento maestro
│   ├── api.py                  Router REST agregador de todos los módulos
│   ├── permissions.py          Motor de permisos por módulo y acción
│   ├── viewsets.py             BaseModelViewSet: auditoría, soft-delete, exportación
│   ├── resource.py             Páginas CRUD declarativas (ResourceView)
│   ├── models_base.py          Modelos abstractos (auditoría, borrado lógico, catálogo)
│   ├── pagination.py           Paginación estándar
│   ├── exceptions.py           Manejo homogéneo de errores de la API
│   ├── errors.py               Handlers 400 / 403 / 404 / 500
│   ├── wsgi.py · asgi.py
│
├── core/                       Módulos funcionales
│   ├── authentication/         Login, 2FA TOTP, recuperación, sesiones, trazabilidad
│   ├── dashboard/              Indicadores, alertas y accesos rápidos por rol
│   ├── configuration/          Perfiles, encabezado de reportes, décimas, parámetros
│   ├── users/                  Usuarios, roles, módulos, matriz de permisos, credenciales
│   ├── institutions/           Institución, sedes, jornadas, calendario institucional
│   ├── academic/               Directiva: año lectivo, periodos, escalas, áreas, grupos
│   ├── students/               Registro, matrícula, admisiones, hoja de vida, certificados
│   ├── teachers/               Planta docente, asignaciones, horarios, carga académica
│   ├── evaluations/            Notas, juicios, cualitativa, preescolar, bilingüe
│   ├── attendance/             Registro y consolidado de asistencia
│   ├── tutoring/               Tutores, juicios, convivencia, bloqueo de boletín
│   ├── observer/               Observador del estudiante e historial disciplinario
│   ├── promotion/              Cierre académico, promoción y boletines
│   ├── recoveries/             Planes de recuperación y actividades complementarias
│   ├── emphases/               Énfasis, apertura de grupos y matrículas
│   ├── documents/              Plantillas documentales e impresión
│   ├── reports/                Catálogo de reportes y estadísticas
│   ├── agenda/                 Calendario institucional, actividades y circulares
│   ├── classroom/              Aula virtual: cursos, material, actividades, seguimiento
│   ├── elections/              Gobierno escolar: configuración, votación y resultados
│   ├── extensions/             Formularios dinámicos y espacios virtuales
│   ├── notifications/          Centro de notificaciones
│   ├── audit/                  Bitácora de auditoría y middleware de trazabilidad
│   └── pae/                    Programa de Alimentación Escolar (22 submódulos)
│
├── templates/
│   ├── layouts/                base · auth · dashboard
│   ├── partials/               resource_page · print_header · print_toolbar
│   └── <módulo>/               Vistas especializadas de cada módulo
│
├── static/
│   ├── css/                    variables · app · components · responsive
│   └── js/                     app · auth · dashboard · modules/*
│
├── fixtures/                   roles.json · permissions.json · super_admin.json
├── docs/                       CREDENCIALES_INSTITUCIONES.md · INSTALAR_EN_OTRO_EQUIPO.md · PAE_*.md
├── media/                      Archivos cargados por los usuarios
├── logs/                       Rotación de logs de la aplicación
└── database/                   Respaldos y scripts SQL
```

---

## 3. Seguridad

### 3.1 Autenticación

- Inicio de sesión por **correo electrónico o nombre de usuario**.
- Bloqueo temporal tras `MAX_LOGIN_ATTEMPTS` intentos fallidos (por defecto 5 / 15 minutos).
- Cambio de contraseña obligatorio en el primer ingreso.
- Recuperación de contraseña con token de un solo uso y vencimiento configurable.
- Verificación de correo electrónico.
- Cierre automático de sesión por inactividad (`SESSION_IDLE_TIMEOUT`).
- Cierre remoto de sesiones desde *Mi Perfil* y desde *Auditoría › Sesiones activas*.

### 3.2 Doble factor (Google Authenticator)

Implementación **TOTP RFC 6238** sin dependencias externas (`core/authentication/models.py`):

- Secreto Base32 de 160 bits, código QR `otpauth://` renderizado en SVG.
- Ventana de tolerancia ±30 s y protección contra reutilización del mismo contador.
- 8 códigos de recuperación de un solo uso, regenerables.
- 2FA opcional por usuario u **obligatorio** por perfil (`two_factor_enforced`).

### 3.3 API REST

- JWT con rotación y *blacklist* de refresh tokens.
- *Throttling* por usuario, anónimo y específico de login.
- `SessionAuthentication` para el frontend y `JWTAuthentication` para integraciones.

### 3.4 Auditoría

Toda operación de escritura queda registrada con usuario, perfil, módulo, entidad, IP,
navegador, ruta, método, código HTTP y duración (`core/audit`).

---

## 4. Roles y permisos

### 4.1 Perfiles iniciales

**Académicos:** `SUPER_ADMIN` · `RECTOR` · `COORDINADOR` · `SECRETARIA` ·
`DOCENTE` · `TUTOR` · `ESTUDIANTE` · `ACUDIENTE`

**Programa de Alimentación Escolar:** `RESPONSABLE_PAE` · `COORDINADOR_SEDE` ·
`OPERADOR_PAE` · `SUPERVISOR_PAE` · `AUDITOR_PAE` · `CONSULTA_PAE`

### 4.2 Acciones por módulo

Cada uno de los **128 módulos y submódulos** admite seis acciones independientes:

`view` (Consultar) · `create` (Crear) · `edit` (Editar) · `delete` (Eliminar) ·
`export` (Exportar) · `approve` (Aprobar)

La matriz se administra en **Configuración › Acceso de Perfiles** y se aplica en tres capas:

| Capa | Mecanismo |
|---|---|
| Vistas HTML | `ModulePermissionRequiredMixin` |
| API REST | `HasModulePermission` (mapea método HTTP → acción) |
| Navegación | El menú lateral solo muestra los módulos con permiso `view` |

Además existen **excepciones individuales** por usuario (`UserModulePermission`) que conceden
o revocan una acción puntual sin alterar el perfil.

---

## 5. Módulos funcionales

| # | Módulo | Submódulos |
|---|---|---|
| 1 | **Login y Seguridad** | Inicio de sesión, recuperación, MFA, auditoría, roles, permisos |
| 2 | **Dashboard** | Indicadores, accesos rápidos, notificaciones, estadísticas, alertas |
| 3 | **Configuración** | Acceso de Perfiles, Encabezado de Reportes, Décimas de Notas, Parámetros |
| 4 | **Usuarios** | Gestión, Usuarios de Estudiantes, Coordinadores, Certificados de credenciales, Reporte de Accesos, Google Authenticator |
| 5 | **Directiva** | Año Lectivo, Periodo, Escala Valorativa, Dimensiones, Áreas, Asignaturas, Niveles, Grados, Grupos, Procesos, Juicios, Convivencia, Propósitos |
| 6 | **Estudiantes** | Registro, Matrícula, Consulta, Promoción, Certificados, Hoja de Vida, Listados, Admisiones, Inscripciones, Acudientes |
| 7 | **Docentes** | Registro, Asignaturas, Horarios, Carga Académica, Procesos Académicos |
| 8 | **Evaluaciones** | Asignación de Notas, Juicios Valorativos, Evaluación Cualitativa, Propósitos Preescolar, Módulo Bilingüe |
| 9 | **Asistencia** | Registro diario, Reporte de inasistencias |
| 10 | **Recuperaciones** | Planes, Actividades complementarias, Recuperación bilingüe, Resultados |
| 11 | **Promoción y Boletín Final** | Cierre académico, Promoción estudiantil, Boletines |
| 12 | **Énfasis y Disciplinas** | Catálogo, Apertura de grupos, Matrículas |
| 13 | **Tutoría** | Tutores, Juicios, Convivencia, Reportes, Bloqueo de Boletín |
| 14 | **Observador** | Tipos de observación, Registro, Historial estudiantil |
| 15 | **Agenda Virtual** | Calendario, Actividades, Correos y circulares |
| 16 | **Aula Virtual** | Cursos, Material, Actividades, Seguimiento |
| 17 | **Elecciones** | Configuración electoral, Votación digital, Resultados |
| 18 | **Documentos Institucionales** | Configuración documental, Impresión |
| 19 | **Reportes** | Académicos, Estadísticos, Administrativos (PDF / Excel / CSV) |
| 20 | **Extensiones** | Formularios dinámicos, Espacios virtuales |
| 21 | **Mi Perfil** | Datos personales, Contraseña, Seguridad 2FA, Sesiones, Actividad |
| 22 | **Auditoría** | Bitácora de acciones, Sesiones activas |
| 23 | **PAE** | Dashboard, Configuración, Diagnóstico de Sedes, Priorización, Beneficiarios, Planeación, Ciclos de Menú, Operadores, Contratos, Programación, Entregas Diarias, Control de Calidad, Visitas, Novedades, Mejoramiento, PQRS, Participación Ciudadana, Documentos, Evidencias, Indicadores, Informes, Auditoría del PAE |

### 5.1 Programa de Alimentación Escolar

Módulo de gestión integral del PAE construido **sobre** la plataforma, no al
lado de ella: la vigencia se apoya en el año lectivo, los beneficiarios
referencian a los estudiantes y sus matrículas, y las sedes y jornadas provienen
de la institución. No duplica ninguna tabla existente.

| Aspecto | Detalle |
|---|---|
| Tablas | 39 (`pae_*`), todas con borrado lógico y trazabilidad |
| Reglas de negocio | 12, centralizadas en `core/pae/services.py` |
| Perfiles | 6 propios, con alcance por sede |
| Parametrización | Los valores normativos son configuración editable, no código |
| Importación | CSV y XLSX con reporte de errores por fila y columna |
| Pruebas | 177 casos |

Documentación: [`docs/PAE_ARQUITECTURA.md`](docs/PAE_ARQUITECTURA.md) (técnica) y
[`docs/PAE_MANUAL.md`](docs/PAE_MANUAL.md) (funcional).

---

## 6. Motor académico

### 6.1 Consolidación de notas (`core/evaluations/services.py`)

```
Procesos del docente  →  promedio ponderado por peso
        ↓  política de décimas (Configuración › Décimas de Notas)
Nota de asignatura del periodo  →  desempeño según escala valorativa
        ↓  promedio por área (por intensidad horaria o por peso)
Nota de área  →  boletín  →  promedio general  →  puesto en el grupo
```

- La nota de recuperación reemplaza la del periodo solo si es mayor.
- El redondeo admite cuatro políticas: aproximación normal, truncar, aproximar desde una
  décima específica, o sin aproximación.

### 6.2 Promoción (`core/promotion/services.py`)

| Resultado | Condición |
|---|---|
| Promovido | Sin áreas ni asignaturas perdidas |
| Promovido con compromiso | Hasta 1 área y 2 asignaturas perdidas |
| Pendiente de recuperación | Casos intermedios |
| No promovido | Más de 2 asignaturas o más de 2 áreas perdidas |
| Graduado | Aprueba el grado marcado como grado de graduación |

El cierre anual calcula además el puesto por grupo y el cuadro de honor.

---

## 7. API REST

Base: `/api/`

### 7.1 Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/auth/login/` | Login con sesión + emisión de JWT |
| `POST` | `/api/auth/logout/` | Cierre de sesión y blacklist del refresh |
| `GET` | `/api/auth/me/` | Perfil y permisos del usuario autenticado |
| `POST` | `/api/token/` | Obtención de par de tokens JWT |
| `POST` | `/api/token/refresh/` | Renovación del access token |
| `GET` `POST` `DELETE` | `/api/auth/2fa/` | Alta, confirmación y baja del segundo factor |
| `POST` | `/api/auth/password-reset/` | Solicitud de recuperación |
| `POST` | `/api/auth/password-change/` | Cambio de contraseña autenticado |

### 7.2 Procesos especializados

| Endpoint | Descripción |
|---|---|
| `GET/POST /api/grade-sheet/` | Planilla de digitación de notas (lectura y guardado masivo) |
| `GET/POST /api/attendance-sheet/` | Planilla diaria de asistencia |
| `GET /api/dashboard/` | Indicadores, gráficas, alertas y accesos rápidos |
| `GET /api/statistics/academic/` | Estadísticas académicas consolidadas |
| `GET /api/statistics/administrative/` | Estadísticas administrativas y de seguridad |
| `POST /api/closing-processes/run/` | Ejecución del cierre académico |
| `POST /api/report-cards/generate/` | Generación de boletines por grupo |
| `POST /api/elections/cast-vote/` | Registro del voto digital |

### 7.3 Recursos CRUD

Más de **100 recursos** REST con el mismo contrato:

```
GET    /api/<recurso>/                 Listado paginado, búsqueda, filtros y ordenamiento
POST   /api/<recurso>/                 Creación
GET    /api/<recurso>/{id}/            Detalle
PATCH  /api/<recurso>/{id}/            Actualización parcial
DELETE /api/<recurso>/{id}/            Borrado lógico
GET    /api/<recurso>/export/?format=xlsx|csv
GET    /api/<recurso>/options/         Pares id/label para selects
GET    /api/<recurso>/stats/           Totales y estado
POST   /api/<recurso>/{id}/approve/    Aprobación (donde aplica)
```

Parámetros comunes: `page`, `page_size`, `search`, `ordering`, `only_active`, `include_deleted`.

---

## 8. Frontend

### 8.1 Sistema de diseño

Inspirado en Linear, Stripe, Vercel, Clerk y shadcn/ui. Sin dependencias externas
(solo la fuente Inter desde Google Fonts).

- `static/css/variables.css` — tokens de color, tipografía, espaciado, sombras, radios y
  animación, con **tema claro y oscuro** completos.
- `static/css/app.css` — reset, layouts de autenticación y dashboard, utilidades.
- `static/css/components.css` — botones, formularios, tarjetas, tablas, drawer, modal,
  dropdown, tabs, toasts, timeline, matriz de permisos, planilla de notas, calendario,
  gráficas y hojas de impresión.
- `static/css/responsive.css` — breakpoints 1440 / 1280 / 1024 / 900 / 768 / 560, con
  conversión de tablas a tarjetas en móvil y soporte de `prefers-reduced-motion`.

### 8.2 JavaScript

| Archivo | Responsabilidad |
|---|---|
| `js/app.js` | Cliente HTTP, toasts, drawer, modal, dropdowns, tabs, tema, sidebar, atajos |
| `js/auth.js` | Fortaleza de contraseña, campos OTP, copiar secreto 2FA |
| `js/dashboard.js` | KPIs, alertas, accesos rápidos, paneles por rol |
| `js/modules/crud.js` | Motor genérico de tablas y formularios contra la API |
| `js/modules/charts.js` | Gráficas SVG nativas: línea, área, barras, dona, sparkline |
| `js/modules/grades.js` | Planilla de notas con navegación por teclado y guardado masivo |
| `js/modules/attendance.js` | Planilla de asistencia |
| `js/modules/permissions.js` | Matriz de permisos por perfil |
| `js/modules/calendar.js` | Calendario institucional |
| `js/modules/elections.js` | Tarjetón de votación y resultados |

### 8.3 Páginas de recurso declarativas

Cada submódulo CRUD se declara en Python; la interfaz se construye sola:

```python
class SubjectView(ResourceView):
    module_code = "academic.subjects"
    title = "Asignaturas"
    endpoint = "/api/subjects/"
    columns = [column("name", "Asignatura"), column("area_name", "Área", type="badge")]
    form_fields = [remote("area", "Área", AREA_OPTIONS, required=True),
                   field("name", "Nombre", required=True)]
```

Se obtienen tabla con búsqueda, filtros, ordenamiento, paginación, formulario lateral,
validación de errores del backend, exportación e impresión — respetando los permisos del perfil.

---

## 9. Comandos de gestión

```bash
python manage.py initialize_platform   # Inicialización completa
python manage.py seed_roles            # Perfiles institucionales
python manage.py seed_modules          # Sincroniza el registro de módulos
python manage.py seed_permissions      # Matriz de permisos por defecto (--reset)
python manage.py seed_demo             # Datos de demostración académicos
python manage.py seed_instituciones    # Instituciones educativas de prueba
python manage.py seed_pae              # Configuración base del PAE
python manage.py seed_pae_demo         # Datos de demostración del PAE
python scripts/generar_sql.py          # Regenera los scripts SQL de database/
python manage.py test core.pae         # Pruebas del módulo PAE
python smoke_test.py                   # Verifica todas las rutas y endpoints
```

### Fixtures

```bash
python manage.py loaddata fixtures/roles.json
python manage.py loaddata fixtures/permissions.json
python manage.py loaddata fixtures/super_admin.json
```

---

## 10. Despliegue en producción

```bash
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(64))')"
export DJANGO_ALLOWED_HOSTS=midominio.edu.co
export SECURE_SSL_REDIRECT=True

python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Con `DEBUG=False` se activan automáticamente HSTS, cookies seguras, `X-Frame-Options: DENY`,
`SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY` y el almacenamiento comprimido de
estáticos con WhiteNoise.

---

## 11. Verificación

`smoke_test.py` recorre autenticado las **101 páginas HTML** y los **101 endpoints REST**
principales y reporta el estado de cada uno:

```bash
python smoke_test.py
# RESULTADO: todas las rutas respondieron correctamente
```
