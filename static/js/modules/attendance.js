/* ==========================================================================
   PL_SGE - Planilla diaria de asistencia
   ========================================================================== */
import { $, $$, api, escapeHtml, icon, toast } from "../app.js";

const TONES = {
  PRESENTE: "success",
  AUSENTE: "danger",
  TARDE: "warning",
  EXCUSA: "info",
  RETIRO: "neutral",
};

const state = {
  sheet: null,
  entries: new Map(),
  dirty: false,
};

function setDirty(value) {
  state.dirty = value;
  $("[data-save-attendance]").disabled = !value;
}

function updateCounters() {
  const counters = { PRESENTE: 0, AUSENTE: 0, TARDE: 0, EXCUSA: 0, RETIRO: 0 };
  state.entries.forEach((entry) => {
    counters[entry.status] = (counters[entry.status] || 0) + 1;
  });
  Object.entries(counters).forEach(([status, total]) => {
    const node = $(`[data-count-${status}]`);
    if (node) node.textContent = total;
  });
  $("[data-attendance-stats]").classList.remove("hidden");
}

function renderRows(filter = "") {
  const body = $("[data-attendance-body]");
  const term = filter.trim().toLowerCase();
  const students = state.sheet.students.filter(
    (student) => !term || student.student.toLowerCase().includes(term) || student.document.includes(term)
  );

  if (!students.length) {
    body.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="padding:40px">
      No hay estudiantes matriculados en este grupo.</td></tr>`;
    return;
  }

  body.innerHTML = students
    .map((student, index) => {
      const entry = state.entries.get(student.student_id) || {
        student_id: student.student_id,
        status: student.status,
        minutes_late: student.minutes_late,
        observation: student.observation,
      };
      const options = state.sheet.statuses
        .map(
          (status) => `<button class="btn btn--sm ${
            entry.status === status.value ? `btn--${TONES[status.value] === "neutral" ? "secondary" : TONES[status.value]}` : "btn--ghost"
          }" type="button" data-status="${status.value}" data-student="${student.student_id}">${escapeHtml(status.label)}</button>`
        )
        .join("");

      return `<tr data-student-row="${student.student_id}">
        <td class="text-xs text-muted">${index + 1}</td>
        <td class="cell-primary">
          <div>${escapeHtml(student.student)}</div>
          <div class="text-xs text-muted">${escapeHtml(student.document)}</div>
        </td>
        <td><div class="btn-group" style="flex-wrap:wrap">${options}</div></td>
        <td>
          <input class="input" type="number" min="0" max="120" style="height:32px"
                 data-minutes="${student.student_id}" value="${entry.minutes_late || 0}"
                 ${entry.status === "TARDE" ? "" : "disabled"}>
        </td>
        <td>
          <input class="input" style="height:32px" placeholder="Observacion"
                 data-observation="${student.student_id}" value="${escapeHtml(entry.observation || "")}">
        </td>
      </tr>`;
    })
    .join("");

  bindRows();
  updateCounters();
}

function bindRows() {
  $$("[data-status]", $("[data-attendance-body]")).forEach((button) => {
    button.addEventListener("click", () => {
      const studentId = Number(button.dataset.student);
      const entry = state.entries.get(studentId) || { student_id: studentId, minutes_late: 0, observation: "" };
      entry.status = button.dataset.status;
      if (entry.status !== "TARDE") entry.minutes_late = 0;
      state.entries.set(studentId, entry);

      const row = button.closest("tr");
      $$("[data-status]", row).forEach((item) => {
        const active = item.dataset.status === entry.status;
        const tone = TONES[item.dataset.status];
        item.className = `btn btn--sm ${active ? `btn--${tone === "neutral" ? "secondary" : tone}` : "btn--ghost"}`;
      });
      const minutes = row.querySelector("[data-minutes]");
      minutes.disabled = entry.status !== "TARDE";
      if (entry.status !== "TARDE") minutes.value = 0;

      setDirty(true);
      updateCounters();
    });
  });

  $$("[data-minutes]", $("[data-attendance-body]")).forEach((input) => {
    input.addEventListener("change", () => {
      const studentId = Number(input.dataset.minutes);
      const entry = state.entries.get(studentId);
      if (entry) {
        entry.minutes_late = Number(input.value) || 0;
        setDirty(true);
      }
    });
  });

  $$("[data-observation]", $("[data-attendance-body]")).forEach((input) => {
    input.addEventListener("change", () => {
      const studentId = Number(input.dataset.observation);
      const entry = state.entries.get(studentId);
      if (entry) {
        entry.observation = input.value;
        setDirty(true);
      }
    });
  });
}

async function loadSheet() {
  const assignment = $("[data-assignment]").value;
  const period = $("[data-period]").value;
  const date = $("[data-date]").value;
  const block = $("[data-block]").value || 1;

  if (!assignment || !period || !date) {
    toast.warning("Seleccione la asignacion, el periodo y la fecha.");
    return;
  }

  $("[data-attendance-body]").innerHTML =
    '<tr><td colspan="5" class="text-center" style="padding:48px"><span class="spinner spinner--lg"></span></td></tr>';

  try {
    const data = await api.get("/api/attendance-sheet/", { assignment, period, date, block });
    state.sheet = data;
    state.entries = new Map(
      data.students.map((student) => [
        student.student_id,
        {
          student_id: student.student_id,
          status: student.status,
          minutes_late: student.minutes_late,
          observation: student.observation,
        },
      ])
    );
    if (data.session?.topic) $("[data-topic]").value = data.session.topic;
    $("[data-attendance-meta]").innerHTML = `
      <span class="badge badge--brand">${icon("book", 13)} ${escapeHtml(data.assignment.subject)}</span>
      <span class="badge badge--neutral">${icon("users", 13)} ${escapeHtml(data.assignment.group)}</span>
      <span class="badge badge--info">${icon("calendar", 13)} ${escapeHtml(date)}</span>`;
    renderRows($("[data-filter-student]").value);
    setDirty(false);
  } catch (error) {
    toast.error(error.message);
    $("[data-attendance-body]").innerHTML =
      `<tr><td colspan="5" class="text-center text-danger" style="padding:44px">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function saveSheet() {
  if (!state.sheet) return;
  const button = $("[data-save-attendance]");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> Guardando...';
  try {
    const data = await api.post("/api/attendance-sheet/", {
      assignment: Number($("[data-assignment]").value),
      period: Number($("[data-period]").value),
      date: $("[data-date]").value,
      block: Number($("[data-block]").value) || 1,
      topic: $("[data-topic]").value,
      entries: Array.from(state.entries.values()),
    });
    toast.success(`Asistencia registrada para ${data.saved} estudiantes.`);
    setDirty(false);
  } catch (error) {
    toast.error(error.message);
  } finally {
    button.innerHTML = `${icon("save", 15)} Guardar asistencia`;
    button.disabled = !state.dirty;
  }
}

function markAll(status) {
  if (!state.sheet) return;
  state.entries.forEach((entry) => {
    entry.status = status;
    if (status !== "TARDE") entry.minutes_late = 0;
  });
  renderRows($("[data-filter-student]").value);
  setDirty(true);
}

document.addEventListener("DOMContentLoaded", () => {
  const dateInput = $("[data-date]");
  if (dateInput && !dateInput.value) dateInput.valueAsDate = new Date();

  $("[data-load-attendance]")?.addEventListener("click", loadSheet);
  $("[data-save-attendance]")?.addEventListener("click", saveSheet);
  $("[data-mark-all]")?.addEventListener("click", (event) => markAll(event.currentTarget.dataset.markAll));
  $("[data-filter-student]")?.addEventListener("input", (event) => {
    if (state.sheet) renderRows(event.target.value);
  });
  $("[data-assignment]")?.addEventListener("change", () => {
    if ($("[data-assignment]").value) loadSheet();
  });
});
