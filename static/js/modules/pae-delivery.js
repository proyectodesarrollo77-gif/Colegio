/**
 * Planilla diaria de entregas del PAE.
 *
 * Calcula en linea faltantes, no entregadas y cumplimiento con las mismas
 * formulas del backend, y guarda toda la planilla en una sola operacion. El
 * servidor vuelve a validar cada fila: el calculo del navegador es solo ayuda
 * visual, nunca la fuente de verdad.
 */
import { $, api, escapeHtml, formatNumber, icon, toast } from "../app.js";

const dateInput = $("#sheet-date");
const planSelect = $("#sheet-plan");
const rowsSlot = $("[data-sheet-rows]");
const totalsSlot = $("[data-sheet-totals]");

let rows = [];

function today() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/* --------------------------------------------------------------------------
   Calculo (espejo de PaeDelivery.compute_totals)
   -------------------------------------------------------------------------- */
function computeRow(row) {
  const scheduled = Number(row.scheduled || 0);
  const received = Number(row.received ?? 0);
  const delivered = Number(row.delivered ?? 0);
  return {
    missing: scheduled - received,
    undelivered: received - delivered,
    compliance: scheduled ? Math.round((delivered / scheduled) * 10000) / 100 : 0,
  };
}

function needsJustification(row) {
  const { missing, undelivered } = computeRow(row);
  return missing > 0 || undelivered > 0 || row.menu_matches === false;
}

function complianceTone(value) {
  if (value >= 95) return "success";
  if (value >= 80) return "warning";
  return "danger";
}

/* --------------------------------------------------------------------------
   Render
   -------------------------------------------------------------------------- */
function renderTotals() {
  const scheduled = rows.reduce((acc, row) => acc + Number(row.scheduled || 0), 0);
  const delivered = rows.reduce((acc, row) => acc + Number(row.delivered || 0), 0);
  const compliance = scheduled ? Math.round((delivered / scheduled) * 10000) / 100 : 0;
  totalsSlot.innerHTML = `
    <div><div class="text-xs text-muted">Programadas</div><div class="text-bold">${formatNumber(scheduled)}</div></div>
    <div><div class="text-xs text-muted">Entregadas</div><div class="text-bold">${formatNumber(delivered)}</div></div>
    <div><div class="text-xs text-muted">Cumplimiento</div>
      <span class="badge badge--${complianceTone(compliance)}">${formatNumber(compliance, 2)}%</span></div>`;
}

function updateRow(index) {
  const row = rows[index];
  const { missing, undelivered, compliance } = computeRow(row);
  const tr = rowsSlot.querySelector(`[data-row="${index}"]`);
  if (!tr) return;

  tr.querySelector("[data-missing]").textContent = formatNumber(Math.max(missing, 0));
  const badge = tr.querySelector("[data-compliance]");
  badge.textContent = `${formatNumber(compliance, 2)}%`;
  badge.className = `badge badge--${complianceTone(compliance)}`;

  const justification = tr.querySelector("[data-justification]");
  const required = needsJustification(row);
  justification.placeholder = required ? "Obligatoria: hay incumplimiento" : "Opcional";
  justification
    .closest(".field")
    .classList.toggle("has-error", required && !justification.value.trim());

  if (undelivered < 0) {
    toast.info("No es posible entregar mas raciones de las recibidas.");
  }
  renderTotals();
}

function render() {
  if (!rows.length) {
    rowsSlot.innerHTML = `<tr><td colspan="11">
      <div class="empty-state">
        <div class="empty-state__icon">${icon("truck", 24)}</div>
        <div class="empty-state__title">No hay programacion para la fecha</div>
        <div class="empty-state__message">Genere la programacion del plan antes de registrar entregas.</div>
      </div></td></tr>`;
    totalsSlot.innerHTML = "";
    return;
  }

  rowsSlot.innerHTML = rows
    .map((row, index) => {
      const { missing, compliance } = computeRow(row);
      return `<tr data-row="${index}">
        <td class="cell-primary">${escapeHtml(row.campus || "")}</td>
        <td>${escapeHtml(row.shift || "-")}</td>
        <td>${escapeHtml(row.complement || "-")}</td>
        <td>${escapeHtml(row.menu || "-")}</td>
        <td class="text-right">${formatNumber(row.scheduled || 0)}</td>
        <td><input class="input" type="number" min="0" data-field="received" value="${row.received ?? ""}"></td>
        <td><input class="input" type="number" min="0" data-field="delivered" value="${row.delivered ?? ""}"></td>
        <td class="text-right" data-missing>${formatNumber(Math.max(missing, 0))}</td>
        <td class="text-right">
          <span class="badge badge--${complianceTone(compliance)}" data-compliance>${formatNumber(compliance, 2)}%</span>
        </td>
        <td>
          <label class="checkbox">
            <input type="checkbox" data-field="menu_matches" ${row.menu_matches === false ? "" : "checked"}>
            <span class="sr-only">Menu corresponde</span>
          </label>
        </td>
        <td>
          <div class="field" style="margin:0">
            <input class="input" type="text" data-field="justification" data-justification
                   value="${escapeHtml(row.justification || "")}" placeholder="Opcional">
            <div class="field__error">Obligatoria cuando hay incumplimiento.</div>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  rowsSlot.querySelectorAll("[data-field]").forEach((control) => {
    const index = Number(control.closest("[data-row]").dataset.row);
    const field = control.dataset.field;
    const event = control.type === "checkbox" ? "change" : "input";
    control.addEventListener(event, () => {
      rows[index][field] = control.type === "checkbox" ? control.checked : control.value;
      if (field === "received" || field === "delivered") rows[index][field] = Number(control.value || 0);
      if (field === "menu_matches") rows[index].menu_matches = control.checked;
      updateRow(index);
    });
  });

  renderTotals();
}

/* --------------------------------------------------------------------------
   Carga y guardado
   -------------------------------------------------------------------------- */
async function load() {
  rowsSlot.innerHTML = `<tr><td colspan="11"><div class="skeleton" style="width:100%"></div></td></tr>`;
  try {
    const params = { date: dateInput.value };
    if (planSelect.value) params.plan = planSelect.value;
    const data = await api.get("/api/pae/planilla-entregas/", params);
    rows = (data.rows || []).map((row) => ({
      ...row,
      received: row.received ?? row.scheduled ?? 0,
      delivered: row.delivered ?? row.scheduled ?? 0,
      menu_matches: true,
      justification: "",
    }));
    render();
  } catch (error) {
    rowsSlot.innerHTML = `<tr><td colspan="11" class="text-sm text-danger">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function save() {
  if (!rows.length) {
    toast.info("No hay filas para guardar.");
    return;
  }
  const pending = rows.find((row) => needsJustification(row) && !String(row.justification || "").trim());
  if (pending) {
    toast.error(`Registre la justificacion de la sede ${pending.campus}: existe incumplimiento.`);
    return;
  }

  const payload = {
    service_date: dateInput.value,
    rows: rows.map((row) => ({
      schedule: row.schedule_id,
      received_rations: Number(row.received || 0),
      delivered_rations: Number(row.delivered || 0),
      menu_matches: row.menu_matches !== false,
      justification: row.justification || "",
    })),
  };

  try {
    const result = await api.post("/api/pae/planilla-entregas/", payload);
    toast.success(`Planilla guardada: ${result.saved} registro(s).`);
    load();
  } catch (error) {
    const detail = error.payload?.errors;
    if (detail) {
      const first = Object.entries(detail)[0];
      const message = Object.values(first[1]).join(" ");
      toast.error(`Fila ${Number(first[0]) + 1}: ${message}`);
    } else {
      toast.error(error.message);
    }
  }
}

dateInput.value = today();
dateInput.addEventListener("change", load);
planSelect.addEventListener("change", load);
$("[data-save-sheet]")?.addEventListener("click", save);

load();
