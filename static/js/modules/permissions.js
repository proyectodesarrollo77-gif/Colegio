/* ==========================================================================
   PL_SGE - Matriz de permisos por perfil y modulo
   ========================================================================== */
import { $, $$, api, confirmDialog, escapeHtml, icon, toast } from "../app.js";

const ACTIONS = ["view", "create", "edit", "delete", "export", "approve"];

const state = {
  roleId: null,
  roleCode: "",
  modules: [],
  permissions: {},
  dirty: false,
};

/* -- Render --------------------------------------------------------------- */
function cell(code, action, checked, disabled) {
  return `<td>
    <label class="switch" style="justify-content:center">
      <input type="checkbox" data-module="${escapeHtml(code)}" data-action="${action}"
             ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}>
      <span class="switch__track"></span>
    </label>
  </td>`;
}

function renderMatrix(filter = "") {
  const body = $("[data-matrix-body]");
  const term = filter.trim().toLowerCase();
  const isSuper = state.roleCode === "SUPER_ADMIN";
  const rows = [];

  state.modules.forEach((module) => {
    const children = module.children.filter(
      (child) => !term || child.name.toLowerCase().includes(term) || module.name.toLowerCase().includes(term)
    );
    const parentMatches = !term || module.name.toLowerCase().includes(term);
    if (!parentMatches && !children.length) return;

    const parentPerms = state.permissions[module.code] || {};
    rows.push(`<tr class="module-row">
      <td>
        <div class="row" style="gap:10px">
          ${icon(module.icon, 16)}
          <span>${escapeHtml(module.name)}</span>
          <span class="badge badge--neutral text-2xs">${escapeHtml(module.group)}</span>
        </div>
      </td>
      ${ACTIONS.map((action) => cell(module.code, action, isSuper || parentPerms[action], isSuper)).join("")}
    </tr>`);

    children.forEach((child) => {
      const perms = state.permissions[child.code] || {};
      rows.push(`<tr class="child-row">
        <td>${escapeHtml(child.name)}</td>
        ${ACTIONS.map((action) => cell(child.code, action, isSuper || perms[action], isSuper)).join("")}
      </tr>`);
    });
  });

  body.innerHTML = rows.join("") ||
    `<tr><td colspan="7" class="text-center text-muted" style="padding:36px">Sin modulos coincidentes.</td></tr>`;

  $$("input[type=checkbox]", body).forEach((input) => {
    input.addEventListener("change", () => {
      const code = input.dataset.module;
      const action = input.dataset.action;
      state.permissions[code] = state.permissions[code] || {};
      state.permissions[code][action] = input.checked;

      // Cualquier accion implica poder consultar el modulo
      if (input.checked && action !== "view") {
        state.permissions[code].view = true;
        const viewInput = body.querySelector(`input[data-module="${CSS.escape(code)}"][data-action="view"]`);
        if (viewInput) viewInput.checked = true;
      }
      // Quitar "consultar" retira el resto de acciones
      if (!input.checked && action === "view") {
        ACTIONS.forEach((other) => {
          state.permissions[code][other] = false;
          const node = body.querySelector(`input[data-module="${CSS.escape(code)}"][data-action="${other}"]`);
          if (node) node.checked = false;
        });
      }
      setDirty(true);
      renderSummary();
    });
  });

  renderSummary();
}

function renderSummary() {
  const counters = Object.fromEntries(ACTIONS.map((action) => [action, 0]));
  Object.values(state.permissions).forEach((perms) => {
    ACTIONS.forEach((action) => {
      if (perms[action]) counters[action] += 1;
    });
  });
  ACTIONS.forEach((action) => {
    const node = $(`[data-summary-${action}]`);
    if (node) node.textContent = counters[action];
  });
  const total = Object.values(counters).reduce((acc, value) => acc + value, 0);
  $("[data-permission-count]").textContent = `${total} permisos activos`;
}

function setDirty(value) {
  state.dirty = value;
  $("[data-save-matrix]").disabled = !value;
}

/* -- Carga y guardado ----------------------------------------------------- */
async function loadRole(roleId) {
  const body = $("[data-matrix-body]");
  body.innerHTML = `<tr><td colspan="7" class="text-center" style="padding:40px"><span class="spinner spinner--lg"></span></td></tr>`;
  try {
    const data = await api.get(`/api/roles/${roleId}/matrix/`);
    state.roleId = roleId;
    state.roleCode = data.role.code;
    state.modules = data.modules;
    state.permissions = data.permissions || {};
    $("[data-role-name]").textContent = data.role.name;
    $("[data-role-code]").textContent = `${data.role.code} · ${data.role.users_count} usuarios`;
    renderMatrix($("[data-filter-module]").value);
    setDirty(false);
  } catch (error) {
    toast.error(error.message);
    body.innerHTML = `<tr><td colspan="7" class="text-center text-danger" style="padding:40px">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function saveMatrix() {
  if (state.roleCode === "SUPER_ADMIN") {
    toast.info("El perfil Super Administrador conserva acceso total.");
    return;
  }
  const button = $("[data-save-matrix]");
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span> Guardando...';
  try {
    await api.post("/api/roles/matrix/", { role: state.roleId, permissions: state.permissions });
    toast.success("Permisos actualizados correctamente.");
    setDirty(false);
  } catch (error) {
    toast.error(error.message);
  } finally {
    button.innerHTML = `${icon("save", 15)} Guardar permisos`;
    button.disabled = !state.dirty;
  }
}

/* -- Acciones masivas ----------------------------------------------------- */
function toggleColumn(action) {
  if (state.roleCode === "SUPER_ADMIN") return;
  const inputs = $$(`input[data-action="${action}"]`, $("[data-matrix-body]"));
  const allChecked = inputs.every((input) => input.checked);
  inputs.forEach((input) => {
    input.checked = !allChecked;
    input.dispatchEvent(new Event("change"));
  });
}

function toggleAll() {
  if (state.roleCode === "SUPER_ADMIN") return;
  const inputs = $$("input[type=checkbox]", $("[data-matrix-body]"));
  const allChecked = inputs.every((input) => input.checked);
  inputs.forEach((input) => {
    input.checked = !allChecked;
    const code = input.dataset.module;
    state.permissions[code] = state.permissions[code] || {};
    state.permissions[code][input.dataset.action] = input.checked;
  });
  setDirty(true);
  renderSummary();
}

async function cloneRole() {
  const name = window.prompt("Nombre del nuevo perfil:", `${$("[data-role-name]").textContent} (copia)`);
  if (!name) return;
  const code = window.prompt("Codigo del nuevo perfil (mayusculas, sin espacios):", "PERFIL_NUEVO");
  if (!code) return;
  try {
    const data = await api.post(`/api/roles/${state.roleId}/clone/`, { name, code: code.toUpperCase() });
    toast.success(`Perfil ${data.name} creado con los mismos permisos.`);
    const select = $("[data-role-select]");
    const option = document.createElement("option");
    option.value = data.id;
    option.textContent = data.name;
    option.dataset.code = data.code;
    select.appendChild(option);
    select.value = data.id;
    loadRole(data.id);
  } catch (error) {
    toast.error(error.message);
  }
}

/* -- Arranque ------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  const select = $("[data-role-select]");
  if (!select || !select.value) return;

  loadRole(select.value);

  select.addEventListener("change", async () => {
    if (state.dirty) {
      const discard = await confirmDialog({
        title: "Cambios sin guardar",
        message: "Tiene cambios pendientes en la matriz. Desea descartarlos?",
        confirmText: "Descartar",
      });
      if (!discard) {
        select.value = state.roleId;
        return;
      }
    }
    loadRole(select.value);
  });

  $("[data-save-matrix]")?.addEventListener("click", saveMatrix);
  $("[data-toggle-all]")?.addEventListener("click", toggleAll);
  $("[data-clone-role]")?.addEventListener("click", cloneRole);
  $$("[data-column-toggle]").forEach((button) =>
    button.addEventListener("click", () => toggleColumn(button.dataset.columnToggle))
  );
  $("[data-filter-module]")?.addEventListener("input", (event) => renderMatrix(event.target.value));

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "s") {
      event.preventDefault();
      saveMatrix();
    }
  });
});
