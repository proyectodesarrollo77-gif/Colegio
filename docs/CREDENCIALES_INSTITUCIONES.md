# KINDORA — Credenciales por institución

**KINDORA** admite **varias instituciones educativas**. En la pantalla de
ingreso aparece un selector para elegir a cuál entrar; cada una es un entorno
independiente con sus propios estudiantes, docentes, grupos y calificaciones.

> El selector solo aparece cuando hay **más de una** institución activa. En una
> instalación con una sola, la pantalla de ingreso se ve exactamente como antes.

---

## 1. Regla de acceso

| Perfil | A qué instituciones puede entrar |
|---|---|
| `SUPER_ADMIN` | **A cualquiera.** Además cambia de institución **sin cerrar sesión**, desde la barra superior o el Panel de Instituciones |
| Todos los demás | **Solo a la suya.** Si eligen otra, el ingreso se rechaza con un mensaje explícito |

Esto no es solo una validación de pantalla: la API filtra por institución en el
servidor. Un usuario que pida por URL un estudiante de otra institución recibe
**404**, no el dato.

---

## 2. Institución en producción

La institución que ya estaba funcionando **no se modificó**: conserva su marca
de institución por defecto, sus 504 estudiantes y todos sus datos.

| Campo | Valor |
|---|---|
| Institución | Institución Educativa Distrital de Experiencias Pedagógicas |
| Usuario | `admin@datly.local` |
| Contraseña | `Admin123*` |
| Perfil | `SUPER_ADMIN` — controla toda la plataforma |

### Los dos modos del Super Administrador

Al ingresar **sin elegir institución**, entra a **administrar la plataforma**:

| | Administrando la plataforma | Dentro de una institución |
|---|---|---|
| Cómo se entra | Ingresar sin elegir institución | *Ingresar* en el panel, el selector de la barra superior, o elegirla al ingresar |
| Dashboard | **Panorama de la plataforma**: todas las instituciones, cómo funciona cada una y qué necesita atención | Dashboard académico **de esa institución** |
| Menú | Institución, Usuarios, Configuración y Auditoría | Los 22 módulos, igual que cualquier perfil de esa institución |
| Barra superior | Dice *Plataforma* | Dice el nombre de la institución |

Para volver: el selector de la barra superior → **Volver a administrar la
plataforma**.

> La operación académica (estudiantes, notas, asistencia, boletines, PAE)
> pertenece a una institución concreta: no significa nada sumada entre
> instituciones distintas. Por eso solo aparece cuando entra a una.

El **panorama de la plataforma** muestra, además del estado de cada
institución, avisos de lo que necesita atención: instituciones **sin ningún
usuario** (nadie puede entrar a ellas), instituciones a las que les falta algo
para operar, e instituciones listas donde nadie ha ingresado todavía.

### Qué puede hacer el Super Administrador

Es el único perfil con acceso al **Panel de Instituciones**
(`Institución → Panel de Instituciones`):

| Acción | Dónde |
|---|---|
| Ver **todas** las instituciones y cómo está funcionando cada una | Panel de Instituciones |
| **Crear** una institución nueva, limpia | Panel → *Nueva institución* |
| **Modificar** los datos de cualquiera | Panel → *Editar* en su fila |
| **Administrar los accesos** de cada institución y cambiar contraseñas | Panel → *Accesos* en su fila |
| **Entrar** a cualquier institución sin cerrar sesión | Panel → *Ingresar*, o el selector de la barra superior |
| **Activar o desactivar** una institución | Panel → *Desactivar* / *Activar* |

El panel muestra, por institución: sedes, grupos, estudiantes, docentes, notas
y asistencias registradas, último acceso, usuarios activos en los últimos 30
días y **qué le falta** para poder operar.

> Al Super Administrador **no le aparece** *Datos Institucionales* en el menú.
> Esa pantalla edita la institución activa, y para quien administra varias
> resulta ambigua: sus datos se modifican desde *Panel → Editar*, que siempre
> dice de cuál institución se trata. Los demás perfiles la siguen viendo.

Estados posibles:

| Estado | Significado |
|---|---|
| **En operación** | Ya tiene notas o asistencia registradas |
| **Lista, sin actividad** | Estructura completa, aún sin uso |
| **Incompleta** | Le falta algo; el panel dice exactamente qué |
| **Inactiva** | Desactivada, no aparece en el selector de ingreso |

> La institución predeterminada **no se puede desactivar**: es la que sostiene
> la plataforma cuando no hay ninguna elegida.

Las cuentas de demostración que ya existían (`rector@datly.local`,
`coordinador@datly.local`, `docente@datly.local`, etc., con `Demo123*`) siguen
funcionando y pertenecen a esta institución.

---

## 3. Instituciones de prueba

Contraseña común: **`Demo123*`**

### Institución Educativa Ficticia San Rafael
Medellín · código DANE `111111111111` · 2 sedes · 12 grupos · 72 estudiantes · 8 docentes

| Perfil | Usuario |
|---|---|
| Rector | `rector.sanrafael@datly.local` |
| Coordinador | `coordinador.sanrafael@datly.local` |
| Secretaria | `secretaria.sanrafael@datly.local` |
| Docente | `docente.sanrafael@datly.local` |

### Institución Educativa Ficticia La Esperanza
Cali · código DANE `222222222222` · 2 sedes · 12 grupos · 72 estudiantes · 8 docentes

| Perfil | Usuario |
|---|---|
| Rector | `rector.laesperanza@datly.local` |
| Coordinador | `coordinador.laesperanza@datly.local` |
| Secretaria | `secretaria.laesperanza@datly.local` |
| Docente | `docente.laesperanza@datly.local` |

### Colegio Ficticio Santa Teresa
Barranquilla · código DANE `333333333333` · 1 sede · 12 grupos · 72 estudiantes · 8 docentes

| Perfil | Usuario |
|---|---|
| Rector | `rector.santateresa@datly.local` |
| Coordinador | `coordinador.santateresa@datly.local` |
| Secretaria | `secretaria.santateresa@datly.local` |
| Docente | `docente.santateresa@datly.local` |

> Información **ficticia**. No corresponde a instituciones ni personas reales.

---

## 4. Cómo ingresar

1. Abra `http://localhost:8000/`.
2. Escriba usuario y contraseña.
3. Pulse *Iniciar sesión*.

**El selector de institución es opcional.** Si lo deja como está
(*Mi institución (automática)*), cada usuario entra a la suya. Solo hay que
elegir una cuando se administran varias.

El nombre de la institución aparece en el menú lateral: es la forma rápida de
confirmar en qué entorno está trabajando.

Para **cambiar de institución**: el Super Administrador usa el selector de la
barra superior o el Panel de Instituciones, sin cerrar sesión. Los demás
perfiles solo tienen acceso a la suya.

---

## 5. Qué está aislado y qué es común

| Aislado por institución | Común a toda la plataforma |
|---|---|
| Estudiantes, acudientes y matrículas | Perfiles y matriz de permisos |
| Docentes y asignaciones | Catálogo de módulos |
| Años lectivos, periodos y escalas | Bitácora de auditoría |
| Niveles, grados, grupos, áreas y asignaturas | Registros de seguridad y sesiones |
| Calificaciones, asistencia y observador | Notificaciones (son por usuario) |
| Sedes y jornadas | |
| Datos del PAE | |

Se aíslan **115 de los 138 modelos** del sistema. Los 23 restantes son
transversales por diseño: no tendría sentido que cada institución tuviera su
propia lista de perfiles o su propia bitácora.

---

## 6. Crear o recrear las instituciones de prueba

```bash
python manage.py seed_instituciones
```

Opciones:

```bash
# Sin estudiantes, solo la estructura académica
python manage.py seed_instituciones --estudiantes-por-grupo 0

# Más estudiantes por grupo
python manage.py seed_instituciones --estudiantes-por-grupo 12

# Solo una institución
python manage.py seed_instituciones --solo 111111111111

# Más grupos por grado
python manage.py seed_instituciones --grupos-por-grado 2
```

El comando es **idempotente**: volver a ejecutarlo no duplica nada y nunca
toca la institución que ya estaba funcionando.

---

## 7. Agregar una institución real

1. Ingrese como Super Administrador (`admin@datly.local` / `Admin123*`).
2. Vaya a **Institución → Panel de Instituciones**.
3. Pulse **Nueva institución**. Aparece el **mismo formulario de Datos
   Institucionales**, con todos los campos en blanco.
4. Diligencie al menos el código DANE y el nombre.
5. Al final, en **Usuario de ingreso a esta institución**, escriba el correo con
   el que se entrará a ella. La contraseña es opcional: si la deja vacía, el
   sistema genera una y se la muestra al crear.
6. Pulse *Crear institución*.

La institución y su usuario se crean **juntos**: si la contraseña no cumple la
política de seguridad, no se crea nada: no queda una institución a la que nadie
pueda entrar. El perfil de ese usuario puede ser Rector, Coordinador o
Secretaria; el Super Administrador no se asigna aquí, porque es un perfil de
toda la plataforma y no de una institución.

La institución **nace limpia**: solo sus datos, sin sedes, años lectivos,
grados, grupos ni asignaturas. No arrastra nada de las demás.

7. Entre a ella con **Ingresar**.
8. Cargue su información propia:
   - **Institución → Sedes y Jornadas**
   - **Directiva → Año Lectivo**, *Periodo Académico*, *Escala Valorativa*,
     *Niveles*, *Grados*, *Grupos*, *Áreas*, *Asignaturas*
   - **Docentes** y **Estudiantes**
   - **Usuarios → Gestión de Usuarios**, asignándoles esa institución

Mientras le falte algo, el panel la reporta como **Incompleta** e indica
exactamente qué. Cuando esté completa, pasa a **Lista, sin actividad**.

---

## 8. Modificar una institución existente

1. **Institución → Panel de Instituciones**.
2. Pulse **Editar** en la fila de la institución.
3. Se abre el **mismo formulario de Datos Institucionales**, cargado con **sus**
   datos: identificación, ubicación, contacto, firmas autorizadas, misión,
   visión, colores, logotipo y sello.
4. Guarde los cambios.

Editar una institución no toca a las demás, ni cambia cuál es la predeterminada
ni si está activa: esas condiciones se manejan con sus propias acciones del
panel. Si intenta ponerle un código DANE que ya usa otra, el cambio se rechaza.

---

## 9. Contraseñas: cambiarlas desde el Super Administrador

1. **Institución → Panel de Instituciones**.
2. Pulse **Accesos** en la fila de la institución.
3. Verá los usuarios que pueden ingresar a **esa** institución, con su perfil,
   último acceso y estado.
4. Pulse **Cambiar contraseña** en el usuario que necesite.

En el formulario puede:

| Opción | Resultado |
|---|---|
| Escribir una contraseña | Se asigna esa, si cumple la política de seguridad |
| Dejar el campo vacío | El sistema genera una y se la muestra |
| Marcar *Exigir que la cambie* | El usuario deberá cambiarla en su primer ingreso |

En ambos casos:

- Queda un **certificado de credenciales** en
  *Usuarios → Certificados de Usuario y Contraseña*.
- La operación se registra en la **bitácora de auditoría**.
- Si la cuenta estaba **bloqueada** por intentos fallidos, se desbloquea.

> Solo el Super Administrador puede hacerlo. Cualquier otro perfil recibe
> **403**, incluso el rector de la propia institución.

---

## 10. Volver a ejecutar `initialize_platform`

```bash
python manage.py initialize_platform
```

Es **seguro repetirlo**: adopta la institución predeterminada que ya existe y
trabaja sobre ella. No crea una institución nueva ni cambia de institución al
Super Administrador.

> Antes buscaba la institución por el código DANE `000000000000`. Si usted le
> había cambiado el código a la suya, el comando creaba una **segunda**
> institución vacía, se quedaba con la marca de predeterminada y arrastraba
> allí al Super Administrador: al ingresar, la plataforma se veía sin datos.
> Si le pasó, en el Panel de Instituciones aparecerá una institución de más
> llamada *Institucion Educativa Datly*, con código `000000000000` y sin
> estudiantes; desactívela y devuelva la marca de **Predeterminada** a la suya.
