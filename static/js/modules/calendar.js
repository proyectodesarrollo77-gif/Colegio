/* ==========================================================================
   PL_SGE - Calendario institucional
   ========================================================================== */
import { $, api, escapeHtml, icon, toast } from "../app.js";

const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const state = { year: new Date().getFullYear(), month: new Date().getMonth() + 1, events: [] };

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function firstWeekday(year, month) {
  // Lunes = 0 ... Domingo = 6
  const day = new Date(year, month - 1, 1).getDay();
  return (day + 6) % 7;
}

function renderCalendar() {
  const grid = $("[data-calendar]");
  const heads = Array.from(grid.querySelectorAll(".calendar__head"));
  grid.innerHTML = "";
  heads.forEach((head) => grid.appendChild(head));

  const total = daysInMonth(state.year, state.month);
  const offset = firstWeekday(state.year, state.month);
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === state.year && today.getMonth() + 1 === state.month;

  const previousTotal = daysInMonth(state.year, state.month === 1 ? 12 : state.month - 1);
  for (let i = offset - 1; i >= 0; i -= 1) {
    grid.insertAdjacentHTML(
      "beforeend",
      `<div class="calendar__day is-outside"><span class="calendar__date">${previousTotal - i}</span></div>`
    );
  }

  const byDay = {};
  state.events.forEach((event) => {
    byDay[event.day] = byDay[event.day] || [];
    byDay[event.day].push(event);
  });

  for (let day = 1; day <= total; day += 1) {
    const events = byDay[day] || [];
    const isToday = isCurrentMonth && today.getDate() === day;
    grid.insertAdjacentHTML(
      "beforeend",
      `<div class="calendar__day ${isToday ? "is-today" : ""}">
        <span class="calendar__date">${day}</span>
        ${events
          .slice(0, 3)
          .map(
            (event) => `<span class="calendar__event" data-event-id="${event.id}"
              style="background:${event.color}1f;color:${event.color}" title="${escapeHtml(event.title)}">
              ${escapeHtml(event.time)} ${escapeHtml(event.title)}</span>`
          )
          .join("")}
        ${events.length > 3 ? `<span class="text-2xs text-muted">+${events.length - 3} mas</span>` : ""}
      </div>`
    );
  }

  const remaining = (7 - ((offset + total) % 7)) % 7;
  for (let day = 1; day <= remaining; day += 1) {
    grid.insertAdjacentHTML("beforeend", `<div class="calendar__day is-outside"><span class="calendar__date">${day}</span></div>`);
  }

  $("[data-calendar-title]").textContent = `${MONTHS[state.month - 1]} ${state.year}`;
  $("[data-calendar-count]").textContent = `${state.events.length} eventos publicados`;
}

function renderList() {
  const list = $("[data-calendar-list]");
  if (!state.events.length) {
    list.innerHTML = `<div class="empty-state" style="padding:36px 16px">
      <div class="empty-state__icon">${icon("calendar", 22)}</div>
      <div class="empty-state__title">Sin eventos este mes</div>
      <div class="empty-state__message">Cree eventos desde la administracion de la agenda.</div>
    </div>`;
    return;
  }
  list.innerHTML = state.events
    .map(
      (event) => `<div style="padding:14px 18px;border-bottom:1px solid var(--border-subtle)">
        <div class="row" style="gap:10px;align-items:flex-start">
          <span style="width:8px;height:8px;border-radius:50%;background:${event.color};margin-top:6px"></span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:500;color:var(--text-primary)">${escapeHtml(event.title)}</div>
            <div class="text-xs text-muted">${escapeHtml(event.date)} ${event.all_day ? "· Todo el dia" : `· ${escapeHtml(event.time)}`}
              ${event.place ? `· ${escapeHtml(event.place)}` : ""}</div>
            ${event.description ? `<div class="text-xs text-secondary mt-2">${escapeHtml(event.description)}</div>` : ""}
          </div>
          <span class="badge badge--neutral">${escapeHtml(event.type)}</span>
        </div>
      </div>`
    )
    .join("");
}

async function load() {
  try {
    const data = await api.get("/api/agenda-events/calendar/", { year: state.year, month: state.month });
    state.events = data.events || [];
    renderCalendar();
    renderList();
  } catch (error) {
    toast.error(error.message);
  }
}

function shift(delta) {
  state.month += delta;
  if (state.month > 12) {
    state.month = 1;
    state.year += 1;
  } else if (state.month < 1) {
    state.month = 12;
    state.year -= 1;
  }
  load();
}

document.addEventListener("DOMContentLoaded", () => {
  if (!$("[data-calendar]")) return;
  load();
  $("[data-calendar-prev]")?.addEventListener("click", () => shift(-1));
  $("[data-calendar-next]")?.addEventListener("click", () => shift(1));
  $("[data-calendar-today]")?.addEventListener("click", () => {
    const now = new Date();
    state.year = now.getFullYear();
    state.month = now.getMonth() + 1;
    load();
  });
});
