/* ==========================================================================
   PL_SGE - Dashboard institucional
   ========================================================================== */
import { $, api, escapeHtml, formatNumber, icon, toast } from "./app.js";
import { barChart, donutChart, lineChart, palette } from "./modules/charts.js";

let cache = null;

/* -- Indicadores ---------------------------------------------------------- */
function renderKpis(cards) {
  const grid = $("[data-kpi-grid]");
  if (!grid) return;
  grid.innerHTML = cards
    .map((card) => {
      const current = Number(card.value) || 0;
      const previous = Number(card.previous) || 0;
      let trend = "flat";
      let variation = 0;
      if (previous > 0) {
        variation = ((current - previous) / previous) * 100;
        trend = variation > 0.5 ? "up" : variation < -0.5 ? "down" : "flat";
      }
      const arrow = trend === "up" ? "trending-up" : trend === "down" ? "trending-down" : "activity";
      return `
        <a class="stat-card" href="${escapeHtml(card.url || "#")}">
          <div class="stat-card__top">
            <span class="stat-card__label">${escapeHtml(card.label)}</span>
            <span class="stat-card__icon" style="background:${card.color}18;color:${card.color}">
              ${icon(card.icon, 18)}
            </span>
          </div>
          <div class="stat-card__value">${formatNumber(current, Number.isInteger(current) ? 0 : 2)}${card.suffix || ""}</div>
          <div class="stat-card__meta">
            <span class="stat-card__trend stat-card__trend--${trend}">
              ${icon(arrow, 12)} ${variation ? `${Math.abs(variation).toFixed(1)}%` : "estable"}
            </span>
            <span>frente al periodo anterior</span>
          </div>
        </a>`;
    })
    .join("");
}

/* -- Alertas -------------------------------------------------------------- */
function renderAlerts(alerts) {
  const container = $("[data-alerts]");
  if (!container) return;
  if (!alerts.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = alerts
    .map(
      (alert) => `
      <a class="alert alert--${alert.level}" href="${escapeHtml(alert.url)}" style="text-decoration:none">
        ${icon(alert.icon || "info", 18)}
        <div style="flex:1">
          <div class="alert__title">${escapeHtml(alert.title)}</div>
          <div class="text-xs">${escapeHtml(alert.message)}</div>
        </div>
        ${icon("chevron-right", 16)}
      </a>`
    )
    .join("");
}

/* -- Accesos rapidos ------------------------------------------------------ */
function renderQuickActions(actions) {
  const container = $("[data-quick-actions]");
  if (!container) return;
  if (!actions.length) {
    container.innerHTML = '<div class="text-sm text-muted">No hay acciones disponibles para su perfil.</div>';
    return;
  }
  container.innerHTML = actions
    .map(
      (action) => `
      <a class="card" href="${escapeHtml(action.url)}" style="display:flex;align-items:center;gap:12px;padding:14px 16px;box-shadow:none">
        <span class="page-header__icon" style="width:34px;height:34px">${icon(action.icon, 17)}</span>
        <span style="font-size:var(--text-sm);font-weight:500;color:var(--text-primary)">${escapeHtml(action.label)}</span>
      </a>`
    )
    .join("");
}

/* -- Paneles por rol ------------------------------------------------------ */
function renderTeacherPanel(data) {
  if (!data) return "";
  const rows = data.grade_progress
    .map(
      (item) => `
      <tr>
        <td class="cell-primary">${escapeHtml(item.subject)}</td>
        <td>${escapeHtml(item.group)}</td>
        <td style="text-align:center">${item.recorded} / ${item.expected}</td>
        <td>
          <div class="row" style="gap:10px">
            <div class="progress progress--sm" style="flex:1">
              <div class="progress__bar progress__bar--${item.progress >= 100 ? "success" : item.progress >= 50 ? "warning" : "danger"}"
                   style="width:${Math.min(item.progress, 100)}%"></div>
            </div>
            <span class="text-xs" style="width:40px;text-align:right">${item.progress}%</span>
          </div>
        </td>
        <td class="cell-actions">
          <a class="btn btn--ghost btn--sm" href="/evaluaciones/notas/?assignment=${item.assignment}">Digitar</a>
        </td>
      </tr>`
    )
    .join("");

  return `
    <div class="card">
      <div class="card__header">
        <span class="page-header__icon" style="width:32px;height:32px">${icon("presentation", 16)}</span>
        <div style="flex:1">
          <div class="card__title">Mi carga academica</div>
          <div class="card__subtitle">${escapeHtml(data.teacher)} &middot; ${data.assignments} asignaciones &middot;
            ${data.students} estudiantes &middot; ${data.hours} horas semanales</div>
        </div>
      </div>
      <div class="card__body card__body--flush">
        <div class="table-wrap">
          <table class="table table--stack">
            <thead><tr>
              <th>Asignatura</th><th>Grupo</th><th style="text-align:center">Notas</th>
              <th>Avance de digitacion</th><th></th>
            </tr></thead>
            <tbody>${rows || '<tr><td colspan="5" class="text-muted">Sin asignaciones registradas.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    </div>`;
}

function renderStudentPanel(data) {
  if (!data) return "";
  const rows = data.subjects
    .map(
      (item) => `
      <tr>
        <td class="cell-primary">${escapeHtml(item.subject)}</td>
        <td>${escapeHtml(item.period || "")}</td>
        <td style="text-align:center"><strong class="${item.score >= 3 ? "text-success" : "text-danger"}">${item.score.toFixed(1)}</strong></td>
        <td>${escapeHtml(item.performance || "")}</td>
      </tr>`
    )
    .join("");

  return `
    <div class="card">
      <div class="card__header">
        <span class="page-header__icon" style="width:32px;height:32px">${icon("graduation-cap", 16)}</span>
        <div style="flex:1">
          <div class="card__title">Mi desempeno academico</div>
          <div class="card__subtitle">${escapeHtml(data.student)} &middot; Grupo ${escapeHtml(data.group)} &middot;
            Promedio ${data.average} &middot; ${data.failing} asignaturas en riesgo</div>
        </div>
      </div>
      <div class="card__body card__body--flush">
        <div class="table-wrap">
          <table class="table table--stack">
            <thead><tr><th>Asignatura</th><th>Periodo</th><th style="text-align:center">Nota</th><th>Desempeno</th></tr></thead>
            <tbody>${rows || '<tr><td colspan="4" class="text-muted">Aun no hay notas publicadas.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    </div>`;
}

/* -- Graficas ------------------------------------------------------------- */
function renderCharts(charts) {
  const enrollment = $("[data-chart-enrollment]");
  if (enrollment) {
    if (charts.enrollment_by_grade.labels.length) {
      barChart(enrollment, {
        labels: charts.enrollment_by_grade.labels,
        series: [{ name: "Estudiantes", data: charts.enrollment_by_grade.data, color: palette[0] }],
        height: 280,
      });
    } else {
      enrollment.innerHTML = emptyChart("Sin matriculas registradas");
    }
  }

  const average = $("[data-chart-average]");
  if (average) {
    if (charts.average_by_period.labels.length) {
      lineChart(average, {
        labels: charts.average_by_period.labels,
        series: [{ name: "Promedio", data: charts.average_by_period.data, color: palette[2] }],
        height: 260,
        formatter: (value) => Number(value).toFixed(1),
      });
    } else {
      average.innerHTML = emptyChart("Aun no hay notas consolidadas");
    }
  }

  const performance = $("[data-chart-performance]");
  if (performance) {
    if (charts.performance.length) {
      const total = charts.performance.reduce((acc, item) => acc + item.value, 0);
      donutChart(performance, {
        items: charts.performance,
        size: 180,
        centerValue: formatNumber(total),
        centerLabel: "valoraciones",
      });
    } else {
      performance.innerHTML = emptyChart("Sin valoraciones registradas");
    }
  }

  const access = $("[data-chart-access]");
  if (access) {
    if (charts.access_trend.labels.length) {
      lineChart(access, {
        labels: charts.access_trend.labels,
        series: [{ name: "Ingresos", data: charts.access_trend.data, color: palette[1] }],
        height: 260,
      });
    } else {
      access.innerHTML = emptyChart("Sin accesos en el periodo");
    }
  }
}

function emptyChart(message) {
  return `<div class="empty-state" style="padding:36px 0">
    <div class="empty-state__icon">${icon("bar-chart", 22)}</div>
    <div class="empty-state__message">${escapeHtml(message)}</div>
  </div>`;
}

/* -- Carga ---------------------------------------------------------------- */
async function load() {
  try {
    const data = await api.get("/api/dashboard/");
    cache = data;
    renderAlerts(data.alerts || []);
    renderKpis(data.cards || []);
    renderQuickActions(data.quick_actions || []);
    renderCharts(data.charts || {});

    const panel = $("[data-role-panel]");
    if (panel) {
      panel.innerHTML = data.teacher ? renderTeacherPanel(data.teacher) : data.student ? renderStudentPanel(data.student) : "";
    }
  } catch (error) {
    toast.error(error.message || "No fue posible cargar el dashboard.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  load();
  $("[data-dashboard-refresh]")?.addEventListener("click", () => {
    load();
    toast.info("Indicadores actualizados.");
  });
  window.addEventListener("resize", () => {
    if (cache) renderCharts(cache.charts || {});
  });
});
