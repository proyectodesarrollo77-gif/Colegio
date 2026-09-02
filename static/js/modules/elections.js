/* ==========================================================================
   PL_SGE - Votacion digital y resultados electorales
   ========================================================================== */
import { $, $$, api, confirmDialog, escapeHtml, icon, initials, toast } from "../app.js";
import { horizontalBars, palette } from "./charts.js";

const selections = new Map();

/* --------------------------------------------------------------------------
   Tarjeton de votacion
   -------------------------------------------------------------------------- */
function candidateCard(candidate, candidacyId, disabled) {
  const selected = selections.get(candidacyId) === candidate.id;
  const photo = candidate.photo
    ? `<img src="${candidate.photo}" alt="" style="width:100%;height:100%;object-fit:cover">`
    : escapeHtml(initials(candidate.student_name || "VB"));

  return `
    <button type="button" class="card" data-candidate="${candidate.id}" data-candidacy="${candidacyId}"
      ${disabled ? "disabled" : ""}
      style="text-align:left;padding:16px;cursor:${disabled ? "not-allowed" : "pointer"};
             border-color:${selected ? "var(--accent)" : "var(--border-color)"};
             box-shadow:${selected ? "var(--shadow-focus)" : "var(--shadow-xs)"};opacity:${disabled ? 0.6 : 1}">
      <div class="row" style="gap:14px;align-items:flex-start">
        <span class="avatar avatar--lg">${photo}</span>
        <div style="flex:1;min-width:0">
          <div class="row" style="gap:8px">
            <span class="badge badge--brand">${candidate.number}</span>
            <strong style="color:var(--text-primary)">
              ${escapeHtml(candidate.is_blank_vote ? "Voto en blanco" : candidate.student_name || "Candidato")}
            </strong>
          </div>
          ${candidate.group_name ? `<div class="text-xs text-muted mt-2">${escapeHtml(candidate.group_name)}</div>` : ""}
          ${candidate.slogan ? `<div class="text-sm text-secondary mt-2">"${escapeHtml(candidate.slogan)}"</div>` : ""}
          ${candidate.proposals ? `<div class="text-xs text-muted mt-2 truncate">${escapeHtml(candidate.proposals)}</div>` : ""}
        </div>
        <span style="color:${selected ? "var(--accent)" : "var(--text-muted)"}">
          ${icon(selected ? "check" : "circle", 20)}
        </span>
      </div>
    </button>`;
}

function renderBallot(data) {
  const container = $("[data-ballot]");
  const open = data.election.is_open;

  container.innerHTML = data.candidacies
    .map((candidacy) => {
      const approved = (candidacy.candidates || []).filter((c) => c.is_approved || c.is_blank_vote);
      return `
        <div class="card mb-6">
          <div class="card__header">
            <span class="page-header__icon" style="width:34px;height:34px">${icon("vote", 17)}</span>
            <div style="flex:1">
              <div class="card__title">${escapeHtml(candidacy.name)}</div>
              <div class="card__subtitle">${escapeHtml(candidacy.description || "Seleccione una opcion")}</div>
            </div>
            ${candidacy.voted ? '<span class="badge badge--success">Ya voto</span>' : ""}
          </div>
          <div class="card__body">
            ${
              approved.length
                ? `<div class="grid grid-3" data-candidacy-group="${candidacy.id}">
                    ${approved.map((candidate) => candidateCard(candidate, candidacy.id, candidacy.voted || !open)).join("")}
                  </div>`
                : '<div class="text-sm text-muted">No hay candidatos aprobados para este cargo.</div>'
            }
          </div>
        </div>`;
    })
    .join("");

  $$("[data-candidate]", container).forEach((button) => {
    button.addEventListener("click", () => {
      const candidacyId = Number(button.dataset.candidacy);
      const candidateId = Number(button.dataset.candidate);
      selections.set(candidacyId, candidateId);
      renderBallot(data);
      $("[data-cast-vote]").disabled = selections.size === 0;
    });
  });

  $("[data-cast-vote]").disabled = selections.size === 0 || !open;
}

async function loadBallot(electionId) {
  const container = $("[data-ballot]");
  container.innerHTML = '<div class="card"><div class="card__body text-center" style="padding:48px"><span class="spinner spinner--lg"></span></div></div>';
  selections.clear();
  try {
    const data = await api.get(`/api/elections/${electionId}/ballot/`);
    renderBallot(data);
  } catch (error) {
    toast.error(error.message);
    container.innerHTML = `<div class="alert alert--danger">${icon("alert-triangle", 18)}<div>${escapeHtml(error.message)}</div></div>`;
  }
}

async function castVote() {
  const electionId = Number($("[data-election]").value);
  const confirmed = await confirmDialog({
    title: "Confirmar voto",
    message: "Su voto es definitivo y no podra modificarse. Desea continuar?",
    confirmText: "Si, votar",
    tone: "primary",
    iconName: "vote",
  });
  if (!confirmed) return;

  const payload = {};
  selections.forEach((candidateId, candidacyId) => {
    payload[candidacyId] = candidateId;
  });

  try {
    const data = await api.post("/api/elections/cast-vote/", { election: electionId, selections: payload });
    toast.success(`Voto registrado en ${data.registered} cargos. Gracias por participar.`);
    loadBallot(electionId);
  } catch (error) {
    toast.error(error.message);
  }
}

/* --------------------------------------------------------------------------
   Resultados
   -------------------------------------------------------------------------- */
async function loadResults(electionId) {
  const container = $("[data-results]");
  if (!container) return;
  container.innerHTML = '<div class="card"><div class="card__body text-center" style="padding:48px"><span class="spinner spinner--lg"></span></div></div>';
  try {
    const data = await api.get("/api/election-results/", { election: electionId, page_size: 200 });
    const rows = data.results || [];
    if (!rows.length) {
      container.innerHTML = `<div class="card"><div class="empty-state">
        <div class="empty-state__icon">${icon("bar-chart", 24)}</div>
        <div class="empty-state__title">Sin resultados publicados</div>
        <div class="empty-state__message">Consolide el escrutinio desde la configuracion electoral.</div>
      </div></div>`;
      return;
    }

    const byCandidacy = {};
    rows.forEach((row) => {
      byCandidacy[row.candidacy_name] = byCandidacy[row.candidacy_name] || [];
      byCandidacy[row.candidacy_name].push(row);
    });

    container.innerHTML = Object.entries(byCandidacy)
      .map(
        ([name, items], index) => `
        <div class="card mb-6">
          <div class="card__header">
            <span class="page-header__icon" style="width:34px;height:34px">${icon("award", 17)}</span>
            <div style="flex:1">
              <div class="card__title">${escapeHtml(name)}</div>
              <div class="card__subtitle">${items.reduce((acc, item) => acc + item.votes, 0)} votos registrados</div>
            </div>
            ${items[0]?.is_winner ? `<span class="badge badge--success">${icon("star", 12)} Electo: ${escapeHtml(items[0].candidate_name)}</span>` : ""}
          </div>
          <div class="card__body"><div data-chart-result="${index}"></div></div>
        </div>`
      )
      .join("");

    Object.values(byCandidacy).forEach((items, index) => {
      const target = $(`[data-chart-result="${index}"]`);
      if (target) {
        horizontalBars(target, {
          items: items.map((item, position) => ({
            label: `${item.candidate_name} (${item.percentage}%)`,
            value: item.votes,
            color: palette[position % palette.length],
          })),
        });
      }
    });
  } catch (error) {
    toast.error(error.message);
  }
}

/* -- Arranque ------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  const select = $("[data-election]");
  if (select && $("[data-ballot]")) {
    if (select.value) loadBallot(select.value);
    select.addEventListener("change", () => loadBallot(select.value));
    $("[data-cast-vote]")?.addEventListener("click", castVote);
  }

  const resultSelect = $("[data-election-results]");
  if (resultSelect) {
    if (resultSelect.value) loadResults(resultSelect.value);
    resultSelect.addEventListener("change", () => loadResults(resultSelect.value));
    $("[data-consolidate-results]")?.addEventListener("click", async () => {
      try {
        const data = await api.post("/api/election-results/consolidate/", { election: resultSelect.value });
        toast.success(`Escrutinio consolidado: ${data.results} resultados.`);
        loadResults(resultSelect.value);
      } catch (error) {
        toast.error(error.message);
      }
    });
  }
});
