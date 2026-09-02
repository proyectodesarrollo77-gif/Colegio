/**
 * Aplicacion de listas de verificacion del PAE.
 *
 * Presenta los criterios agrupados por categoria, calcula el puntaje ponderado
 * en linea y guarda todas las respuestas en una sola operacion. El resultado
 * definitivo lo recalcula el backend (`PaeVerification.recalculate`).
 */
import { $, api, escapeHtml, formatNumber, icon, toast } from "../app.js";

const select = $("#check-verification");
const bodySlot = $("[data-check-body]");
const resultSlot = $("[data-check-result]");
const observations = $("#check-observations");

const ANSWERS = [
  { value: "CUMPLE", label: "Cumple" },
  { value: "NO_CUMPLE", label: "No cumple" },
  { value: "NO_APLICA", label: "No aplica" },
];

const RESULT_TONE = {
  CUMPLE: "success",
  CUMPLE_PARCIAL: "warning",
  NO_CUMPLE: "danger",
  SIN_EVALUAR: "neutral",
};

let categories = [];
// Umbrales parametrizables; los entrega el backend con cada lista.
let thresholds = { full: 90, partial: 70 };

/* --------------------------------------------------------------------------
   Puntaje (espejo del calculo del backend)
   -------------------------------------------------------------------------- */
function score() {
  let obtained = 0;
  let total = 0;
  let criticalFailure = false;

  categories.forEach((category) =>
    category.items.forEach((item) => {
      if (item.answer === "NO_APLICA") return;
      total += Number(item.weight || 1);
      if (item.answer === "CUMPLE") obtained += Number(item.weight || 1);
      if (item.answer === "NO_CUMPLE" && item.is_critical) criticalFailure = true;
    })
  );

  const percent = total ? Math.round((obtained / total) * 10000) / 100 : 0;
  let result = "SIN_EVALUAR";
  if (total) {
    if (criticalFailure) result = "NO_CUMPLE";
    else if (percent >= thresholds.full) result = "CUMPLE";
    else if (percent >= thresholds.partial) result = "CUMPLE_PARCIAL";
    else result = "NO_CUMPLE";
  }
  return { percent, result, criticalFailure };
}

function renderResult() {
  const { percent, result, criticalFailure } = score();
  const label = { CUMPLE: "Cumple", CUMPLE_PARCIAL: "Cumple parcialmente", NO_CUMPLE: "No cumple", SIN_EVALUAR: "Sin evaluar" }[
    result
  ];
  resultSlot.innerHTML = `
    <span class="badge badge--${RESULT_TONE[result]}">${label} &middot; ${formatNumber(percent, 2)}%</span>
    ${criticalFailure ? '<div class="text-xs text-danger mt-2">Un criterio critico incumplido fuerza el resultado.</div>' : ""}`;
}

/* --------------------------------------------------------------------------
   Render
   -------------------------------------------------------------------------- */
function render() {
  if (!categories.length) {
    bodySlot.innerHTML = `<div class="card"><div class="empty-state">
      <div class="empty-state__icon">${icon("clipboard-check", 26)}</div>
      <div class="empty-state__title">Seleccione una verificacion</div>
      <div class="empty-state__message">
        Cree la verificacion desde Control de calidad y vuelva aqui para aplicar los criterios.
      </div>
    </div></div>`;
    resultSlot.innerHTML = '<span class="badge badge--neutral">Sin evaluar</span>';
    return;
  }

  bodySlot.innerHTML = categories
    .map(
      (category, categoryIndex) => `<div class="card mb-4">
        <div class="card__header">
          <div style="flex:1">
            <div class="card__title">${escapeHtml(category.name)}</div>
            <div class="card__subtitle">${category.items.length} criterio(s)</div>
          </div>
        </div>
        <div class="card__body card__body--flush">
          <div class="table-wrap">
            <table class="table table--compact">
              <thead>
                <tr>
                  <th>Criterio</th>
                  <th style="width:80px" class="text-right">Peso</th>
                  <th style="width:280px">Respuesta</th>
                  <th style="width:260px">Observacion</th>
                </tr>
              </thead>
              <tbody>
                ${category.items
                  .map(
                    (item, itemIndex) => `<tr>
                      <td class="cell-primary">
                        ${escapeHtml(item.criterion)}
                        ${item.is_critical ? '<span class="badge badge--danger">Critico</span>' : ""}
                        ${item.requires_evidence ? '<span class="badge badge--info">Evidencia</span>' : ""}
                      </td>
                      <td class="text-right">${formatNumber(item.weight, 1)}</td>
                      <td>
                        <div class="btn-group" data-answer="${categoryIndex}-${itemIndex}">
                          ${ANSWERS.map(
                            (answer) =>
                              `<button class="btn btn--sm ${
                                item.answer === answer.value ? "btn--primary" : "btn--secondary"
                              }" type="button" data-value="${answer.value}">${answer.label}</button>`
                          ).join("")}
                        </div>
                      </td>
                      <td>
                        <input class="input" type="text" data-observation="${categoryIndex}-${itemIndex}"
                               value="${escapeHtml(item.observation || "")}" placeholder="Observacion">
                      </td>
                    </tr>`
                  )
                  .join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>`
    )
    .join("");

  bodySlot.querySelectorAll("[data-answer] button").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.closest("[data-answer]");
      const [categoryIndex, itemIndex] = group.dataset.answer.split("-").map(Number);
      categories[categoryIndex].items[itemIndex].answer = button.dataset.value;
      group.querySelectorAll("button").forEach((sibling) => {
        sibling.className = `btn btn--sm ${sibling === button ? "btn--primary" : "btn--secondary"}`;
      });
      renderResult();
    });
  });

  bodySlot.querySelectorAll("[data-observation]").forEach((input) => {
    input.addEventListener("input", () => {
      const [categoryIndex, itemIndex] = input.dataset.observation.split("-").map(Number);
      categories[categoryIndex].items[itemIndex].observation = input.value;
    });
  });

  renderResult();
}

/* --------------------------------------------------------------------------
   Carga y guardado
   -------------------------------------------------------------------------- */
async function load() {
  if (!select.value) {
    categories = [];
    render();
    return;
  }
  try {
    const data = await api.get("/api/pae/hoja-verificacion/", { verification: select.value });
    categories = data.categories || [];
    thresholds = data.thresholds || thresholds;
    observations.value = data.verification?.observations || "";
    render();
  } catch (error) {
    toast.error(error.message);
  }
}

async function save() {
  if (!select.value) {
    toast.info("Seleccione la verificacion a aplicar.");
    return;
  }
  const entries = categories.flatMap((category) =>
    category.items
      .filter((item) => item.answer)
      .map((item) => ({
        item: item.item_id,
        answer: item.answer,
        observation: item.observation || "",
      }))
  );
  if (!entries.length) {
    toast.error("Responda al menos un criterio.");
    return;
  }

  try {
    const result = await api.post("/api/pae/hoja-verificacion/", {
      verification: Number(select.value),
      entries,
      observations: observations.value,
    });
    const verification = result.verification || {};
    toast.success(`Criterios guardados: ${result.saved}.`);
    resultSlot.innerHTML = `<span class="badge badge--${RESULT_TONE[verification.result] || "neutral"}">
      ${escapeHtml(verification.result_display || verification.result || "")} &middot;
      ${formatNumber(verification.score || 0, 2)}%</span>`;
  } catch (error) {
    toast.error(error.message);
  }
}

select.addEventListener("change", load);
$("[data-save-checklist]")?.addEventListener("click", save);

const params = new URLSearchParams(window.location.search);
if (params.get("verification")) select.value = params.get("verification");
load();
