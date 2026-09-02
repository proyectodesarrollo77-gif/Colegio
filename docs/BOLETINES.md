# KINDORA — Boletines e informes académicos

Un boletín es una **fotografía** de las notas en el momento en que se genera:
KINDORA guarda el detalle completo (áreas, asignaturas, notas, desempeños,
fallas y docentes) dentro del boletín. Por eso reimprimirlo meses después
devuelve exactamente lo mismo, aunque las notas hayan cambiado después.

Se entrega de dos formas: **por estudiante** y **por grupo completo**.

---

## 1. Dónde está

**Promoción → Boletines Finales** (`/promocion/boletines/`)

Solo lo ven los perfiles con permiso sobre `promotion.final_reports`. Los
boletines que se muestran son siempre los de la institución en la que está
trabajando: un boletín de otra institución no se puede abrir ni siquiera
escribiendo su dirección a mano.

---

## 2. Generar (siempre en lote, por grupo)

En la parte superior de la pantalla se eligen tres cosas:

| Campo | Qué significa |
|---|---|
| **Grupo** | El curso completo. Obligatorio |
| **Periodo** | El periodo a informar. Si lo deja vacío, sale el **consolidado del año** |
| **Tipo de boletín** | *Boletín de periodo* o *Boletín final del año* |

Luego **Generar boletines**. KINDORA recorre las matrículas **activas** del
grupo y arma un boletín por estudiante, con:

- las asignaturas agrupadas por área, con nota, desempeño, fallas y docente;
- el promedio de cada área;
- el promedio general y el total de inasistencias;
- la observación del director de grupo, si el tutor la registró.

Vuelve a ejecutarse cuantas veces haga falta: **actualiza** el boletín que ya
existía, no crea uno nuevo. Así, si corrige una nota, basta con volver a
generar.

> Los boletines nacen **sin publicar**, y mientras lo estén, el documento sale
> marcado *DOCUMENTO NO PUBLICADO*.

---

## 3. Publicar

**Publicar boletines** marca como publicados todos los del grupo elegido. Es el
paso que separa el borrador que revisa la coordinación del documento que se
entrega al acudiente.

---

## 4. Imprimir

### Por estudiante

En la tabla, la acción **Imprimir boletín** de cada fila abre el boletín de ese
estudiante listo para imprimir (`/promocion/boletin/<id>/`).

### Por grupo (en lote)

El botón **Imprimir grupo** abre, en una sola pestaña, los boletines de todo el
grupo con el filtro que tenga seleccionado (grupo, periodo y tipo). Cada boletín
ocupa **su propia hoja**: se manda una vez a la impresora y salen todos.

Es exactamente el mismo documento que el individual — misma hoja, mismo
encabezado, mismas firmas — porque ambas impresiones usan la misma plantilla.

Para guardarlos como PDF, en el diálogo de impresión del navegador elija
*Guardar como PDF* en vez de la impresora.

---

## 5. Qué sale en la hoja

| Zona | Contenido |
|---|---|
| Encabezado | Nombre de la institución, resolución, DANE, NIT, dirección y logo |
| Identificación | Estudiante, documento, grado, grupo, año lectivo y director de grupo |
| Cuerpo | Áreas con sus asignaturas: nota, desempeño, fallas, docente y observación |
| Totales | Promedio general, puesto y total de inasistencias |
| Observaciones | Lo que registró el director de grupo |
| Firmas | Director de grupo y rector (con firma escaneada si está cargada) |
| Pie | Fecha de generación, institución y ciudad |

El encabezado sale de **Configuración → Encabezado de Reportes**, y se mantiene
al día solo: si cambia el nombre, el código DANE o la dirección de la
institución, las líneas se actualizan. Si alguien las redactó a mano, se
respetan tal cual.

---

## 6. Exportar la lista

La tabla de boletines se exporta a **CSV** o **Excel** con el botón de
exportación, con los promedios, puestos y fallas de todos los estudiantes
filtrados. Es la lista consolidada, no los boletines impresos.

---

## 7. Orden recomendado para cerrar un periodo

1. **Evaluaciones → Registro de Notas**: termine de digitar.
2. **Promoción → Cierre Académico**: consolide el periodo.
3. **Promoción → Boletines Finales**: elija grupo y periodo, **Generar boletines**.
4. Revise en la tabla los promedios y puestos.
5. **Publicar boletines**.
6. **Imprimir grupo** y entregue.

Repita los pasos 3 a 6 por cada grupo.
