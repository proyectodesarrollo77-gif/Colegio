/* ==========================================================================
   PL_SGE - Interacciones de las pantallas de autenticacion
   ========================================================================== */
import { $, $$, api, icon, toast } from "./app.js";

/* -- Mostrar / ocultar contrasena ----------------------------------------- */
function initPasswordToggles() {
  $$("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const wrapper = button.closest(".input-group");
      const input = wrapper?.querySelector("input");
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.innerHTML = icon(showing ? "eye" : "lock", 16);
      button.setAttribute("aria-label", showing ? "Mostrar contrasena" : "Ocultar contrasena");
      input.focus();
    });
  });
}

/* -- Estado de envio ------------------------------------------------------ */
function initSubmitState() {
  $$("form[novalidate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const required = Array.from(form.querySelectorAll("[required]"));
      const missing = required.filter((input) => !input.value.trim());
      if (missing.length) {
        event.preventDefault();
        missing[0].focus();
        missing.forEach((input) => input.closest(".field")?.classList.add("has-error"));
        toast.warning("Complete los campos obligatorios para continuar.");
        return;
      }
      const button = form.querySelector("[data-submit]");
      if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> Procesando...';
      }
    });
    form.querySelectorAll("input").forEach((input) =>
      input.addEventListener("input", () => input.closest(".field")?.classList.remove("has-error"))
    );
  });
}

/* -- Medidor de fortaleza de contrasena ----------------------------------- */
function passwordScore(value) {
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;
  return Math.min(score, 4);
}

function initPasswordStrength() {
  const input = $("[data-password-strength]");
  if (!input) return;
  const meter = document.createElement("div");
  meter.className = "stack";
  meter.style.gap = "6px";
  meter.innerHTML = `
    <div class="progress progress--sm"><div class="progress__bar" style="width:0"></div></div>
    <div class="field__hint" data-strength-label>Use al menos 8 caracteres con mayusculas, numeros y simbolos.</div>`;
  input.closest(".field").appendChild(meter);

  const labels = ["Muy debil", "Debil", "Aceptable", "Fuerte", "Excelente"];
  const tones = ["danger", "danger", "warning", "success", "success"];

  input.addEventListener("input", () => {
    const score = passwordScore(input.value);
    const bar = meter.querySelector(".progress__bar");
    bar.style.width = `${(score / 4) * 100}%`;
    bar.className = `progress__bar progress__bar--${tones[score]}`;
    meter.querySelector("[data-strength-label]").textContent = input.value
      ? `Seguridad: ${labels[score]}`
      : "Use al menos 8 caracteres con mayusculas, numeros y simbolos.";
  });
}

/* -- Confirmacion de contrasena ------------------------------------------- */
function initPasswordMatch() {
  const password = $("[name='new_password']");
  const confirm = $("[name='confirm_password']");
  if (!password || !confirm) return;
  const validate = () => {
    const field = confirm.closest(".field");
    const slot = field?.querySelector(".field__error");
    const matches = !confirm.value || password.value === confirm.value;
    field?.classList.toggle("has-error", !matches);
    if (slot) slot.textContent = matches ? "" : "Las contrasenas no coinciden.";
  };
  password.addEventListener("input", validate);
  confirm.addEventListener("input", validate);
}

/* -- Campos de codigo OTP ------------------------------------------------- */
function initOtpInputs() {
  const container = $("[data-otp]");
  if (!container) return;
  const hidden = container.querySelector("input[type='hidden']");
  const boxes = Array.from(container.querySelectorAll("[data-otp-box]"));

  const sync = () => {
    if (hidden) hidden.value = boxes.map((box) => box.value).join("");
  };

  boxes.forEach((box, index) => {
    box.addEventListener("input", () => {
      box.value = box.value.replace(/\D/g, "").slice(-1);
      sync();
      if (box.value && index < boxes.length - 1) boxes[index + 1].focus();
      if (boxes.every((item) => item.value) && hidden) {
        hidden.form?.requestSubmit?.();
      }
    });
    box.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && !box.value && index > 0) boxes[index - 1].focus();
      if (event.key === "ArrowLeft" && index > 0) boxes[index - 1].focus();
      if (event.key === "ArrowRight" && index < boxes.length - 1) boxes[index + 1].focus();
    });
    box.addEventListener("paste", (event) => {
      event.preventDefault();
      const digits = (event.clipboardData.getData("text") || "").replace(/\D/g, "").split("");
      boxes.forEach((item, position) => (item.value = digits[position] || ""));
      sync();
      boxes[Math.min(digits.length, boxes.length - 1)]?.focus();
    });
  });
  boxes[0]?.focus();
}

/* -- Copiar secreto 2FA / codigos de recuperacion ------------------------- */
function initCopyButtons() {
  $$("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const value = button.dataset.copy;
      try {
        await navigator.clipboard.writeText(value);
        toast.success("Copiado al portapapeles.");
      } catch (error) {
        toast.error("No fue posible copiar el contenido.");
      }
    });
  });
}

/* -- Regenerar codigos de recuperacion ------------------------------------ */
function initRecoveryCodes() {
  const button = $("[data-regenerate-codes]");
  if (!button) return;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const data = await api.post("/api/auth/2fa/recovery-codes/", {});
      const list = $("[data-recovery-list]");
      if (list) {
        list.innerHTML = data.recovery_codes
          .map((code) => `<code class="chip">${code}</code>`)
          .join("");
      }
      toast.success("Se generaron nuevos codigos de recuperacion.");
    } catch (error) {
      toast.error(error.message);
    } finally {
      button.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initPasswordToggles();
  initSubmitState();
  initPasswordStrength();
  initPasswordMatch();
  initOtpInputs();
  initCopyButtons();
  initRecoveryCodes();
});

export { passwordScore };
