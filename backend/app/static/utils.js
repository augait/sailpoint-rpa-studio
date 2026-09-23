export const state = { token: null, role: null, username: null };
export const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const button = (text, action, id = "", cls = "") =>
  `<button type="button" class="${cls}" data-action="${action}" data-id="${esc(id)}">${esc(text)}</button>`;
export const badge = (s) => `<span class="badge ${esc(s)}">● ${esc(s)}</span>`;
export const time = (v) => (v ? new Date(v).toLocaleString("pt-BR") : "—");
export const empty = (title, description) =>
  `<div class="empty"><h3>${title}</h3><p>${description}</p></div>`;
export function modal(html) {
  document.querySelector("#modal-content").innerHTML = html;
  document.querySelector("#modal").showModal();
}
let toastTimer;
export function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 6000);
}
export async function api(
  path,
  method = "GET",
  body = null,
  extra = {},
  absolute = false,
) {
  const response = await fetch((absolute ? "" : "/api/v1") + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: "Bearer " + state.token } : {}),
      ...extra,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) {
    let detail = data.detail;
    if (Array.isArray(detail))
      detail = detail.map((x) => x.loc.join(".") + ": " + x.msg).join("\n");
    if (typeof detail === "object") detail = JSON.stringify(detail);
    throw Error(detail || "Falha na requisição");
  }
  return data;
}
export function bind(target, event, fn) {
  (typeof target === "string"
    ? document.querySelector(target)
    : target
  ).addEventListener(event, async (e) => {
    try {
      await fn(e);
    } catch (err) {
      toast(err.message);
      const el =
        document.querySelector("#modal[open] #form-error") ||
        document.querySelector("#login-error");
      if (el) el.textContent = err.message;
    }
  });
}
