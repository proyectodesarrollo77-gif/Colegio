# Instalar PL_SGE en otro equipo

Guía paso a paso para poner la plataforma a funcionar en un computador nuevo.

---

## Antes de empezar: qué NO se copia

Estas carpetas **no** deben copiarse del equipo original. Se generan en el
equipo nuevo durante la instalación, y copiarlas causa fallos:

| No copiar | Por qué |
|---|---|
| `.venv/` | Contiene rutas absolutas del equipo original |
| `__pycache__/` | Bytecode compilado, se regenera solo |
| `.env` | Lleva la contraseña de **esa** base de datos; se crea nuevo |
| `staticfiles/` | Se regenera con `collectstatic` |
| `logs/` | Registros del otro equipo |

Todo eso ya está excluido en `.gitignore`, así que si traslada el proyecto con
Git no tiene que hacer nada.

---

## Paso 1 — Instalar Python

Descargue **Python 3.11 o superior** de <https://www.python.org/downloads/>.

> **En Windows, durante la instalación marque la casilla
> «Add Python to PATH».** Es el error más común: si no la marca, los `.bat`
> no encontrarán Python.

Verifique en una consola nueva:

```bash
python --version
```

Debe responder `Python 3.11.x` o superior.

---

## Paso 2 — Instalar PostgreSQL

Descargue **PostgreSQL 14 o superior** de
<https://www.postgresql.org/download/>.

Durante la instalación:

1. Anote la **contraseña del usuario `postgres`** que le pida. La necesitará en
   el paso 4.
2. Deje el puerto por defecto: **5432**.
3. Al final puede omitir «Stack Builder».

Verifique que el servicio quedó corriendo:

- **Windows**: tecla Windows → `services.msc` → busque `postgresql-x64-16`; el
  estado debe ser *En ejecución*.
- **Linux**: `sudo systemctl status postgresql`
- **macOS**: `brew services list`

---

## Paso 3 — Copiar el proyecto

Elija una de las dos formas.

### Opción A — Con Git (recomendada)

```bash
git clone <url-del-repositorio>
cd PL_SGE
```

### Opción B — Copiando la carpeta

Copie la carpeta `PL_SGE` completa (por USB, red o ZIP) al equipo nuevo, por
ejemplo a `C:\PL_SGE`.

Si copió la carpeta desde un equipo donde ya se había usado, **borre** en el
equipo nuevo estas carpetas si existen: `.venv`, `staticfiles`, `logs` y todas
las `__pycache__`. También borre el archivo `.env`.

---

## Paso 4 — Configurar la contraseña de la base de datos

Copie `.env.example` a `.env`:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abra `.env` con el Bloc de notas y ajuste **solo estas líneas** con los datos
de PostgreSQL del equipo nuevo:

```
DB_NAME=pl_sge
DB_USER=postgres
DB_PASSWORD=la-contraseña-que-puso-en-el-paso-2
DB_HOST=localhost
DB_PORT=5432
```

> Si va a dejar la plataforma expuesta a otros equipos de la red, cambie además
> `DJANGO_SECRET_KEY` por un valor propio y agregue la IP del servidor a
> `DJANGO_ALLOWED_HOSTS`.

Si omite este paso, el instalador crea el `.env` con la contraseña por defecto
`postgres`, que probablemente no coincida con la suya.

---

## Paso 5 — Ejecutar la instalación

### Windows

Doble clic en **`INSTALAR.bat`**, o desde el menú `PL_SGE.bat` → opción **1**.

### Linux / macOS

```bash
chmod +x instalar.sh
./instalar.sh
```

El instalador hace siete pasos por usted:

1. Verifica Python
2. Crea el entorno virtual `.venv`
3. Instala las dependencias
4. Crea el `.env` si no existe
5. Crea la base de datos `pl_sge`
6. Crea las 157 tablas
7. Carga perfiles, permisos, estructura académica y la configuración del PAE

Al terminar muestra las credenciales de acceso.

### Si prefiere hacerlo a mano

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python scripts/crear_bd.py
python manage.py migrate
python manage.py initialize_platform
```

---

## Paso 6 — Iniciar y entrar

### Windows

Doble clic en **`INICIAR.bat`** (o `PL_SGE.bat` → opción **3**). Abre el
navegador solo.

### Linux / macOS

```bash
./iniciar.sh
```

Entre en <http://localhost:8000/> con:

| Campo | Valor |
|---|---|
| Usuario | `admin@datly.local` |
| Contraseña | `Admin123*` |

> **Cambie esa contraseña de inmediato** si el equipo va a quedar en uso real:
> Mi perfil → Seguridad.

En el menú lateral debe aparecer el grupo **Alimentación Escolar** con las 22
opciones del PAE.

---

## Paso 7 — Verificar que todo quedó bien

```bash
python smoke_test.py
```

Debe terminar con `RESULTADO: todas las rutas respondieron correctamente`.

Desde el menú: `PL_SGE.bat` → opción **9**.

---

## Paso 8 (opcional) — Datos de demostración

Solo si quiere recorrer la plataforma con información de ejemplo. **No lo haga
en una instalación que vaya a usarse de verdad**, porque crea estudiantes,
docentes y operadores ficticios.

```bash
python manage.py seed_demo --students-per-group 21 --teachers 14
python manage.py seed_pae_demo
```

Desde el menú: opción **2** y luego opción **13 → 2**.

---

## Llevarse también la información (no solo el programa)

Los pasos anteriores instalan la plataforma **vacía**. Si además quiere pasar
los datos que ya tiene en el equipo original:

**En el equipo original**, genere un respaldo:

```bash
python scripts/respaldar_bd.py
```

Queda un archivo en `database/respaldos/pl_sge_AAAAMMDD_HHMMSS.backup`.
Desde el menú: opción **6**.

**Copie ese archivo** a la misma carpeta del equipo nuevo y restaure:

```bash
python scripts/restaurar_bd.py --ultimo
```

Desde el menú: opción **7**.

> La restauración **reemplaza** toda la información del equipo nuevo. Como
> acaba de instalarlo, no hay nada que perder.

Copie también la carpeta `media/` si tenía documentos, evidencias o fotos
cargadas: esos archivos no viajan dentro del respaldo de la base de datos.

---

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `'python' no se reconoce como un comando` | No marcó «Add Python to PATH». Reinstale Python marcando la casilla, o use la ruta completa al ejecutable |
| `No fue posible preparar la base de datos` | El servicio de PostgreSQL está detenido, o la contraseña de `.env` no coincide con la real |
| `password authentication failed for user "postgres"` | La `DB_PASSWORD` del `.env` es incorrecta |
| `port 8000 is already in use` | Otro programa usa el puerto. Ejecute `INICIAR.bat 8080` y entre a `http://localhost:8080/` |
| La página carga sin estilos | Ejecute `python manage.py collectstatic --noinput` (menú → opción **11**) |
| El menú no muestra el PAE | Ejecute `python manage.py seed_pae` |
| `ModuleNotFoundError` al iniciar | El entorno virtual no está activo o faltan dependencias: `pip install -r requirements.txt` |

---

## Si otros equipos deben conectarse a este

Para que la plataforma sea accesible desde otros computadores de la red:

1. En `.env`, agregue la IP del servidor:

   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
   DJANGO_CSRF_TRUSTED_ORIGINS=http://192.168.1.50:8000
   ```

2. Inicie con:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

3. Abra el puerto 8000 en el firewall de Windows.

Los demás equipos entran a `http://192.168.1.50:8000/`.

> Para uso institucional real, siga la sección **Despliegue en producción** del
> [README](../README.md): `DJANGO_DEBUG=False`, `gunicorn` y un servidor web
> al frente. `runserver` es solo para desarrollo y pruebas.
