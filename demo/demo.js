async function api(path, method = "GET", body) {
  const r = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const d = await r.json();
  if (!r.ok) throw Error(d.detail);
  return d;
}
document.querySelector("#login-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/session", "POST", {
      username: document.querySelector("#login-username").value,
      password: document.querySelector("#login-password").value,
    });
    document.querySelector("#login-form").hidden = true;
    document.querySelector("#portal").hidden = false;
  } catch (e) {
    document.querySelector("#error").textContent = e.message;
  }
};
async function load() {
  const rows = await api("/accounts");
  document.querySelector("#accounts").replaceChildren(
    ...rows.map((r) => {
      const tr = document.createElement("tr");
      for (const v of [
        r.username,
        r.firstname + " " + r.lastname,
        r.email,
        r.department,
      ]) {
        const td = document.createElement("td");
        td.textContent = v;
        tr.append(td);
      }
      return tr;
    }),
  );
}
document.querySelector("#users").onclick = async () => {
  document.querySelector("#user-section").hidden = false;
  await load();
};
document.querySelector("#new-user").onclick = () =>
  (document.querySelector("#user-form").hidden = false);
document.querySelector("#user-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api(
      "/accounts",
      "POST",
      Object.fromEntries(new FormData(e.target)),
    );
    document.querySelector("#result").textContent = r.message;
    document.querySelector("#account-id").textContent = r.accountId;
    await load();
  } catch (e) {
    document.querySelector("#error").textContent = e.message;
  }
};
