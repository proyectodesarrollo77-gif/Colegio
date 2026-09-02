/**
 * Tablero del PAE.
 *
 * Reutiliza el cliente `api`, el sistema de iconos y las graficas SVG propias
 * de la plataforma (`modules/charts.js`). No define paleta ni colores nuevos:
 * los tonos provienen de `charts.js` y de las variables del design system.
 */
import { $, $$, api, escapeHtml, formatNumber, icon, toast } from "../app.js";
import { barChart, donutChart, horizontalBars, lineChart, palette } from "./charts.js";

const state = { campus: "", shift: "", operator: "", date_from: "", date_to: "" };

/* --------------------------------------------------------------------------
   Tarjetas
   -------------------------------------------------------------------------- */
function renderCards(cards) {
  const slot = $("[data-pae-cards]");
  if (!slot) return;
  if (!cards.length) {
    slot.innerHTML = `<div class="card" style="grid-column:1/-1">
      <div class="empty-state">
        <div class="empty-state__icon">${icon("utensils", 26)}</div>
        <div class="empty-state__title">Sin informacion para la vigencia</div>
        <div class="empty-state__message">Configure la vigencia del PAE y registre beneficiarios y entregas.</div>
      </div>
    </div>`;
    return;
  }

  slot.innerHTML = cards
    .map((card) => {
      const value = card.suffix === "%" ? `${formatNumber(card.value, 1)}%` : formatNumber(card.value);
      let meta = "";
      if (card.goal !== undefined && card.goal !== null) {
        const reached = Number(card.value) >= Number(card.goal);
        meta = `<span class="stat-card__trend stat-card__trend--${reached ? "up" : "down"}">
                  ${icon(reached ? "trending-up" : "trending-down", 13)} meta ${formatNumber(card.goal, 1)}%
                </span>`;
      }
      return `<a class="stat-card" href="${escapeHtml(card.url || "#")}">
        <div class="stat-card__top">
          <span class="stat-card__label">${escapeHtml(card.label)}</span>
          <span class="stat-card__icon">${icon(card.icon || "activity", 18)}</span>
        </div>
        <div class="stat-card__value">${value}</div>
        <div class="stat-card__meta">${meta}</div>
      </a>`;
    })
    .join("");
}

/* --------------------------------------------------------------------------
   Alertas
   -------------------------------------------------------------------------- */
function renderAlerts(alerts) {
  const slot = $("[data-pae-alerts]");
  if (!slot) return;
  if (!alerts.length) {
    slot.innerHTML = `<div class="empty-state">
      <div class="empty-state__icon">${icon("check", 24)}</div>
      <div class="empty-state__title">Sin alertas activas</div>
      <div class="empty-state__message">La operacion del programa esta al dia.</div>
    </div>`;
    return;
  }
  slot.innerHTML = alerts
    .map(
      (alert) => `<a class="dropdown__item" href="${escapeHtml(alert.url || "#")}"
         style="align-items:flex-start;padding:12px 16px;border-bottom:1px solid var(--border-subtle)">
        <span class="badge badge--${escapeHtml(alert.level || "info")}" style="margin-top:2px">
          ${icon(alert.icon || "alert-triangle", 13)}
        </span>
        <span style="flex:1;min-width:0">
          <span style="display:block;color:var(--text-primary);font-weight:500">${escapeHtml(alert.title)}</span>
          <span class="text-xs text-muted">${escapeHtml(alert.message || "")}</span>
        </span>
      </a>`
    )
    .join("");
}

/* --------------------------------------------------------------------------
   Graficas
   -------------------------------------------------------------------------- */
function chartSlot(name) {
  return $(`[data-pae-chart="${name}"]`);
}

function emptyChart(node, message) {
  node.innerHTML = `<div class="text-sm text-muted text-center" style="padding:36px 0">${escapeHtml(message)}</div>`;
}

function renderCharts(charts) {
  const rations = chartSlot("rations");
  if (rations) {
    const data = charts.rations || { labels: [], scheduled: [], delivered: [] };
    if (!data.labels.length) emptyChart(rations, "Aun no hay entregas registradas.");
    else
      barChart(rations, {
        labels: data.labels,
        series: [
          { name: "Programadas", data: data.scheduled, color: palette[0] },
          { name: "Entregadas", data: data.delivered, color: palette[1] },
        ],
        height: 280,
        formatter: (value) => formatNumber(value),
      });
  }

  const monthly = chartSlot("monthly_compliance");
  if (monthly) {
    const data = charts.monthly_compliance || { labels: [], data: [] };
    if (!data.labels.length) emptyChart(monthly, "Sin datos mensuales de cumplimiento.");
    else
      lineChart(monthly, {
        labels: data.labels,
        series: [{ name: "Cumplimiento", data: data.data, color: palette[2] }],
        height: 260,
        formatter: (value) => `${value}%`,
      });
  }

  const byCampus = chartSlot("beneficiaries_by_campus");
  if (byCampus) {
    const data = charts.beneficiaries_by_campus || { labels: [], data: [] };
    if (!data.labels.length) emptyChart(byCampus, "Sin beneficiarios vinculados.");
    else
      donutChart(byCampus, {
        items: data.labels.map((label, index) => ({ label, value: data.data[index] })),
        centerLabel: "Beneficiarios",
        centerValue: formatNumber(data.data.reduce((acc, value) => acc + value, 0)),
      });
  }

  [
    ["incidents_by_type", "Sin novedades registradas."],
    ["incidents_by_status", "Sin novedades registradas."],
    ["findings_by_severity", "Sin hallazgos registrados."],
  ].forEach(([name, message]) => {
    const node = chartSlot(name);
    if (!node) return;
    const data = charts[name] || { labels: [], data: [] };
    if (!data.labels.length) emptyChart(node, message);
    else
      horizontalBars(node, {
        items: data.labels.map((label, index) => ({ label, value: data.data[index] })),
        formatter: (value) => formatNumber(value),
      });
  });

  const operators = chartSlot("compliance_by_operator");
  if (operators) {
    const data = charts.compliance_by_operator || { labels: [], data: [] };
    if (!data.labels.length) emptyChart(operators, "Sin entregas asociadas a un operador.");
    else
      horizontalBars(operators, {
        items: data.labels.map((label, index) => ({ label, value: data.data[index] })),
        formatter: (value) => `${value}%`,
      });
  }
}

/* --------------------------------------------------------------------------
   Carga
   -------------------------------------------------------------------------- */
async function load() {
  try {
    const params = Object.fromEntries(Object.entries(state).filter(([, value]) => value));
    const data = await api.get("/api/pae/dashboard/", params);
    renderCards(data.cards || []);
    renderAlerts(data.alerts || []);
    renderCharts(data.charts || {});
  } catch (error) {
    toast.error(error.message);
  }
}

$$("[data-pae-filter]").forEach((control) =>
  control.addEventListener("change", () => {
    state[control.dataset.paeFilter] = control.value;
    load();
  })
);

$("[data-pae-notify]")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const result = await api.post("/api/pae/alertas/", {});
    toast.success(`Notificaciones enviadas: ${result.notifications ?? 0}`);
  } catch (error) {
    toast.error(error.message);
  } finally {
    button.disabled = false;
  }
});

window.addEventListener("resize", () => {
  clearTimeout(window.__paeResize);
  window.__paeResize = setTimeout(load, 320);
});

load();
