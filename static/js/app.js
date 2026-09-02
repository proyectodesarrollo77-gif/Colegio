/* ==========================================================================
   PL_SGE - Runtime principal (ES6+)
   Cliente API, notificaciones, drawer, modal, dropdown, tema y navegacion.
   ========================================================================== */

export const PLSGE = {
  version: "1.0.0",
  name: "PL_SGE",
};

/* --------------------------------------------------------------------------
   Utilidades
   -------------------------------------------------------------------------- */
export const $ = (selector, scope = document) => scope.querySelector(selector);
export const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === null || value === undefined || value === false) return;
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "dataset") {
      Object.entries(value).forEach(([dk, dv]) => (node.dataset[dk] = dv));
    } else node.setAttribute(key, value);
  });
  (Array.isArray(children) ? children : [children]).forEach((child) => {
    if (child === null || child === undefined || child === false) return;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  });
  return node;
}

export function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

export const csrfToken = () =>
  getCookie(window.PLSGE_CONFIG?.csrfCookieName || "plsge_csrftoken") ||
  document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
  "";

export function debounce(fn, delay = 320) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return number.toLocaleString("es-CO", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatDate(value, withTime = false) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const options = { year: "numeric", month: "short", day: "2-digit" };
  if (withTime) Object.assign(options, { hour: "2-digit", minute: "2-digit" });
  return date.toLocaleDateString("es-CO", options);
}

export function initials(text) {
  if (!text) return "?";
  return String(text)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function icon(name, size = 18) {
  const paths = window.PLSGE_ICONS || {};
  const path = paths[name] || paths.circle || "";
  return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true">${path}</svg>`;
}

/* --------------------------------------------------------------------------
   Cliente HTTP
   -------------------------------------------------------------------------- */
class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export const api = {
  async request(url, { method = "GET", data = null, params = null, raw = false, headers = {} } = {}) {
    let endpoint = url;
    if (params) {
      const query = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== "")
      ).toString();
      if (query) endpoint += (endpoint.includes("?") ? "&" : "?") + query;
    }

    const options = {
      method,
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest", ...headers },
    };

    if (!["GET", "HEAD"].includes(method)) {
      options.headers["X-CSRFToken"] = csrfToken();
      if (data instanceof FormData) {
        options.body = data;
      } else if (data !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(data);
      }
    }

    progress.start();
    let response;
    try {
      response = await fetch(endpoint, options);
    } catch (error) {
      progress.done();
      throw new ApiError("No fue posible conectar con el servidor.", 0, null);
    }
    progress.done();

    if (raw) return response;

    if (response.status === 204) return null;

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json().catch(() => null)
      : await response.text();

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/auth/login/?next=" + encodeURIComponent(window.location.pathname);
      }
      const detail =
        (payload && (payload.detail || payload.error)) ||
        (response.status === 403 ? "No cuenta con permisos para esta accion." : "Error en la solicitud.");
      throw new ApiError(typeof detail === "string" ? detail : "Error en la solicitud.", response.status, payload);
    }
    return payload;
  },

  get: (url, params) => api.request(url, { method: "GET", params }),
  post: (url, data) => api.request(url, { method: "POST", data }),
  put: (url, data) => api.request(url, { method: "PUT", data }),
  patch: (url, data) => api.request(url, { method: "PATCH", data }),
  delete: (url) => api.request(url, { method: "DELETE" }),

  async download(url, params, filename = "reporte") {
    const response = await api.request(url, { method: "GET", params, raw: true });
    if (!response.ok) {
      toast.error("No fue posible generar el archivo.");
      return;
    }
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = match ? match[1] : filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  },
};

/* --------------------------------------------------------------------------
   Barra de progreso
   -------------------------------------------------------------------------- */
export const progress = {
  bar: null,
  count: 0,
  ensure() {
    if (!this.bar) {
      this.bar = el("div", { class: "route-progress" });
      document.body.appendChild(this.bar);
    }
    return this.bar;
  },
  start() {
    this.count += 1;
    const bar = this.ensure();
    bar.style.opacity = "1";
    bar.style.width = "38%";
    setTimeout(() => {
      if (this.count > 0) bar.style.width = "72%";
    }, 240);
  },
  done() {
    this.count = Math.max(0, this.count - 1);
    if (this.count > 0) return;
    const bar = this.ensure();
    bar.style.width = "100%";
    setTimeout(() => {
      bar.style.opacity = "0";
      setTimeout(() => (bar.style.width = "0"), 220);
    }, 180);
  },
};

/* --------------------------------------------------------------------------
   Toasts
   -------------------------------------------------------------------------- */
export const toast = {
  stack: null,
  ensure() {
    if (!this.stack) {
      this.stack = $(".toast-stack") || el("div", { class: "toast-stack" });
      if (!this.stack.isConnected) document.body.appendChild(this.stack);
    }
    return this.stack;
  },
  show(message, { type = "info", title = "", timeout = 4200 } = {}) {
    const icons = { success: "check", danger: "alert-triangle", warning: "alert-triangle", info: "info" };
    const node = el("div", {
      class: `toast toast--${type}`,
      html: `<span class="toast__icon">${icon(icons[type] || "info", 18)}</span>
             <div class="toast__body">
               ${title ? `<div class="toast__title">${escapeHtml(title)}</div>` : ""}
               <div class="toast__message">${escapeHtml(message)}</div>
             </div>`,
    });
    const close = el("button", {
      class: "icon-btn",
      type: "button",
      html: icon("x", 14),
      onclick: () => dismiss(),
    });
    node.appendChild(close);
    this.ensure().appendChild(node);

    const dismiss = () => {
      node.classList.add("is-leaving");
      setTimeout(() => node.remove(), 220);
    };
    if (timeout) setTimeout(dismiss, timeout);
    return dismiss;
  },
  success: (message, title = "Operacion exitosa") => toast.show(message, { type: "success", title }),
  error: (message, title = "Se presento un error") => toast.show(message, { type: "danger", title, timeout: 6000 }),
  warning: (message, title = "Atencion") => toast.show(message, { type: "warning", title }),
  info: (message, title = "") => toast.show(message, { type: "info", title }),
};

/* --------------------------------------------------------------------------
   Overlay compartido
   -------------------------------------------------------------------------- */
function overlayElement() {
  let overlay = $("#plsge-overlay");
  if (!overlay) {
    overlay = el("div", { class: "overlay", id: "plsge-overlay" });
    document.body.appendChild(overlay);
  }
  return overlay;
}

/* --------------------------------------------------------------------------
   Drawer
   -------------------------------------------------------------------------- */
export class Drawer {
  constructor({ title = "", subtitle = "", wide = false } = {}) {
    this.overlay = overlayElement();
    this.node = el("aside", { class: `drawer${wide ? " drawer--wide" : ""}`, role: "dialog", "aria-modal": "true" });
    this.node.innerHTML = `
      <header class="drawer__header">
        <div style="flex:1;min-width:0">
          <div class="drawer__title" data-drawer-title>${escapeHtml(title)}</div>
          <div class="drawer__subtitle" data-drawer-subtitle>${escapeHtml(subtitle)}</div>
        </div>
        <button class="icon-btn" type="button" data-drawer-close aria-label="Cerrar">${icon("x")}</button>
      </header>
      <div class="drawer__body" data-drawer-body></div>
      <footer class="drawer__footer" data-drawer-footer></footer>`;
    document.body.appendChild(this.node);
    this.body = $("[data-drawer-body]", this.node);
    this.footer = $("[data-drawer-footer]", this.node);
    $("[data-drawer-close]", this.node).addEventListener("click", () => this.close());
    this._onOverlay = () => this.close();
    this._onKey = (event) => event.key === "Escape" && this.close();
  }

  setTitle(title, subtitle = "") {
    $("[data-drawer-title]", this.node).textContent = title;
    $("[data-drawer-subtitle]", this.node).textContent = subtitle;
  }

  open() {
    this.overlay.classList.add("is-open");
    this.node.classList.add("is-open");
    document.body.style.overflow = "hidden";
    this.overlay.addEventListener("click", this._onOverlay);
    document.addEventListener("keydown", this._onKey);
    setTimeout(() => $("input,select,textarea", this.body)?.focus(), 260);
    return this;
  }

  close() {
    this.overlay.classList.remove("is-open");
    this.node.classList.remove("is-open");
    document.body.style.overflow = "";
    this.overlay.removeEventListener("click", this._onOverlay);
    document.removeEventListener("keydown", this._onKey);
    if (typeof this.onClose === "function") this.onClose();
    return this;
  }

  destroy() {
    this.close();
    setTimeout(() => this.node.remove(), 320);
  }
}

/* --------------------------------------------------------------------------
   Modal de confirmacion
   -------------------------------------------------------------------------- */
export function confirmDialog({
  title = "Confirmar accion",
  message = "Esta seguro de realizar esta accion?",
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  tone = "danger",
  iconName = "alert-triangle",
} = {}) {
  return new Promise((resolve) => {
    const overlay = overlayElement();
    const modal = el("div", { class: "modal", role: "dialog", "aria-modal": "true" });
    modal.innerHTML = `
      <div class="modal__header">
        <div class="modal__icon modal__icon--${tone}">${icon(iconName, 22)}</div>
        <div class="modal__title">${escapeHtml(title)}</div>
      </div>
      <div class="modal__body">${escapeHtml(message)}</div>
      <div class="modal__footer">
        <button class="btn btn--secondary" data-cancel type="button">${escapeHtml(cancelText)}</button>
        <button class="btn btn--${tone === "danger" ? "danger" : "primary"}" data-confirm type="button">
          ${escapeHtml(confirmText)}
        </button>
      </div>`;
    document.body.appendChild(modal);
    requestAnimationFrame(() => {
      overlay.classList.add("is-open");
      modal.classList.add("is-open");
    });

    const finish = (value) => {
      overlay.classList.remove("is-open");
      modal.classList.remove("is-open");
      document.removeEventListener("keydown", onKey);
      setTimeout(() => modal.remove(), 240);
      resolve(value);
    };
    const onKey = (event) => {
      if (event.key === "Escape") finish(false);
      if (event.key === "Enter") finish(true);
    };

    $("[data-cancel]", modal).addEventListener("click", () => finish(false));
    $("[data-confirm]", modal).addEventListener("click", () => finish(true));
    overlay.addEventListener("click", () => finish(false), { once: true });
    document.addEventListener("keydown", onKey);
    setTimeout(() => $("[data-confirm]", modal).focus(), 200);
  });
}

/* --------------------------------------------------------------------------
   Dropdowns
   -------------------------------------------------------------------------- */
function initDropdowns() {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-dropdown-toggle]");
    $$(".dropdown.is-open").forEach((dropdown) => {
      if (!trigger || dropdown !== trigger.closest(".dropdown")) dropdown.classList.remove("is-open");
    });
    if (trigger) {
      event.preventDefault();
      trigger.closest(".dropdown")?.classList.toggle("is-open");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") $$(".dropdown.is-open").forEach((d) => d.classList.remove("is-open"));
  });
}

/* --------------------------------------------------------------------------
   Tabs
   -------------------------------------------------------------------------- */
function initTabs() {
  $$("[data-tabs]").forEach((container) => {
    const tabs = $$("[data-tab]", container);
    const panels = $$("[data-tab-panel]", container);
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((item) => item.classList.toggle("is-active", item === tab));
        panels.forEach((panel) =>
          panel.classList.toggle("is-active", panel.dataset.tabPanel === tab.dataset.tab)
        );
        const url = new URL(window.location);
        url.hash = tab.dataset.tab;
        history.replaceState(null, "", url);
      });
    });
    const hash = window.location.hash.replace("#", "");
    if (hash) $(`[data-tab="${hash}"]`, container)?.click();
  });
}

/* --------------------------------------------------------------------------
   Sidebar y tema
   -------------------------------------------------------------------------- */
function initSidebar() {
  const shell = $(".app-shell");
  if (!shell) return;

  const collapsed = localStorage.getItem("plsge:sidebar") === "collapsed";
  if (collapsed) shell.classList.add("is-collapsed");

  $("[data-sidebar-toggle]")?.addEventListener("click", () => {
    shell.classList.toggle("is-collapsed");
    localStorage.setItem("plsge:sidebar", shell.classList.contains("is-collapsed") ? "collapsed" : "expanded");
  });

  const backdrop = el("div", { class: "sidebar-backdrop" });
  shell.appendChild(backdrop);
  const closeMobile = () => shell.classList.remove("is-mobile-open");
  backdrop.addEventListener("click", closeMobile);
  $("[data-menu-toggle]")?.addEventListener("click", () => shell.classList.toggle("is-mobile-open"));

  $$("[data-nav-parent]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const item = button.closest(".nav-item");
      const wasOpen = item.classList.contains("is-open");
      if (!event.metaKey) {
        $$(".nav-item.is-open").forEach((other) => other !== item && other.classList.remove("is-open"));
      }
      item.classList.toggle("is-open", !wasOpen);
    });
  });

  const search = $("[data-nav-search]");
  if (search) {
    search.addEventListener("input", () => {
      const term = search.value.trim().toLowerCase();
      $$(".nav-group").forEach((group) => {
        let groupVisible = false;
        $$(".nav-item", group).forEach((item) => {
          const parentText = $(".nav-link__text", item)?.textContent.toLowerCase() || "";
          const links = $$(".nav-sub__link", item);
          let anyChild = false;
          links.forEach((link) => {
            const visible = !term || link.textContent.toLowerCase().includes(term);
            link.style.display = visible ? "" : "none";
            if (visible) anyChild = true;
          });
          const visible = !term || parentText.includes(term) || anyChild;
          item.style.display = visible ? "" : "none";
          if (visible) groupVisible = true;
          if (term && anyChild) item.classList.add("is-open");
        });
        group.style.display = groupVisible ? "" : "none";
      });
    });
  }
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("plsge:theme", theme);
}

function initTheme() {
  const stored = localStorage.getItem("plsge:theme") || document.documentElement.dataset.theme || "light";
  applyTheme(stored);
  $("[data-theme-toggle]")?.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  });
}

/* --------------------------------------------------------------------------
   Atajos de teclado
   -------------------------------------------------------------------------- */
function initShortcuts() {
  document.addEventListener("keydown", (event) => {
    const inField = ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName);
    if ((event.ctrlKey || event.metaKey) && event.key === "k") {
      event.preventDefault();
      $("[data-nav-search]")?.focus();
    }
    if (!inField && event.key === "n" && $("[data-resource-create]")) {
      event.preventDefault();
      $("[data-resource-create]").click();
    }
  });
}

/* --------------------------------------------------------------------------
   Mensajes del servidor + relojes
   -------------------------------------------------------------------------- */
function initServerMessages() {
  $$("[data-server-message]").forEach((node) => {
    toast.show(node.dataset.serverMessage, { type: node.dataset.serverLevel || "info" });
    node.remove();
  });
}

function initClock() {
  const clock = $("[data-clock]");
  if (!clock) return;
  const tick = () => {
    clock.textContent = new Date().toLocaleString("es-CO", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
  };
  tick();
  setInterval(tick, 30000);
}

/* --------------------------------------------------------------------------
   Notificaciones en la barra superior
   -------------------------------------------------------------------------- */
async function initNotifications() {
  const panel = $("[data-notifications-list]");
  if (!panel) return;
  $("[data-notifications-read-all]")?.addEventListener("click", async () => {
    try {
      await api.post("/api/notifications/mark-all-read/", {});
      $$("[data-notification-item]").forEach((item) => item.classList.add("is-read"));
      const badge = $("[data-notifications-count]");
      if (badge) badge.remove();
      toast.success("Notificaciones marcadas como leidas.");
    } catch (error) {
      toast.error(error.message);
    }
  });
}

/* --------------------------------------------------------------------------
   Arranque
   -------------------------------------------------------------------------- */
export function boot() {
  initDropdowns();
  initTabs();
  initSidebar();
  initTheme();
  initShortcuts();
  initServerMessages();
  initClock();
  initNotifications();
  document.body.classList.add("is-ready");
}

document.addEventListener("DOMContentLoaded", boot);

window.PLSGE = { ...PLSGE, api, toast, confirmDialog, Drawer, $, $$, el, icon, formatDate, formatNumber, applyTheme };
