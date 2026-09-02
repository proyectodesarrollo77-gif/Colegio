# Módulo del PAE — Manual funcional e instalación

Guía de uso del **Programa de Alimentación Escolar** en PL_SGE, dirigida a
quien opera el programa en la institución.

---

## 1. Instalación

El módulo viene incluido en la plataforma. Sobre una instalación ya
funcionando (`migrate` + `initialize_platform`), basta cargar su configuración:

```bash
python manage.py seed_pae
```

Esto crea la normativa de referencia, los 12 catálogos parametrizables (85
elementos), las modalidades, los tipos de complemento, tres listas de
verificación con 26 criterios y la vigencia del programa asociada al año
lectivo en curso.

Para recorrer el módulo con información de ejemplo:

```bash
python manage.py seed_demo --students-per-group 21 --teachers 14
python manage.py seed_pae_demo
```

> Los datos de demostración son **ficticios**: operadores, contratos, personas
> y radicados son inventados y no corresponden a organizaciones ni personas
> reales.

Instalación completa desde cero:

```bash
python manage.py migrate
python manage.py initialize_platform
python manage.py seed_pae
python manage.py runserver
```

En Windows, `PL_SGE.bat` ofrece las mismas operaciones desde un menú.

---

## 2. Perfiles de acceso

Además de los perfiles académicos, el módulo agrega seis:

| Perfil | Qué puede hacer |
|---|---|
| `RESPONSABLE_PAE` | Gestión integral: configura, planea, aprueba y exporta |
| `COORDINADOR_SEDE` | Opera **su sede**: beneficiarios, programación, entregas, control, novedades y PQRS. No aprueba planes ni elimina |
| `OPERADOR_PAE` | El operador contratado: registra entregas, novedades y evidencias. No ve contratos |
| `SUPERVISOR_PAE` | Supervisión: visitas, hallazgos, control de calidad y planes de mejoramiento; consulta el resto |
| `AUDITOR_PAE` | Consulta y exporta todo, con acceso a la bitácora. No escribe |
| `CONSULTA_PAE` | Solo consulta la información básica del programa. No exporta |

El perfil **Administrador** del programa corresponde a `SUPER_ADMIN` y el
**Directivo** a `RECTOR`, que ya cubren el módulo.

Los permisos se ajustan en **Configuración › Acceso de Perfiles**. Se validan
en el servidor: ocultar un botón nunca es el control.

---

## 3. Orden de trabajo recomendado

```
1. Configuración   →  vigencia, normativa, catálogos, modalidades, complementos
2. Diagnóstico     →  condiciones de cada sede
3. Priorización    →  focalización de la población
4. Beneficiarios   →  vinculación de los estudiantes matriculados
5. Operadores      →  registro del operador
6. Contratos       →  contrato y sedes cubiertas
7. Menús           →  ciclo de menú, días, preparaciones e ingredientes
8. Planeación      →  plan operativo por sede → aprobación
9. Programación    →  generación masiva de la programación diaria
10. Entregas       →  registro diario en la planilla
11. Control        →  aplicación de listas de verificación
12. Seguimiento    →  visitas, novedades, mejoramiento, PQRS, participación
13. Indicadores    →  recálculo y consulta
```

---

## 4. Las 22 opciones del menú

| # | Opción | Para qué sirve |
|---|---|---|
| 1 | Dashboard PAE | Cobertura, cumplimiento, novedades y alertas, con filtros por sede, jornada, operador y fechas |
| 2 | Configuración del Programa | Vigencias, normativa, catálogos, modalidades y complementos |
| 3 | Diagnóstico de Sedes | Condiciones de infraestructura; calcula un puntaje y un resultado |
| 4 | Priorización de Población | Focalización por sede, grado y grupo con criterios ponderados |
| 5 | Beneficiarios | Vinculación de estudiantes matriculados al programa |
| 6 | Planeación Operativa | Plan por sede con su flujo de aprobación |
| 7 | Ciclos de Menú | Menús versionados con días, preparaciones e ingredientes |
| 8 | Operadores | Operadores del servicio de alimentación |
| 9 | Contratos y Convenios | Contratos, sedes cubiertas y alerta de vencimiento |
| 10 | Programación de Entregas | Programación diaria, con generación masiva |
| 11 | Entregas Diarias | Registro efectivo y planilla del día |
| 12 | Control de Calidad | Listas de verificación, criterios y su aplicación |
| 13 | Visitas de Supervisión | Visitas y hallazgos |
| 14 | Novedades e Incidencias | Novedades con su ciclo de gestión |
| 15 | Planes de Mejoramiento | Acciones correctivas con verificación de eficacia |
| 16 | PQRS | Peticiones, quejas y reclamos con control de términos |
| 17 | Participación Ciudadana | Comités, asistentes y compromisos |
| 18 | Documentos del Programa | Repositorio documental versionado |
| 19 | Evidencias | Soportes adjuntos a cualquier registro |
| 20 | Indicadores | Cobertura, cumplimiento y gestión frente a las metas |
| 21 | Informes PAE | 14 informes exportables |
| 22 | Auditoría del PAE | Bitácora de las operaciones del módulo |

---

## 5. Operaciones frecuentes

### 5.1 Vincular beneficiarios

**Los estudiantes provienen del módulo de Estudiantes.** El PAE solo establece
la relación de beneficiario. Hay tres caminos:

1. **Desde una priorización aprobada** — en *Priorización*, botón
   *Vincular beneficiarios*: se vinculan los estudiantes matriculados que
   cumplen los criterios, sin duplicar los ya vinculados.
2. **Uno a uno** — en *Beneficiarios*, botón *Nuevo*.
3. **Por archivo** — *Beneficiarios › Importar*.

Un estudiante no puede quedar vinculado dos veces en la misma vigencia.

### 5.2 Importar desde CSV o XLSX

En **Importar información** se cargan beneficiarios, programaciones y ciclos de
menú.

1. Elija qué importar y descargue la plantilla.
2. Complete el archivo; la primera fila son los encabezados.
3. Use **Solo validar** para revisar sin guardar.
4. Use **Importar** para aplicar los cambios.

Reglas de la importación:

- Si **una** fila falla, **no se guarda ninguna**: se muestra la tabla de
  errores con la fila y la columna exactas.
- Volver a cargar el mismo archivo **actualiza**, no duplica.
- Un documento repetido dentro del archivo se reporta como error.
- Un estudiante que no exista en el módulo de Estudiantes se reporta con su
  fila: debe registrarse allí primero.
- Máximo 5 MB y 5.000 filas por archivo.

### 5.3 Registrar la entrega del día

En **Entregas Diarias › Planilla del día**:

1. Elija la fecha y, si lo desea, el plan.
2. Digite las raciones **recibidas** y **entregadas** de cada fila.
3. La planilla calcula en línea:

   ```
   faltantes     = programadas − recibidas
   no entregadas = recibidas   − entregadas
   cumplimiento  = entregadas  / programadas × 100
   ```

4. Si hay cualquier incumplimiento, la **justificación es obligatoria**: el
   campo se marca en rojo y la planilla no se guarda sin ella.
5. No es posible registrar más entregadas que recibidas.
6. Guarde: las filas con incumplimiento quedan en estado *Con novedad*.

Desde una entrega puede generarse una novedad con el botón de la fila.

### 5.4 Aplicar una lista de verificación

En **Control de Calidad › Aplicar lista**:

1. Seleccione la verificación creada previamente.
2. Responda cada criterio: *Cumple*, *No cumple* o *No aplica*.
3. El resultado se calcula con el peso de cada criterio. *No aplica* se excluye
   del cálculo.
4. **Un criterio crítico marcado como *No cumple* fuerza el resultado global a
   *No cumple***, sin importar el puntaje.
5. Los umbrales de cumplimiento pleno y parcial se configuran en cada lista.

### 5.5 Aprobar un plan operativo

Flujo de estados:

```
Borrador → En revisión → Aprobado → En ejecución → Cerrado
```

- Solo los planes en *Borrador* o *En revisión* admiten edición libre.
- Aprobar exige **permiso de aprobación** sobre planeación.
- Cada transición queda en el historial con usuario, fecha y motivo.
- *Sincronizar beneficiarios* actualiza el conteo y las raciones proyectadas.

### 5.6 Gestionar una novedad

```
Reportada → Asignada → En investigación → En corrección → Solucionada → Cerrada
```

Para **cerrar** se exige registrar la solución aplicada. Desde un hallazgo puede
generarse el plan de mejoramiento correspondiente, que a su vez exige
verificación de eficacia y evidencia para cerrarse.

### 5.7 Versionar un ciclo de menú

*Crear nueva versión* clona días, preparaciones e ingredientes y archiva la
versión anterior. *Publicar como vigente* deja una sola versión activa por
código. Las programaciones históricas conservan el menú con el que operaron.

### 5.8 Consultar indicadores e informes

- **Indicadores**: *Recalcular* los reconstruye de la operación registrada. No
  se digitan a mano.
- **Informes**: 14 informes exportables a XLSX y CSV, con filtros por sede y
  rango de fechas. Cada exportación queda en la bitácora.

---

## 6. Alertas

El tablero muestra las situaciones que requieren gestión:

| Alerta | Cuándo aparece |
|---|---|
| Contratos vencidos / por vencer | Según los días de aviso del contrato |
| Documentos vencidos / por vencer | Dentro de los 30 días previos |
| Novedades vencidas | Superaron su fecha límite sin cierre |
| Acciones correctivas vencidas | Planes de mejoramiento fuera de plazo |
| PQRS fuera de término | Sin respuesta dentro del plazo |
| Visitas pendientes | Programadas y no realizadas |
| Entregas con incumplimiento | Con raciones faltantes o no entregadas |
| Sin vigencia configurada | No hay vigencia del programa creada |

*Notificar alertas* las envía al centro de notificaciones de la plataforma.

---

## 7. Parámetros normativos

Los valores de origen normativo **no están fijos en el código**: son
configuración editable desde **Configuración del Programa**.

Los que aún no se han confirmado contra el texto oficial aparecen marcados
como **Por validar**. Confírmelos y ajústelos antes de operar en producción;
no requiere intervención técnica.

Cada vigencia guarda la norma bajo la cual opera, de modo que un cambio
normativo no altera la información ya producida.

---

## 8. Preguntas frecuentes

**El estudiante no aparece al vincular beneficiarios.**
Debe estar registrado en el módulo de Estudiantes y tener matrícula **activa**
en el año lectivo de la vigencia.

**No puedo editar un plan.**
Si está aprobado, en ejecución o cerrado, se requiere permiso de aprobación.

**La planilla no deja guardar.**
Hay incumplimiento sin justificar, o se están registrando más raciones
entregadas que recibidas.

**La verificación da "No cumple" con puntaje alto.**
Un criterio crítico quedó marcado como *No cumple*: eso fuerza el resultado.

**No veo información de otras sedes.**
Los perfiles de coordinador de sede y operador solo ven las sedes asignadas.

**La importación reporta errores y no guardó nada.**
Es el comportamiento esperado: o entra el archivo completo, o no entra ninguna
fila. Corrija las filas indicadas y vuelva a cargarlo.
