/* ==========================================================================
   PL_SGE - Planilla de digitacion de notas
   ========================================================================== */
import { $, $$, api, confirmDialog, Drawer, escapeHtml, icon, toast } from "../app.js";

const state = {
  assignment: null,
  period: null,
  sheet: null,
  dirty: new Map(),
};

/* -- Utilidades ----------------------------------------------------------- */
function scale() {
  return state.sheet?.scale || { minimum: 1, maximum: 5, passing: 3, decimals: 1 };
}

function clampScore(value) {
  const { minimum, maximum } = scale();
  const number = Number(String(value).replace(",", "."));
  if (Number.isNaN(number)) return null;
  return Math.min(Math.max(number, minimum), maximum);
}

/* -- Calculo de la definitiva --------------------------------------------
   Replica exactamente el motor del servidor (core/evaluations/services.py):
     compute_process_average -> promedio ponderado por el peso del proceso,
                                contando SOLO los procesos con nota digitada
     apply_rounding          -> politica de decimas configurada
     level_for               -> desempeno segun la escala valorativa

   El resultado es una previsualizacion: al guardar, el backend recalcula y
   la planilla se repinta con el valor consolidado, que es el que manda.
   ------------------------------------------------------------------------ */
function rounding() {
  return state.sheet?.rounding || { mode: "HALF_UP", decimals: 1, round_from: 0.5, apply_to_period: true };
}

/**
 * Divide dos enteros redondeando a la mitad al par (ROUND_HALF_EVEN), que es
 * el modo por defecto de `Decimal.quantize()` en el servidor.
 */
function divideHalfEven(numerator, denominator) {
  const whole = Math.floor(numerator / denominator);
  const twiceRemainder = 2 * (numerator - whole * denominator);
  if (twiceRemainder > denominator) return whole + 1;
  if (twiceRemainder < denominator) return whole;
  return whole % 2 === 0 ? whole : whole + 1; // empate: se queda en el par
}

/**
 * Aplica la politica de decimas sobre un valor expresado en centesimas
 * enteras, replicando `GradeDecimalConfig.apply()`.
 */
function applyRounding(hundredths) {
  const config = rounding();
  // Sin aplicacion al periodo el servidor deja el valor con dos decimales.
  if (!config.apply_to_period) return hundredths / 100;

  const decimals = config.decimals ?? 1;
  const divisor = 10 ** Math.max(0, 2 - decimals);
  const factor = 10 ** decimals;

  if (config.mode === "NONE") return hundredths / 100;
  if (config.mode === "DOWN") return Math.floor(hundredths / divisor) / factor;
  if (config.mode === "UP_FROM") {
    const integer = Math.floor(hundredths / 100);
    const fraction = (hundredths - integer * 100) / 100;
    return fraction >= config.round_from ? integer + 1 : integer;
  }
  // HALF_UP: la mitad sube, como ROUND_HALF_UP de Decimal.
  return Math.floor((hundredths + divisor / 2) / divisor) / factor;
}

/**
 * Definitiva del periodo: promedio ponderado por el peso de cada proceso,
 * contando solo los que tienen nota digitada.
 *
 * Replica `compute_process_average` + `apply_rounding` del servidor, con dos
 * detalles que importan para no mostrar una decima distinta de la guardada:
 *   1. El servidor redondea DOS veces: a 2 decimales y luego a la precision
 *      configurada.
 *   2. El primer redondeo es half-even (el de Decimal), no half-up.
 * Se opera con enteros para que no aparezcan errores de coma flotante.
 */
function computeFinal(student) {
  let numerator = 0;   // suma de nota(x100) * peso(x100)
  let denominator = 0; // suma de peso(x100)

  for (const process of state.sheet.processes) {
    const raw = student.grades[String(process.id)];
    if (raw === null || raw === undefined || raw === "") continue;
    const score = Number(raw);
    if (Number.isNaN(score)) continue;
    const weight = Number(process.weight ?? 100);
    numerator += Math.round(score * 100) * Math.round(weight * 100);
    denominator += Math.round(weight * 100);
  }
  if (denominator === 0) return null;

  // numerator / denominator es el promedio expresado en centesimas.
  const hundredths = divideHalfEven(numerator, denominator);
  return applyRounding(hundredths);
}

function performanceFor(value) {
  if (value === null || value === undefined) return null;
  const levels = scale().levels || [];
  const level = levels.find((item) => value >= item.minimum && value <= item.maximum);
  return level ? level.name : null;
}

function markDirty(studentId, processId, value) {
  state.dirty.set(`${studentId}:${processId}`, { student_id: studentId, process_id: processId, score: value });
  $("[data-save-sheet]").disabled = false;
  $("[data-pending-badge]").classList.remove("hidden");
}

/* -- Render --------------------------------------------------------------- */
function renderHead() {
  const head = $("[data-sheet-head]");
  const processes = state.sheet.processes;
  head.innerHTML = `
    <tr>
      <th class="sticky-col">Estudiante</th>
      ${processes
        .map(
          (process) => `<th class="grade-cell" title="${escapeHtml(process.name)}">
            <div class="truncate" style="max-width:76px;margin:0 auto">${escapeHtml(process.name)}</div>
            <div class="text-2xs text-muted">${process.weight}%</div>
          </th>`
        )
        .join("")}
      <th class="grade-cell grade-cell--final">Definitiva</th>
      <th class="grade-cell">Desempeno</th>
      <th class="grade-cell">Fallas</th>
    </tr>`;
}

function renderBody(filter = "") {
  const body = $("[data-sheet-body]");
  const processes = state.sheet.processes;
  const term = filter.trim().toLowerCase();
  const students = state.sheet.students.filter(
    (student) => !term || student.student.toLowerCase().includes(term) || student.document.includes(term)
  );

  if (!students.length) {
    body.innerHTML = `<tr><td colspan="${processes.length + 4}" class="text-center text-muted" style="padding:40px">
      No hay estudiantes matriculados en este grupo.</td></tr>`;
    return;
  }

  const passing = scale().passing;
  const locked = state.sheet.locked || !state.sheet.period.open;

  body.innerHTML = students
    .map((student, index) => {
      const cells = processes
        .map((process) => {
          const value = student.grades[String(process.id)];
          const failing = value !== null && value !== undefined && Number(value) < passing;
          // Se muestra con la precision de la escala: 3 -> 3.0
          const shown = value === null || value === undefined ? "" : Number(value).toFixed(scale().decimals);
          return `<td class="grade-cell">
            <input class="grade-input ${failing ? "is-failing" : ""}" inputmode="decimal"
              data-student="${student.student_id}" data-process="${process.id}"
              data-row="${index}" value="${shown}" ${locked ? "disabled" : ""}
              aria-label="Nota de ${escapeHtml(student.student)} en ${escapeHtml(process.name)}">
          </td>`;
        })
        .join("");

      const final = computeFinal(student);
      const performance = performanceFor(final);
      const finalClass = final !== null && final < passing ? "text-danger" : "text-success";
      return `
        <tr data-student-row="${student.student_id}">
          <td class="sticky-col">
            <div class="row" style="gap:10px">
              <span class="text-xs text-muted" style="width:22px">${index + 1}</span>
              <div style="min-width:0">
                <div class="truncate" style="font-weight:500;color:var(--text-primary)">${escapeHtml(student.student)}</div>
                <div class="text-xs text-muted">${escapeHtml(student.document)}</div>
              </div>
            </div>
          </td>
          ${cells}
          <td class="grade-cell grade-cell--final text-center">
            <strong class="${finalClass}" data-final>${final !== null ? final.toFixed(scale().decimals) : "-"}</strong>
          </td>
          <td class="grade-cell text-center text-xs" data-performance>${escapeHtml(performance || "-")}</td>
          <td class="grade-cell text-center text-xs">${student.absences || 0}</td>
        </tr>`;
    })
    .join("");

  bindInputs();
}

/** Repinta la definitiva y el desempeno de una fila tras editar una nota. */
function refreshRow(studentId) {
  const student = state.sheet.students.find((row) => row.student_id === studentId);
  const tr = $(`[data-student-row="${studentId}"]`, $("[data-sheet-body]"));
  if (!student || !tr) return;

  const final = computeFinal(student);
  const performance = performanceFor(final);
  const passing = scale().passing;

  const cell = $("[data-final]", tr);
  cell.textContent = final !== null ? final.toFixed(scale().decimals) : "-";
  cell.className = final !== null && final < passing ? "text-danger" : "text-success";

  $("[data-performance]", tr).textContent = performance || "-";
}

/** Recalcula las tarjetas del encabezado con lo que hay en pantalla. */
function refreshStats() {
  if (!state.sheet) return;
  const passing = scale().passing;
  const finals = state.sheet.students
    .map((student) => computeFinal(student))
    .filter((value) => value !== null);

  const total = state.sheet.students.length;
  const passingCount = finals.filter((value) => value >= passing).length;
  const failing = finals.filter((value) => value < passing).length;
  const average = finals.length ? finals.reduce((sum, value) => sum + value, 0) / finals.length : 0;
  const rate = finals.length ? Math.round((passingCount / finals.length) * 100) : 0;

  renderStats({
    total,
    average: average.toFixed(1),
    passing: passingCount,
    failing,
    pass_rate: rate,
  });
}

function bindInputs() {
  const inputs = $$(".grade-input", $("[data-sheet-body]"));
  inputs.forEach((input, index) => {
    input.addEventListener("focus", () => input.select());

    input.addEventListener("input", () => {
      const clean = input.value.replace(/[^\d.,]/g, "");
      if (clean !== input.value) input.value = clean;
    });

    input.addEventListener("change", () => {
      const studentId = Number(input.dataset.student);
      const processId = Number(input.dataset.process);
      const student = state.sheet.students.find((row) => row.student_id === studentId);
      const raw = input.value.trim();

      if (raw === "") {
        // Sin nota, el proceso deja de contar en el promedio ponderado,
        // igual que en el servidor (score__isnull=False).
        if (student) student.grades[String(processId)] = null;
        markDirty(studentId, processId, "");
        input.classList.remove("is-failing");
        refreshRow(studentId);
        refreshStats();
        return;
      }

      const value = clampScore(raw);
      if (value === null) {
        input.value = "";
        toast.warning("Valor invalido. Use el rango de la escala institucional.");
        return;
      }

      input.value = value.toFixed(scale().decimals);
      input.classList.toggle("is-failing", value < scale().passing);
      input.classList.add("is-saved");
      setTimeout(() => input.classList.remove("is-saved"), 900);

      // Se actualiza el modelo en memoria antes de recalcular, para que la
      // definitiva y el desempeno reflejen lo que el docente acaba de digitar.
      if (student) student.grades[String(processId)] = value;
      markDirty(studentId, processId, input.value);
      refreshRow(studentId);
      refreshStats();
    });

    input.addEventListener("keydown", (event) => {
      const columns = state.sheet.processes.length;
      if (event.key === "Enter" || event.key === "ArrowDown") {
        event.preventDefault();
        inputs[index + columns]?.focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        inputs[index - columns]?.focus();
      } else if (event.key === "ArrowRight" && input.selectionStart === input.value.length) {
        inputs[index + 1]?.focus();
      } else if (event.key === "ArrowLeft" && input.selectionStart === 0) {
        inputs[index - 1]?.focus();
      }
    });
  });
}

function renderStats(statistics) {
  const container = $("[data-stats]");
  if (!statistics) {
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");
  $("[data-stat-total]").textContent = statistics.total;
  $("[data-stat-average]").textContent = Number(statistics.average).toFixed(1);
  $("[data-stat-passing]").textContent = statistics.passing;
  $("[data-stat-failing]").textContent = statistics.failing;
  $("[data-stat-rate]").textContent = `${statistics.pass_rate}%`;
}

function renderMeta() {
  const meta = $("[data-sheet-meta]");
  const info = state.sheet.assignment;
  meta.innerHTML = `
    <span class="badge badge--brand">${icon("book", 13)} ${escapeHtml(info.subject)}</span>
    <span class="badge badge--neutral">${icon("users", 13)} ${escapeHtml(info.group)}</span>
    <span class="badge badge--info">${icon("user", 13)} ${escapeHtml(info.teacher)}</span>`;

  const alert = $("[data-sheet-alert]");
  if (state.sheet.locked) {
    alert.innerHTML = `<div class="alert alert--danger mb-4">${icon("lock", 18)}
      <div><div class="alert__title">Planilla bloqueada</div>
      La digitacion fue bloqueada por coordinacion. Consulte con el administrador.</div></div>`;
  } else if (!state.sheet.period.open) {
    alert.innerHTML = `<div class="alert alert--warning mb-4">${icon("clock", 18)}
      <div><div class="alert__title">Digitacion cerrada</div>
      La ventana de digitacion de este periodo no esta abierta.</div></div>`;
  } else if (!state.sheet.processes.length) {
    alert.innerHTML = `<div class="alert alert--warning mb-4">${icon("alert-triangle", 18)}
      <div><div class="alert__title">Sin procesos academicos</div>
      Cree al menos un proceso evaluable para esta asignatura y periodo.</div></div>`;
  } else {
    alert.innerHTML = "";
  }
}

/* -- Carga y guardado ----------------------------------------------------- */
async function loadSheet() {
  const assignment = $("[data-assignment]").value;
  const period = $("[data-period]").value;
  if (!assignment || !period) {
    toast.warning("Seleccione la asignacion academica y el periodo.");
    return;
  }
  state.assignment = assignment;
  state.period = period;
  state.dirty.clear();
  $("[data-save-sheet]").disabled = true;
  $("[data-pending-badge]").classList.add("hidden");
  $("[data-sheet-body]").innerHTML = `<tr><td class="text-center" style="padding:48px">
    <span class="spinner spinner--lg"></span></td></tr>`;

  try {
    const data = await api.get("/api/grade-sheet/", { assignment, period });
    state.sheet = data;
    renderHead();
    renderBody($("[data-filter-student]").value);
    // Las tarjetas se derivan de las mismas notas que muestra la tabla, para
    // que el encabezado nunca contradiga lo que el docente esta viendo.
    refreshStats();
    renderMeta();
  } catch (error) {
    toast.error(error.message);
    $("[data-sheet-body]").innerHTML = `<tr><td class="text-center text-danger" style="padding:48px">
      ${escapeHtml(error.message)}</td></tr>`;
  }
}

async function saveSheet() {
  if (!state.dirty.size) {
    toast.info("No hay cambios pendientes por guardar.");
    return;
  }
  const button = $("[data-save-sheet]");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> Guardando...';
  try {
    const data = await api.post("/api/grade-sheet/", {
      assignment: Number(state.assignment),
      period: Number(state.period),
      entries: Array.from(state.dirty.values()),
    });
    state.sheet = data;
    state.dirty.clear();
    renderHead();
    renderBody($("[data-filter-student]").value);
    refreshStats();
    $("[data-pending-badge]").classList.add("hidden");
    toast.success(`Se guardaron ${data.saved} notas y se consolido la definitiva.`);
  } catch (error) {
    toast.error(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = `${icon("save", 15)} Guardar notas`;
  }
}

/* -- Procesos academicos -------------------------------------------------- */
async function openProcessDrawer() {
  if (!state.assignment || !state.period) {
    toast.warning("Seleccione primero la asignacion y el periodo.");
    return;
  }
  const drawer = new Drawer({ title: "Nuevo proceso academico", subtitle: "Define una columna evaluable en la planilla." });
  drawer.body.innerHTML = `
    <form class="form-grid" id="process-form">
      <div class="field col-12">
        <label class="field__label">Nombre del proceso <span class="required">*</span></label>
        <input class="input" name="name" required placeholder="Taller 1, Evaluacion final...">
      </div>
      <div class="field col-6">
        <label class="field__label">Porcentaje (%)</label>
        <input class="input" name="weight" type="number" step="0.01" value="100">
      </div>
      <div class="field col-6">
        <label class="field__label">Fecha limite</label>
        <input class="input" name="due_date" type="date">
      </div>
      <div class="field col-12">
        <label class="field__label">Descripcion</label>
        <textarea class="textarea" name="description" rows="3"></textarea>
      </div>
    </form>`;
  drawer.footer.innerHTML = `
    <button class="btn btn--secondary" type="button" data-cancel>Cancelar</button>
    <button class="btn btn--primary" type="submit" form="process-form">${icon("save", 16)} Crear proceso</button>`;
  $("[data-cancel]", drawer.footer).addEventListener("click", () => drawer.destroy());
  drawer.open();

  $("#process-form", drawer.body).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      await api.post("/api/teacher-processes/", {
        assignment: Number(state.assignment),
        period: Number(state.period),
        name: form.name.value,
        weight: form.weight.value || 100,
        due_date: form.due_date.value || null,
        description: form.description.value,
      });
      toast.success("Proceso academico creado.");
      drawer.destroy();
      loadSheet();
    } catch (error) {
      toast.error(error.message);
    }
  });
}

/* -- Consolidacion -------------------------------------------------------- */
async function consolidateGroup() {
  if (!state.sheet) {
    toast.warning("Cargue primero una planilla.");
    return;
  }
  const confirmed = await confirmDialog({
    title: "Consolidar notas del grupo",
    message: "Se recalcularan las definitivas y los promedios de area de todo el grupo en este periodo.",
    confirmText: "Consolidar",
    tone: "primary",
    iconName: "refresh",
  });
  if (!confirmed) return;

  try {
    const assignment = await api.get(`/api/teaching-assignments/${state.assignment}/`);
    const data = await api.post("/api/subject-grades/consolidate/", {
      group: assignment.group,
      period: Number(state.period),
    });
    toast.success(`Se consolidaron ${data.processed} registros.`);
    loadSheet();
  } catch (error) {
    toast.error(error.message);
  }
}

/* -- Arranque ------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  $("[data-load-sheet]")?.addEventListener("click", loadSheet);
  $("[data-save-sheet]")?.addEventListener("click", saveSheet);
  $("[data-manage-processes]")?.addEventListener("click", openProcessDrawer);
  $("[data-consolidate]")?.addEventListener("click", consolidateGroup);
  $("[data-assignment]")?.addEventListener("change", () => {
    if ($("[data-assignment]").value) loadSheet();
  });
  $("[data-period]")?.addEventListener("change", () => {
    if (state.assignment) loadSheet();
  });
  $("[data-filter-student]")?.addEventListener("input", (event) => {
    if (state.sheet) renderBody(event.target.value);
  });

  const params = new URLSearchParams(window.location.search);
  const preset = params.get("assignment");
  if (preset) {
    $("[data-assignment]").value = preset;
    loadSheet();
  }

  window.addEventListener("beforeunload", (event) => {
    if (state.dirty.size) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "s") {
      event.preventDefault();
      saveSheet();
    }
  });
});
