/* ==========================================================================
   PL_SGE - Motor generico de paginas de recurso (tabla + formulario)
   ========================================================================== */
import {
  $,
  $$,
  api,
  confirmDialog,
  debounce,
  Drawer,
  el,
  escapeHtml,
  formatDate,
  formatNumber,
  icon,
  initials,
  toast,
} from "../app.js";

const optionsCache = new Map();

async function loadOptions(endpoint) {
  if (optionsCache.has(endpoint)) return optionsCache.get(endpoint);
  const promise = api
    .get(endpoint)
    .then((data) => (Array.isArray(data) ? data : data.results || []))
    .catch(() => []);
  optionsCache.set(endpoint, promise);
  return promise;
}

export function clearOptionsCache() {
  optionsCache.clear();
}

/* --------------------------------------------------------------------------
   Renderizado de celdas
   -------------------------------------------------------------------------- */
function resolvePath(object, path) {
  return path.split(".").reduce((acc, key) => (acc === null || acc === undefined ? acc : acc[key]), object);
}

function renderCell(column, row) {
  const raw = resolvePath(row, column.field);
  switch (column.type) {
    case "badge": {
      const map = column.map || {};
      const entry = map[raw] || {};
      const label = entry.label || row[`${column.field}_display`] || raw || "-";
      const tone = entry.tone || column.tone || "neutral";
      if (raw === null || raw === undefined || raw === "") return '<span class="text-muted">-</span>';
      return `<span class="badge badge--${tone}">${escapeHtml(label)}</span>`;
    }
    case "boolean":
      return raw
        ? '<span class="badge badge--success"><span class="badge__dot"></span>Si</span>'
        : '<span class="badge badge--neutral"><span class="badge__dot"></span>No</span>';
    case "date":
      return escapeHtml(formatDate(raw));
    case "datetime":
      return escapeHtml(formatDate(raw, true));
    case "number":
      return `<span class="text-mono">${formatNumber(raw, column.decimals || 0)}</span>`;
    case "grade": {
      if (raw === null || raw === undefined || raw === "") return '<span class="text-muted">-</span>';
      const value = Number(raw);
      const threshold = column.passing ?? 3;
      const tone = value >= threshold ? "text-success" : "text-danger";
      return `<strong class="${tone}">${value.toFixed(column.decimals ?? 1)}</strong>`;
    }
    case "percent": {
      const value = Number(raw || 0);
      const tone = value >= 80 ? "success" : value >= 50 ? "warning" : "danger";
      return `<div class="row" style="gap:8px">
        <div class="progress progress--sm" style="width:70px"><div class="progress__bar progress__bar--${tone}" style="width:${Math.min(
        value,
        100
      )}%"></div></div>
        <span class="text-xs">${value.toFixed(0)}%</span></div>`;
    }
    case "avatar": {
      const label = raw || "-";
      const sub = column.subfield ? resolvePath(row, column.subfield) : "";
      return `<div class="row" style="gap:10px">
        <span class="avatar avatar--sm">${escapeHtml(initials(label))}</span>
        <div style="min-width:0"><div class="truncate" style="font-weight:500;color:var(--text-primary)">${escapeHtml(
          label
        )}</div>${sub ? `<div class="text-xs text-muted truncate">${escapeHtml(sub)}</div>` : ""}</div>
      </div>`;
    }
    case "link":
      return `<a href="${escapeHtml((column.url || "#").replace("{id}", row.id))}">${escapeHtml(raw || "-")}</a>`;
    case "mono":
      return `<span class="text-mono">${escapeHtml(raw ?? "-")}</span>`;
    case "color":
      return `<span class="row" style="gap:8px"><span style="width:14px;height:14px;border-radius:4px;background:${escapeHtml(
        raw || "#ccc"
      )};display:inline-block"></span><span class="text-mono">${escapeHtml(raw || "")}</span></span>`;
    case "truncate":
      return `<span class="truncate" style="display:block;max-width:${column.width || 280}px" title="${escapeHtml(
        raw || ""
      )}">${escapeHtml(raw ?? "-")}</span>`;
    default: {
      if (raw === null || raw === undefined || raw === "") return '<span class="text-muted">-</span>';
      return escapeHtml(String(raw));
    }
  }
}

/* --------------------------------------------------------------------------
   Construccion de campos de formulario
   -------------------------------------------------------------------------- */
async function buildField(field, value) {
  const width = { full: "col-12", half: "col-6", third: "col-4", quarter: "col-3" }[field.col || "full"] || "col-12";
  const wrapper = el("div", { class: `field ${width}`, dataset: { fieldName: field.name } });
  const required = field.required ? '<span class="required">*</span>' : "";

  if (field.type === "section") {
    wrapper.className = "col-12";
    wrapper.innerHTML = `<div style="border-top:1px solid var(--border-subtle);margin:8px 0 4px;padding-top:14px">
      <div class="text-bold">${escapeHtml(field.label)}</div>
      ${field.hint ? `<div class="field__hint">${escapeHtml(field.hint)}</div>` : ""}</div>`;
    return wrapper;
  }

  const label = el("label", {
    class: "field__label",
    html: `${escapeHtml(field.label)}${required}`,
    for: `f_${field.name}`,
  });
  wrapper.appendChild(label);

  let input;
  const currentValue = value === null || value === undefined ? field.default ?? "" : value;

  switch (field.type) {
    case "textarea":
      input = el("textarea", {
        class: "textarea",
        id: `f_${field.name}`,
        name: field.name,
        rows: field.rows || 4,
        placeholder: field.placeholder || "",
      });
      input.value = currentValue ?? "";
      break;

    case "select": {
      input = el("select", { class: "select", id: `f_${field.name}`, name: field.name });
      if (!field.required) input.appendChild(el("option", { value: "", text: field.placeholder || "Seleccione..." }));
      (field.options || []).forEach((option) => {
        const node = el("option", { value: option.value, text: option.label });
        if (String(option.value) === String(currentValue)) node.selected = true;
        input.appendChild(node);
      });
      break;
    }

    case "remote": {
      input = el("select", { class: "select", id: `f_${field.name}`, name: field.name });
      input.appendChild(el("option", { value: "", text: "Cargando..." }));
      const options = await loadOptions(field.endpoint);
      input.innerHTML = "";
      if (!field.required) input.appendChild(el("option", { value: "", text: field.placeholder || "Seleccione..." }));
      options.forEach((option) => {
        const node = el("option", { value: option.id, text: option.label });
        if (String(option.id) === String(currentValue)) node.selected = true;
        input.appendChild(node);
      });
      break;
    }

    case "boolean": {
      wrapper.innerHTML = "";
      const switchLabel = el("label", { class: "switch" });
      input = el("input", { type: "checkbox", id: `f_${field.name}`, name: field.name });
      input.checked = Boolean(currentValue);
      switchLabel.append(input, el("span", { class: "switch__track" }), el("span", { text: field.label }));
      wrapper.appendChild(switchLabel);
      if (field.hint) wrapper.appendChild(el("div", { class: "field__hint", text: field.hint }));
      wrapper.appendChild(el("div", { class: "field__error" }));
      return wrapper;
    }

    case "file":
    case "image":
      input = el("input", {
        type: "file",
        class: "input",
        id: `f_${field.name}`,
        name: field.name,
        accept: field.type === "image" ? "image/*" : field.accept || "",
        style: "padding-top:7px",
      });
      break;

    default:
      input = el("input", {
        type: field.type || "text",
        class: "input",
        id: `f_${field.name}`,
        name: field.name,
        placeholder: field.placeholder || "",
        step: field.step || (field.type === "number" ? "any" : null),
        min: field.min ?? null,
        max: field.max ?? null,
        maxlength: field.maxlength ?? null,
      });
      input.value = currentValue ?? "";
  }

  if (field.required) input.required = true;
  if (field.readonly) input.readOnly = true;
  wrapper.appendChild(input);
  if (field.hint) wrapper.appendChild(el("div", { class: "field__hint", text: field.hint }));
  wrapper.appendChild(el("div", { class: "field__error" }));
  return wrapper;
}

function collectForm(form, fields) {
  const hasFile = fields.some((f) => ["file", "image"].includes(f.type));
  const payload = hasFile ? new FormData() : {};

  fields.forEach((field) => {
    if (field.type === "section") return;
    const input = form.querySelector(`[name="${field.name}"]`);
    if (!input) return;

    let value;
    if (field.type === "boolean") value = input.checked;
    else if (["file", "image"].includes(field.type)) value = input.files[0] || null;
    else value = input.value;

    if (["file", "image"].includes(field.type)) {
      if (value && hasFile) payload.append(field.name, value);
      return;
    }
    if (value === "" && !field.required) value = field.nullable === false ? "" : null;

    if (hasFile) {
      payload.append(field.name, value === null ? "" : value);
    } else {
      payload[field.name] = value;
    }
  });
  return payload;
}

/* --------------------------------------------------------------------------
   ResourceTable
   -------------------------------------------------------------------------- */
export class ResourceTable {
  constructor(config, root) {
    this.config = config;
    this.root = root;
    this.state = {
      page: 1,
      pageSize: config.pageSize || 25,
      search: "",
      ordering: config.ordering || "",
      filters: {},
      count: 0,
      numPages: 1,
      rows: [],
      loading: false,
    };
    this.drawer = null;
    this.render();
    this.load();
  }

  /* ---- Estructura ---- */
  render() {
    const { config } = this;
    this.root.innerHTML = `
      <div class="card">
        <div class="table-toolbar">
          <div class="input-group">
            <span class="input-group__icon">${icon("search", 16)}</span>
            <input class="input" type="search" data-search placeholder="${escapeHtml(
              config.searchPlaceholder || "Buscar..."
            )}" autocomplete="off">
          </div>
          <div class="row row-wrap" data-filters></div>
          <div class="spacer"></div>
          <div class="row" data-toolbar-actions></div>
        </div>
        <div class="table-wrap">
          <table class="table table--stack">
            <thead data-thead></thead>
            <tbody data-tbody></tbody>
          </table>
        </div>
        <div data-state-slot></div>
        <div class="table-footer">
          <div data-summary class="text-xs text-muted"></div>
          <div class="row">
            <select class="select" data-page-size style="width:auto;height:30px;font-size:var(--text-xs)">
              <option value="10">10 / pagina</option>
              <option value="25" selected>25 / pagina</option>
              <option value="50">50 / pagina</option>
              <option value="100">100 / pagina</option>
            </select>
            <div class="pagination" data-pagination></div>
          </div>
        </div>
      </div>`;

    this.thead = $("[data-thead]", this.root);
    this.tbody = $("[data-tbody]", this.root);
    this.stateSlot = $("[data-state-slot]", this.root);
    this.summary = $("[data-summary]", this.root);
    this.paginationNode = $("[data-pagination]", this.root);

    this.renderHead();
    this.renderFilters();
    this.renderToolbarActions();

    $("[data-search]", this.root).addEventListener(
      "input",
      debounce((event) => {
        this.state.search = event.target.value.trim();
        this.state.page = 1;
        this.load();
      }, 340)
    );

    $("[data-page-size]", this.root).addEventListener("change", (event) => {
      this.state.pageSize = Number(event.target.value);
      this.state.page = 1;
      this.load();
    });
  }

  renderHead() {
    const columns = this.config.columns
      .map((column) => {
        const sortable = column.sortable !== false && !column.field.includes(".");
        const isSorted = this.state.ordering.replace("-", "") === column.field;
        const direction = this.state.ordering.startsWith("-") ? "desc" : "asc";
        return `<th class="${sortable ? "is-sortable" : ""} ${isSorted ? "is-sorted" : ""}"
          ${sortable ? `data-sort="${escapeHtml(column.field)}"` : ""}
          style="${column.width ? `width:${column.width}px;` : ""}${column.align ? `text-align:${column.align};` : ""}">
          ${escapeHtml(column.label)}
          ${sortable ? `<span class="sort-indicator">${isSorted ? (direction === "asc" ? "&#9650;" : "&#9660;") : "&#8645;"}</span>` : ""}
        </th>`;
      })
      .join("");

    const hasActions = this.config.allow.edit || this.config.allow.delete || (this.config.rowActions || []).length;
    this.thead.innerHTML = `<tr>${columns}${hasActions ? '<th style="width:1%"></th>' : ""}</tr>`;

    $$("[data-sort]", this.thead).forEach((th) => {
      th.addEventListener("click", () => {
        const field = th.dataset.sort;
        this.state.ordering = this.state.ordering === field ? `-${field}` : field;
        this.state.page = 1;
        this.renderHead();
        this.load();
      });
    });
  }

  renderFilters() {
    const container = $("[data-filters]", this.root);
    (this.config.filters || []).forEach((filter) => {
      if (filter.type === "remote") {
        const select = el("select", { class: "select", style: "width:auto;min-width:150px" });
        select.appendChild(el("option", { value: "", text: filter.label }));
        loadOptions(filter.endpoint).then((options) => {
          options.forEach((option) => select.appendChild(el("option", { value: option.id, text: option.label })));
        });
        select.addEventListener("change", () => {
          this.state.filters[filter.name] = select.value;
          this.state.page = 1;
          this.load();
        });
        container.appendChild(select);
        return;
      }
      const select = el("select", { class: "select", style: "width:auto;min-width:140px" });
      select.appendChild(el("option", { value: "", text: filter.label }));
      (filter.options || []).forEach((option) =>
        select.appendChild(el("option", { value: option.value, text: option.label }))
      );
      select.addEventListener("change", () => {
        this.state.filters[filter.name] = select.value;
        this.state.page = 1;
        this.load();
      });
      container.appendChild(select);
    });
  }

  renderToolbarActions() {
    const container = $("[data-toolbar-actions]", this.root);
    container.innerHTML = "";

    container.appendChild(
      el("button", {
        class: "icon-btn",
        type: "button",
        title: "Actualizar",
        html: icon("refresh", 16),
        onclick: () => this.load(),
      })
    );

    if (this.config.allow.export) {
      const dropdown = el("div", { class: "dropdown" });
      dropdown.innerHTML = `
        <button class="btn btn--secondary btn--sm" type="button" data-dropdown-toggle>
          ${icon("download", 15)} Exportar
        </button>
        <div class="dropdown__menu">
          <button class="dropdown__item" type="button" data-export="xlsx">${icon("save", 16)} Excel (.xlsx)</button>
          <button class="dropdown__item" type="button" data-export="csv">${icon("file-text", 16)} CSV (.csv)</button>
          <button class="dropdown__item" type="button" data-print>${icon("printer", 16)} Imprimir</button>
        </div>`;
      $$("[data-export]", dropdown).forEach((button) =>
        button.addEventListener("click", () => this.export(button.dataset.export))
      );
      $("[data-print]", dropdown).addEventListener("click", () => window.print());
      container.appendChild(dropdown);
    }

    if (this.config.allow.create) {
      container.appendChild(
        el("button", {
          class: "btn btn--primary btn--sm",
          type: "button",
          "data-resource-create": "1",
          html: `${icon("plus", 16)} Nuevo`,
          onclick: () => this.openForm(),
        })
      );
    }
  }

  /* ---- Datos ---- */
  query() {
    const params = {
      ...(this.config.baseParams || {}),
      page: this.state.page,
      page_size: this.state.pageSize,
    };
    if (this.state.search) params.search = this.state.search;
    if (this.state.ordering) params.ordering = this.state.ordering;
    Object.entries(this.state.filters).forEach(([key, value]) => {
      if (value) params[key] = value;
    });
    return params;
  }

  async load() {
    this.setLoading(true);
    try {
      const data = await api.get(this.config.endpoint, this.query());
      const rows = Array.isArray(data) ? data : data.results || [];
      this.state.rows = rows;
      this.state.count = Array.isArray(data) ? rows.length : data.count || 0;
      this.state.numPages = Array.isArray(data) ? 1 : data.num_pages || 1;
      this.renderRows();
      this.renderFooter();
    } catch (error) {
      this.tbody.innerHTML = "";
      this.stateSlot.innerHTML = `<div class="empty-state">
        <div class="empty-state__icon">${icon("alert-triangle", 26)}</div>
        <div class="empty-state__title">No fue posible cargar la informacion</div>
        <div class="empty-state__message">${escapeHtml(error.message)}</div>
      </div>`;
    } finally {
      this.setLoading(false);
    }
  }

  setLoading(loading) {
    this.state.loading = loading;
    if (loading) {
      this.stateSlot.innerHTML = "";
      const columnCount = this.config.columns.length + 1;
      this.tbody.innerHTML = Array.from({ length: 6 })
        .map(
          () =>
            `<tr>${Array.from({ length: columnCount })
              .map(() => '<td><div class="skeleton" style="width:80%"></div></td>')
              .join("")}</tr>`
        )
        .join("");
    }
  }

  renderRows() {
    const { config, state } = this;
    if (!state.rows.length) {
      this.tbody.innerHTML = "";
      this.stateSlot.innerHTML = `<div class="empty-state">
        <div class="empty-state__icon">${icon("folder", 26)}</div>
        <div class="empty-state__title">${escapeHtml(config.empty.title)}</div>
        <div class="empty-state__message">${escapeHtml(config.empty.message)}</div>
        ${
          config.allow.create
            ? `<button class="btn btn--primary" type="button" data-empty-create>${icon("plus", 16)} Crear registro</button>`
            : ""
        }
      </div>`;
      $("[data-empty-create]", this.stateSlot)?.addEventListener("click", () => this.openForm());
      return;
    }

    this.stateSlot.innerHTML = "";
    const hasActions = config.allow.edit || config.allow.delete || (config.rowActions || []).length;

    this.tbody.innerHTML = state.rows
      .map((row) => {
        const cells = config.columns
          .map(
            (column, index) =>
              `<td data-label="${escapeHtml(column.label)}" class="${index === 0 ? "cell-primary" : ""}"
                 style="${column.align ? `text-align:${column.align}` : ""}">${renderCell(column, row)}</td>`
          )
          .join("");

        let actions = "";
        if (hasActions) {
          const custom = (config.rowActions || [])
            .map(
              (action) =>
                `<button class="icon-btn" type="button" data-row-action="${escapeHtml(action.name)}"
                   data-id="${row.id}" title="${escapeHtml(action.label)}">${icon(action.icon || "external", 15)}</button>`
            )
            .join("");
          actions = `<td class="cell-actions"><div class="row-actions">${custom}
            ${
              config.allow.edit
                ? `<button class="icon-btn" type="button" data-edit="${row.id}" title="Editar">${icon("pencil", 15)}</button>`
                : ""
            }
            ${
              config.allow.delete
                ? `<button class="icon-btn" type="button" data-delete="${row.id}" title="Eliminar">${icon("trash", 15)}</button>`
                : ""
            }
          </div></td>`;
        }
        return `<tr data-row-id="${row.id}">${cells}${actions}</tr>`;
      })
      .join("");

    $$("[data-edit]", this.tbody).forEach((button) =>
      button.addEventListener("click", () => {
        const row = this.state.rows.find((item) => String(item.id) === button.dataset.edit);
        this.openForm(row);
      })
    );
    $$("[data-delete]", this.tbody).forEach((button) =>
      button.addEventListener("click", () => this.remove(button.dataset.delete))
    );
    $$("[data-row-action]", this.tbody).forEach((button) =>
      button.addEventListener("click", () => {
        const action = (this.config.rowActions || []).find((item) => item.name === button.dataset.rowAction);
        const row = this.state.rows.find((item) => String(item.id) === button.dataset.id);
        if (action?.url) window.location.href = action.url.replace("{id}", button.dataset.id);
        else document.dispatchEvent(new CustomEvent("resource:action", { detail: { action, row, table: this } }));
      })
    );
  }

  renderFooter() {
    const { state } = this;
    const from = state.count === 0 ? 0 : (state.page - 1) * state.pageSize + 1;
    const to = Math.min(state.page * state.pageSize, state.count);
    this.summary.textContent = `Mostrando ${from}-${to} de ${formatNumber(state.count)} registros`;

    const pages = [];
    const total = state.numPages;
    const current = state.page;
    const push = (page) => pages.push(page);

    push(1);
    for (let page = current - 1; page <= current + 1; page += 1) {
      if (page > 1 && page < total) push(page);
    }
    if (total > 1) push(total);
    const unique = [...new Set(pages)].sort((a, b) => a - b);

    let html = `<button type="button" data-page="${current - 1}" ${current === 1 ? "disabled" : ""}>${icon(
      "chevron-left",
      14
    )}</button>`;
    let previous = 0;
    unique.forEach((page) => {
      if (previous && page - previous > 1) html += `<button type="button" disabled>...</button>`;
      html += `<button type="button" data-page="${page}" class="${page === current ? "is-active" : ""}">${page}</button>`;
      previous = page;
    });
    html += `<button type="button" data-page="${current + 1}" ${current >= total ? "disabled" : ""}>${icon(
      "chevron-right",
      14
    )}</button>`;
    this.paginationNode.innerHTML = html;

    $$("[data-page]", this.paginationNode).forEach((button) =>
      button.addEventListener("click", () => {
        const page = Number(button.dataset.page);
        if (page >= 1 && page <= total && page !== current) {
          this.state.page = page;
          this.load();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      })
    );
  }

  /* ---- Formulario ---- */
  async openForm(row = null) {
    const isEdit = Boolean(row);
    if (!this.drawer) this.drawer = new Drawer({ wide: this.config.fields.length > 8 });
    const drawer = this.drawer;
    drawer.setTitle(
      isEdit ? `Editar ${this.config.title.toLowerCase()}` : `Nuevo registro`,
      isEdit ? "Modifique la informacion y guarde los cambios." : "Complete los campos obligatorios (*)."
    );

    const form = el("form", { class: "form-grid", id: "resource-form", novalidate: "true" });
    drawer.body.innerHTML = '<div class="row" style="justify-content:center;padding:32px"><span class="spinner spinner--lg"></span></div>';
    drawer.open();

    const nodes = await Promise.all(
      this.config.fields.map((field) => buildField(field, row ? resolvePath(row, field.name) : undefined))
    );
    drawer.body.innerHTML = "";
    nodes.forEach((node) => form.appendChild(node));
    drawer.body.appendChild(form);

    drawer.footer.innerHTML = `
      <button class="btn btn--secondary" type="button" data-cancel>Cancelar</button>
      <button class="btn btn--primary" type="submit" form="resource-form" data-save>
        ${icon("save", 16)} ${isEdit ? "Guardar cambios" : "Crear registro"}
      </button>`;
    $("[data-cancel]", drawer.footer).addEventListener("click", () => drawer.close());

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const saveButton = $("[data-save]", drawer.footer);
      saveButton.disabled = true;
      saveButton.innerHTML = '<span class="spinner"></span> Guardando...';
      $$(".field", form).forEach((field) => field.classList.remove("has-error"));

      try {
        const payload = collectForm(form, this.config.fields);
        const url = isEdit ? `${this.config.endpoint}${row.id}/` : this.config.endpoint;
        if (payload instanceof FormData) {
          await api.request(url, { method: isEdit ? "PATCH" : "POST", data: payload });
        } else if (isEdit) {
          await api.patch(url, payload);
        } else {
          await api.post(url, payload);
        }
        toast.success(isEdit ? "Registro actualizado correctamente." : "Registro creado correctamente.");
        drawer.close();
        clearOptionsCache();
        this.load();
      } catch (error) {
        this.applyErrors(form, error);
        toast.error(error.message || "No fue posible guardar el registro.");
      } finally {
        saveButton.disabled = false;
        saveButton.innerHTML = `${icon("save", 16)} ${isEdit ? "Guardar cambios" : "Crear registro"}`;
      }
    });
  }

  applyErrors(form, error) {
    const detail = error.payload?.detail;
    if (!detail || typeof detail !== "object") return;
    Object.entries(detail).forEach(([key, messages]) => {
      const field = form.querySelector(`[data-field-name="${key}"]`);
      if (!field) return;
      field.classList.add("has-error");
      const slot = $(".field__error", field);
      if (slot) slot.textContent = Array.isArray(messages) ? messages.join(" ") : String(messages);
    });
  }

  async remove(id) {
    const confirmed = await confirmDialog({
      title: "Eliminar registro",
      message: "Esta accion marcara el registro como eliminado. Desea continuar?",
      confirmText: "Si, eliminar",
    });
    if (!confirmed) return;
    try {
      await api.delete(`${this.config.endpoint}${id}/`);
      toast.success("Registro eliminado correctamente.");
      if (this.state.rows.length === 1 && this.state.page > 1) this.state.page -= 1;
      this.load();
    } catch (error) {
      toast.error(error.message);
    }
  }

  export(format) {
    const params = { ...this.query(), format };
    delete params.page;
    delete params.page_size;
    api.download(`${this.config.endpoint}export/`, params, `${this.config.module}.${format}`);
  }
}

/* --------------------------------------------------------------------------
   Arranque automatico
   -------------------------------------------------------------------------- */
export function mountResourcePage() {
  const configNode = document.getElementById("resource-config");
  const root = document.getElementById("resource-root");
  if (!configNode || !root) return null;
  const config = JSON.parse(configNode.textContent);
  const table = new ResourceTable(config, root);
  window.PLSGE_TABLE = table;
  return table;
}

document.addEventListener("DOMContentLoaded", mountResourcePage);
