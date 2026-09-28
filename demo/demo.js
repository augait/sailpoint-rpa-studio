let editingUsername = null;

async function api(
  path,
  method = "GET",
  body,
) {
  const r = await fetch(path, {
    method,
    headers: {
      "Content-Type":
        "application/json",
    },
    ...(body
      ? {
          body:
            JSON.stringify(body),
        }
      : {}),
  });

  const d = await r.json();

  if (!r.ok) {
    throw Error(d.detail);
  }

  return d;
}


document.querySelector(
  "#login-form",
).onsubmit = async (e) => {
  e.preventDefault();

  try {
    await api(
      "/session",
      "POST",
      {
        username:
          document.querySelector(
            "#login-username",
          ).value,

        password:
          document.querySelector(
            "#login-password",
          ).value,
      },
    );

    document.querySelector(
      "#login-form",
    ).hidden = true;

    document.querySelector(
      "#portal",
    ).hidden = false;

  } catch (e) {
    document.querySelector(
      "#error",
    ).textContent = e.message;
  }
};


function prepareNewUser() {
  editingUsername = null;

  const form = document.querySelector(
    "#user-form",
  );

  form.reset();
  form.hidden = false;

  const username =
    document.querySelector(
      "#username",
    );

  username.readOnly = false;

  document.querySelector(
    "#save",
  ).textContent = "Save";
}


function prepareEditUser(row) {
  editingUsername = row.username;

  const form = document.querySelector(
    "#user-form",
  );

  form.hidden = false;

  const username =
    document.querySelector(
      "#username",
    );

  username.value = row.username;
  username.readOnly = true;

  document.querySelector(
    "#firstname",
  ).value = row.firstname;

  document.querySelector(
    "#lastname",
  ).value = row.lastname;

  document.querySelector(
    "#email",
  ).value = row.email;

  document.querySelector(
    "#department",
  ).value = row.department;

  document.querySelector(
    "#save",
  ).textContent = "Update";

  document.querySelector(
    "#result",
  ).textContent = "";
}


async function load() {
  const rows = await api(
    "/accounts",
  );

  document.querySelector(
    "#accounts",
  ).replaceChildren(
    ...rows.map((row) => {
      const tr =
        document.createElement(
          "tr",
        );

      for (const value of [
        row.username,
        (
          row.firstname
          + " "
          + row.lastname
        ),
        row.email,
        row.department,
      ]) {
        const td =
          document.createElement(
            "td",
          );

        td.textContent = value;

        tr.append(td);
      }

      const actionCell =
        document.createElement(
          "td",
        );

      const edit =
        document.createElement(
          "button",
        );

      edit.type = "button";
      edit.textContent = "Edit";

      edit.dataset.accountEdit =
        row.username;

      edit.setAttribute(
        "aria-label",
        `Edit ${row.username}`,
      );

      edit.onclick = () =>
        prepareEditUser(row);

      actionCell.append(edit);
      tr.append(actionCell);

      return tr;
    }),
  );
}


document.querySelector(
  "#users",
).onclick = async () => {
  document.querySelector(
    "#user-section",
  ).hidden = false;

  await load();
};


document.querySelector(
  "#new-user",
).onclick = () => {
  prepareNewUser();
};


document.querySelector(
  "#user-form",
).onsubmit = async (e) => {
  e.preventDefault();

  try {
    const data =
      Object.fromEntries(
        new FormData(
          e.target,
        ),
      );

    let result;

    if (editingUsername) {
      const {
        username,
        ...attributes
      } = data;

      result = await api(
        (
          "/accounts/"
          + encodeURIComponent(
              editingUsername,
            )
        ),
        "PUT",
        attributes,
      );

    } else {
      result = await api(
        "/accounts",
        "POST",
        data,
      );
    }

    document.querySelector(
      "#result",
    ).textContent =
      result.message;

    document.querySelector(
      "#account-id",
    ).textContent =
      result.accountId;

    await load();

  } catch (e) {
    document.querySelector(
      "#error",
    ).textContent = e.message;
  }
};
