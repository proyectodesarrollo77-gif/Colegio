# Cómo ingresar a PL_SGE

Guía rápida de acceso a la **Plataforma Web Integral de Gestión Académica Institucional**.

---

> ¿Va a instalar la plataforma en **otro computador**? Siga
> [`docs/INSTALAR_EN_OTRO_EQUIPO.md`](docs/INSTALAR_EN_OTRO_EQUIPO.md).
>
> ¿Necesita las credenciales de **cada institución**? Están en
> [`docs/CREDENCIALES_INSTITUCIONES.md`](docs/CREDENCIALES_INSTITUCIONES.md).

## 1. Ubicación del proyecto

```
D:\Colegios_2026\PL_SGE\
```

Todos los ejecutables están en esa carpeta.

---

## 2. Iniciar la plataforma

### Opción A — Doble clic (recomendada)

| Archivo | Qué hace |
|---|---|
| **`PL_SGE.bat`** | Menú principal con todas las operaciones (incluida la opción **13** del PAE) |
| **`INSTALAR.bat`** | Instalación completa (solo la primera vez) |
| **`INICIAR.bat`** | Arranca el servidor y abre el navegador |

Primera vez:

1. Doble clic en **`INSTALAR.bat`** → espere a que termine.
2. Doble clic en **`INICIAR.bat`** → el navegador se abre solo.

Uso diario: solo **`INICIAR.bat`**.

### Opción B — Línea de comandos

```bat
cd D:\Colegios_2026\PL_SGE
.venv\Scripts\python.exe manage.py runserver
```

### Opción C — Linux / macOS

```bash
cd /ruta/a/PL_SGE
./instalar.sh     # solo la primera vez
./iniciar.sh
```

---

## 3. Dirección de acceso

| Destino | Dirección |
|---|---|
| Inicio de sesión | `http://localhost:8000/auth/login/` |
| Panel principal | `http://localhost:8000/dashboard/` |
| Administración técnica | `http://localhost:8000/admin/` |
| API REST | `http://localhost:8000/api/` |
| Estado del servicio | `http://localhost:8000/healthz` |

Para usar otro puerto: `INICIAR.bat 8080`

Desde otro equipo de la red local, reemplace `localhost` por la IP del servidor
(por ejemplo `http://192.168.1.50:8000/`) y agregue esa IP a `DJANGO_ALLOWED_HOSTS`
en el archivo `.env`.

---

## 4. Credenciales

### Administrador principal

| Campo | Valor |
|---|---|
| **Correo** | `admin@datly.local` |
| **Contraseña** | `Admin123*` |
| **Perfil** | `SUPER_ADMIN` — acceso a los 128 módulos |

> Puede ingresar con el correo completo o con el nombre de usuario `admin`.

### Cuentas de demostración

Disponibles después de ejecutar la carga de datos de demostración
(opción **2** del menú). Contraseña común: **`Demo123*`**

| Perfil | Correo | Módulos | Puede hacer |
|---|---|---|---|
| Rector | `rector@datly.local` | 128 | Todo, con énfasis en aprobación |
| Coordinador | `coordinador@datly.local` | 107 | Gestión académica, convivencia y consulta del PAE |
| Secretaria | `secretaria@datly.local` | 36 | Estudiantes, usuarios y documentos |
| Docente | `docente@datly.local` | 49 | Notas, asistencia, aula virtual |
| Tutor | `tutor@datly.local` | 33 | Tutoría, convivencia, observador |
| Estudiante | `estudiante@datly.local` | 14 | Consulta de notas, agenda, aula |
| Acudiente | `acudiente@datly.local` | 13 | Seguimiento del estudiante |

### Perfiles del Programa de Alimentación Escolar

Se crean con la plataforma, sin cuenta de demostración asociada. Para probarlos,
asigne el perfil a un usuario en **Usuarios › Gestión de Usuarios**.

| Perfil | Módulos | Puede hacer |
|---|---|---|
| `RESPONSABLE_PAE` | 56 | Gestión integral del programa, incluida la aprobación |
| `COORDINADOR_SEDE` | 33 | Operación de su sede; no aprueba planes ni elimina |
| `OPERADOR_PAE` | 11 | Registro de entregas, novedades y evidencias |
| `SUPERVISOR_PAE` | 24 | Visitas, control de calidad y planes de mejoramiento |
| `AUDITOR_PAE` | 31 | Consulta y exportación con acceso a la bitácora |
| `CONSULTA_PAE` | 8 | Solo consulta; no exporta |

Cada perfil ve **solo** los módulos habilitados en su matriz de permisos:
el menú lateral se construye dinámicamente y las rutas no autorizadas
responden **403**.

---

## 5. Primer ingreso, paso a paso

1. Abra `http://localhost:8000/auth/login/`
2. Escriba `admin@datly.local` y `Admin123*`
3. Presione **Iniciar sesión** → llega al Dashboard

Desde ahí:

| Para… | Vaya a |
|---|---|
| Cargar el logo y datos del colegio | **Institución › Datos Institucionales** |
| Ajustar qué puede hacer cada perfil | **Configuración › Acceso de Perfiles** |
| Crear el año lectivo y los periodos | **Directiva › Año Lectivo / Periodo Académico** |
| Registrar estudiantes | **Estudiantes › Registro de Estudiantes** |
| Registrar docentes | **Docentes › Registro Docente** |
| Digitar calificaciones | **Evaluaciones › Asignación de Notas** |
| Generar boletines | **Promoción › Boletines Finales** |

---

## 6. Activar el doble factor (Google Authenticator)

1. Ingrese y vaya a **Mi Perfil › Seguridad**
2. **Activar doble factor**
3. Escanee el código QR con Google Authenticator, Microsoft Authenticator o Authy
4. Escriba el código de 6 dígitos para confirmar
5. **Guarde los 8 códigos de recuperación** — sirven si pierde el teléfono

Para exigirlo a un perfil completo: **Usuarios › Gestión de Usuarios**, editar el
usuario y marcar *Exigir doble factor*.

---

## 7. Si no puede ingresar

| Situación | Solución |
|---|---|
| «Credenciales inválidas» | Verifique mayúsculas; la contraseña es `Admin123*` con asterisco final |
| «Cuenta bloqueada» | Se bloquea 15 minutos tras 5 intentos fallidos. Espere o ejecute el desbloqueo (abajo) |
| Olvidó la contraseña | Enlace **Olvidé mi contraseña** en el login |
| La página no carga | Verifique que la ventana de `INICIAR.bat` siga abierta |
| «No fue posible conectar con la base de datos» | Inicie el servicio de PostgreSQL y revise el archivo `.env` |
| Puerto 8000 ocupado | Ejecute `INICIAR.bat 8080` |

Desbloquear o restablecer la contraseña del administrador desde la consola
(menú opción **12**, o `.venv\Scripts\python.exe manage.py shell`):

```python
from core.users.models import User
u = User.objects.get(email="admin@datly.local")
u.locked_until = None
u.failed_login_attempts = 0
u.set_password("Admin123*")
u.save()
```

---

## 8. Detener la plataforma

- Presione **CTRL + C** en la ventana negra del servidor, o
- Menú `PL_SGE.bat` → opción **4**, o
- `scripts\detener.bat`

---

## 9. Cambiar la contraseña del administrador

Recomendado antes de poner la plataforma en producción:

**Mi Perfil › Seguridad › Cambiar contraseña**

O cree otro administrador desde el menú, opción **5**.
