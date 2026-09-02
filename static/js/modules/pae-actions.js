/**
 * Acciones de fila del modulo PAE.
 *
 * Se engancha al evento `resource:action` que emite `crud.js`, de modo que no
 * duplica la tabla, los filtros ni el formulario: solo agrega las operaciones
 * de negocio (transiciones de estado, versiones de menu, generacion de
 * novedades y consulta de historiales). No define estilos ni colores propios.
 */
import { Drawer, api, confirmDialog, escapeHtml, formatDate, icon, toast } from "../app.js";

const PLAN_STATUS = {
  BORRADOR: "Borrador",
  EN_REVISION: "En revision",
  APROBADO: "Aprobado",
  EN_EJECUCION: "En ejecucion",
  CERRADO: "Cerrado",
  ANULADO: "Anulado",
};

const INCIDENT_STATUS = {
  REPORTADA: "Reportada",
  ASIGNADA: "Asignada",
  EN_INVESTIGACION: "En investigacion",
  EN_CORRECCION: "En correccion",
  SOLUCIONADA: "Solucionada",
  CERRADA: "Cerrada",
};

const BENEFICIARY_STATUS = {
  ACTIVO: "Activo",
  SUSPENDIDO: "Suspendido",
  RETIRADO: "Retirado",
  TRASLADADO: "Trasladado",
};

/* --------------------------------------------------------------------------
   Utilidades
   -------------------------------------------------------------------------- */
function drawerWith(title, subtitle, html, { wide = false } = {}) {
  const drawer = new Drawer({ title, subtitle, wide });
  drawer.body.innerHTML = html;
  drawer.footer.innerHTML = `<button class="btn btn--secondary" type="button" data-close>Cerrar</button>`;
  drawer.footer.querySelector("[data-close]").addEventListener("click", () => drawer.destroy());
  drawer.open();
  return drawer;
}

/**
 * Formulario corto dentro de un drawer. `fields` es una lista de descriptores
 * y resuelve con los valores o `null` si el usuario cancela.
 */
function promptForm({ title, subtitle = "", fields, confirmText = "Guardar" }) {
  return new Promise((resolve) => {
    const drawer = new Drawer({ title, subtitle });
    drawer.body.innerHTML = `<div class="form-grid">${fields
      .map((field) => {
        const id = `pae-field-${field.name}`;
        if (field.type === "select") {
          return `<div class="field col-12">
            <label class="field__label" for="${id}">${escapeHtml(field.label)}</label>
            <select class="select" id="${id}" name="${field.name}">
              ${(field.options || [])
                .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
                .join("")}
            </select>
            ${field.hint ? `<div class="field__hint">${escapeHtml(field.hint)}</div>` : ""}
          </div>`;
        }
        return `<div class="field col-12">
          <label class="field__label" for="${id}">${escapeHtml(field.label)}</label>
          <textarea class="textarea" id="${id}" name="${field.name}" rows="3"
            placeholder="${escapeHtml(field.placeholder || "")}"></textarea>
          ${field.hint ? `<div class="field__hint">${escapeHtml(field.hint)}</div>` : ""}
        </div>`;
      })
      .join("")}</div>`;

    drawer.footer.innerHTML = `
      <button class="btn btn--secondary" type="button" data-cancel>Cancelar</button>
      <button class="btn btn--primary" type="button" data-confirm>${escapeHtml(confirmText)}</button>`;

    drawer.footer.querySelector("[data-cancel]").addEventListener("click", () => {
      drawer.destroy();
      resolve(null);
    });
    drawer.footer.querySelector("[data-confirm]").addEventListener("click", () => {
      const values = {};
      fields.forEach((field) => {
        values[field.name] = drawer.body.querySelector(`[name="${field.name}"]`)?.value || "";
      });
      drawer.destroy();
      resolve(values);
    });
    drawer.open();
  });
}

function historyRows(rows, { statusMap = {}, statusKey = "new_status", dateKey = "changed_at" }) {
  if (!rows.length) {
    return `<div class="empty-state">
      <div class="empty-state__icon">${icon("activity", 24)}</div>
      <div class="empty-state__title">Sin movimientos registrados</div>
      <div class="empty-state__message">El historial se alimenta automaticamente con cada cambio de estado.</div>
    </div>`;
  }
  return `<div class="timeline">${rows
    .map((row) => {
      const status = row[statusKey] || "";
      return `<div class="timeline__item">
        <span class="timeline__dot"></span>
        <div class="timeline__title">${escapeHtml(statusMap[status] || status)}</div>
        <div class="timeline__meta">
          ${escapeHtml(formatDate(row[dateKey], true))}
          ${row.changed_by_name ? ` &middot; ${escapeHtml(row.changed_by_name)}` : ""}
        </div>
        ${row.comment || row.reason ? `<div class="text-sm mt-2">${escapeHtml(row.comment || row.reason)}</div>` : ""}
      </div>`;
    })
    .join("")}</div>`;
}

async function run(table, promise, successMessage) {
  try {
    const result = await promise;
    toast.success(successMessage);
    table.load();
    return result;
  } catch (error) {
    toast.error(error.message);
    return null;
  }
}

/* --------------------------------------------------------------------------
   Manejadores por accion
   -------------------------------------------------------------------------- */
const handlers = {
  async "set-current"({ row, table }) {
    const ok = await confirmDialog({
      title: "Definir vigencia actual",
      message: `La vigencia "${row.name}" pasara a ser la vigencia en curso del programa.`,
      confirmText: "Definir",
      tone: "primary",
      iconName: "check",
    });
    if (!ok) return;
    await run(table, api.post(`/api/pae/vigencias/${row.id}/set-current/`, {}), "Vigencia actualizada.");
  },

  async "enroll-beneficiaries"({ row, table }) {
    const ok = await confirmDialog({
      title: "Vincular beneficiarios",
      message:
        "Se vincularan como beneficiarios los estudiantes matriculados que cumplen los criterios de esta priorizacion. " +
        "Los estudiantes ya vinculados no se duplican.",
      confirmText: "Vincular",
      tone: "primary",
      iconName: "users",
    });
    if (!ok) return;
    const result = await run(
      table,
      api.post(`/api/pae/priorizaciones/${row.id}/enroll-beneficiaries/`, {}),
      "Proceso de vinculacion ejecutado."
    );
    if (result) toast.info(`Beneficiarios nuevos: ${result.created ?? 0}`);
  },

  async transition({ row, table }) {
    const options = (row.allowed_transitions || []).map((item) => ({
      value: item.status,
      label: `${PLAN_STATUS[item.status] || item.status} (requiere ${item.action})`,
    }));
    if (!options.length) {
      toast.info("El plan no admite mas cambios de estado.");
      return;
    }
    const values = await promptForm({
      title: "Cambiar estado del plan",
      subtitle: `${row.code || ""} ${row.name || ""}`.trim(),
      confirmText: "Aplicar",
      fields: [
        { name: "status", label: "Nuevo estado", type: "select", options },
        {
          name: "reason",
          label: "Motivo o comentario",
          placeholder: "Justifique el cambio de estado",
          hint: "Queda registrado en el historial del plan y en la bitacora de auditoria.",
        },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/planes/${row.id}/transition/`, values),
      "Estado del plan actualizado."
    );
  },

  async "sync-beneficiaries"({ row, table }) {
    const result = await run(
      table,
      api.post(`/api/pae/planes/${row.id}/sync-beneficiaries/`, {}),
      "Beneficiarios sincronizados."
    );
    if (result) toast.info(`Beneficiarios: ${result.beneficiaries} · raciones proyectadas: ${result.projected_rations}`);
  },

  async estado({ row, table }) {
    const options = (row.allowed_transitions || []).map((status) => ({
      value: status,
      label: INCIDENT_STATUS[status] || status,
    }));
    if (!options.length) {
      toast.info("La novedad esta cerrada y no admite mas transiciones.");
      return;
    }
    const values = await promptForm({
      title: "Cambiar estado de la novedad",
      subtitle: row.code || "",
      confirmText: "Aplicar",
      fields: [
        { name: "status", label: "Nuevo estado", type: "select", options },
        {
          name: "comment",
          label: "Comentario",
          placeholder: "Describa la gestion realizada",
          hint: "Para cerrar una novedad se exige causa raiz, accion correctiva y evidencia.",
        },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/novedades/${row.id}/estado/`, values),
      "Estado de la novedad actualizado."
    );
  },

  async "cambiar-estado"({ row, table }) {
    const values = await promptForm({
      title: "Cambiar estado del beneficiario",
      subtitle: row.student_name || "",
      confirmText: "Aplicar",
      fields: [
        {
          name: "status",
          label: "Nuevo estado",
          type: "select",
          options: Object.entries(BENEFICIARY_STATUS).map(([value, label]) => ({ value, label })),
        },
        { name: "reason", label: "Motivo", placeholder: "Motivo del cambio", hint: "Obligatorio para retiro o suspension." },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/beneficiarios/${row.id}/change-status/`, values),
      "Estado del beneficiario actualizado."
    );
  },

  async history({ row }) {
    const isPlan = window.location.pathname.includes("/planeacion");
    const isIncident = window.location.pathname.includes("/novedades");
    const endpoint = isPlan
      ? `/api/pae/planes/${row.id}/history/`
      : isIncident
        ? `/api/pae/novedades/${row.id}/history/`
        : `/api/pae/beneficiarios/${row.id}/history/`;
    try {
      const data = await api.get(endpoint);
      drawerWith(
        "Historial de estados",
        row.code || row.student_name || row.name || "",
        historyRows(data.results || [], {
          statusMap: isPlan ? PLAN_STATUS : isIncident ? INCIDENT_STATUS : BENEFICIARY_STATUS,
        })
      );
    } catch (error) {
      toast.error(error.message);
    }
  },

  async detail({ row }) {
    try {
      const data = await api.get(`/api/pae/menus/${row.id}/detail/`);
      const days = data.days || [];
      const html = days.length
        ? days
            .map(
              (day) => `<div class="card mb-3">
                <div class="card__header">
                  <div style="flex:1">
                    <div class="card__title">Dia ${day.day_number} &middot; ${escapeHtml(day.name || "")}</div>
                    <div class="card__subtitle">${day.total_calories || 0} kcal</div>
                  </div>
                </div>
                <div class="card__body">
                  ${
                    (day.preparations || []).length
                      ? `<ul class="stack">${day.preparations
                          .map(
                            (prep) =>
                              `<li><span class="text-bold">${escapeHtml(prep.name)}</span>
                               <span class="text-xs text-muted"> &middot; ${escapeHtml(prep.component_display || "")}</span></li>`
                          )
                          .join("")}</ul>`
                      : '<div class="text-sm text-muted">Sin preparaciones registradas.</div>'
                  }
                </div>
              </div>`
            )
            .join("")
        : `<div class="empty-state">
             <div class="empty-state__icon">${icon("layers", 24)}</div>
             <div class="empty-state__title">El ciclo aun no tiene dias</div>
             <div class="empty-state__message">Registre los dias del ciclo y sus preparaciones.</div>
           </div>`;
      drawerWith(row.name || "Ciclo de menu", `Codigo ${row.code || ""}`, html, { wide: true });
    } catch (error) {
      toast.error(error.message);
    }
  },

  async "new-version"({ row, table }) {
    const isDocument = window.location.pathname.includes("/documentos");
    if (isDocument) {
      toast.info("Cargue la nueva version desde el formulario del documento.");
      return;
    }
    const ok = await confirmDialog({
      title: "Crear nueva version del ciclo",
      message: "Se clonara el ciclo con sus dias, preparaciones e ingredientes y el original quedara archivado.",
      confirmText: "Crear version",
      tone: "primary",
      iconName: "copy",
    });
    if (!ok) return;
    await run(table, api.post(`/api/pae/menus/${row.id}/new-version/`, {}), "Nueva version creada.");
  },

  async publish({ row, table }) {
    const ok = await confirmDialog({
      title: "Publicar ciclo de menu",
      message: "El ciclo quedara vigente y las versiones anteriores con el mismo codigo se archivaran.",
      confirmText: "Publicar",
      tone: "primary",
      iconName: "check",
    });
    if (!ok) return;
    await run(table, api.post(`/api/pae/menus/${row.id}/publish/`, {}), "Ciclo publicado.");
  },

  async performance({ row }) {
    try {
      const data = await api.get(`/api/pae/operadores/${row.id}/performance/`);
      const rows = Object.entries(data || {})
        .filter(([, value]) => typeof value !== "object")
        .map(
          ([key, value]) => `<div class="meter-row">
            <span class="meter-row__label">${escapeHtml(key.replace(/_/g, " "))}</span>
            <span class="meter-row__value">${escapeHtml(String(value))}</span>
          </div>`
        )
        .join("");
      drawerWith(row.business_name || "Operador", "Desempeno en la vigencia actual", rows || "Sin datos.");
    } catch (error) {
      toast.error(error.message);
    }
  },

  async "create-incident"({ row, table }) {
    const values = await promptForm({
      title: "Generar novedad desde la entrega",
      subtitle: `${row.campus_name || ""} · ${row.service_date || ""}`,
      confirmText: "Generar",
      fields: [
        {
          name: "description",
          label: "Descripcion de la novedad",
          placeholder: "Describa el incumplimiento detectado",
          hint: "La novedad queda vinculada a la entrega, la sede y el operador.",
        },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/entregas/${row.id}/create-incident/`, values),
      "Novedad generada."
    );
  },

  async "create-action"({ row, table }) {
    const values = await promptForm({
      title: "Generar plan de mejoramiento",
      subtitle: row.code || row.description || "",
      confirmText: "Generar",
      fields: [
        { name: "action", label: "Accion correctiva", placeholder: "Accion a implementar" },
        {
          name: "root_cause",
          label: "Causa raiz",
          placeholder: "Causa identificada",
          hint: "El plan queda vinculado al hallazgo y con vencimiento a 30 dias si no se indica otra fecha.",
        },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/hallazgos/${row.id}/create-action/`, values),
      "Plan de mejoramiento creado."
    );
  },

  async close({ row, table }) {
    const values = await promptForm({
      title: "Verificar y cerrar la accion",
      subtitle: row.code || "",
      confirmText: "Cerrar accion",
      fields: [
        {
          name: "verification_note",
          label: "Nota de verificacion",
          placeholder: "Resultado de la verificacion de eficacia",
          hint: "Se exige evidencia y avance del 100% para cerrar.",
        },
      ],
    });
    if (!values) return;
    await run(
      table,
      api.post(`/api/pae/mejoramiento/${row.id}/close/`, values),
      "Accion verificada y cerrada."
    );
  },

  async apply({ row }) {
    window.location.href = `/pae/control-calidad/aplicar/?verification=${row.id}`;
  },

  async versions({ row }) {
    try {
      const data = await api.get(`/api/pae/documentos/${row.id}/versions/`);
      const rows = data.results || [];
      const html = rows.length
        ? `<div class="table-wrap"><table class="table table--compact">
             <thead><tr><th>Version</th><th>Fecha</th><th>Estado</th></tr></thead>
             <tbody>${rows
               .map(
                 (item) => `<tr>
                   <td>${escapeHtml(String(item.version ?? ""))}</td>
                   <td>${escapeHtml(formatDate(item.issued_on))}</td>
                   <td>${escapeHtml(item.status_display || item.status || "")}</td>
                 </tr>`
               )
               .join("")}</tbody>
           </table></div>`
        : '<div class="text-sm text-muted">Solo existe la version actual.</div>';
      drawerWith(row.name || "Documento", "Versiones registradas", html);
    } catch (error) {
      toast.error(error.message);
    }
  },
};

document.addEventListener("resource:action", (event) => {
  const { action, row, table } = event.detail || {};
  const handler = handlers[action?.name];
  if (handler) handler({ row, table });
});

export { handlers, promptForm, drawerWith };
