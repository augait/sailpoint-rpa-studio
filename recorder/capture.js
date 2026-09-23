(() => {
  if (window !== window.top || window.__studioRecorder) return;

  window.__studioRecorder = true;

  const recordedSelects = new Set();
  const recordedAssertions = new Set();
  const recordedOutputs = new Set();

  const POST_ACTION_KEY = "studioRecorderPostActionUntil";

  const escapeCss = (value) => CSS.escape(value);

  const cleanText = (value) =>
    String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 180);

  const variableName = (el) => {
    let name =
      el.getAttribute("name") ||
      el.id ||
      el.getAttribute("aria-label") ||
      el.getAttribute("placeholder") ||
      "field";

    name = name
      .trim()
      .replace(/[^A-Za-z0-9_]/g, "_")
      .replace(/_+/g, "_");

    if (!/^[A-Za-z_]/.test(name)) {
      name = "field_" + name;
    }

    return name || "field";
  };

  const outputName = (el) => {
    let raw =
      el.getAttribute("data-output") ||
      el.getAttribute("data-testid") ||
      el.id ||
      el.getAttribute("name") ||
      "result";

    raw = raw
      .replace(/[^A-Za-z0-9]+/g, " ")
      .trim();

    const parts = raw
      .split(/\s+/)
      .filter(Boolean);

    if (!parts.length) {
      return "result";
    }

    let result =
      parts[0].toLowerCase() +
      parts
        .slice(1)
        .map(
          (part) =>
            part.charAt(0).toUpperCase() +
            part.slice(1).toLowerCase(),
        )
        .join("");

    if (!/^[A-Za-z_]/.test(result)) {
      result = "result" + result;
    }

    return result.slice(0, 60);
  };

  const elementKey = (el) => {
    if (el.id) {
      return `id:${el.id}`;
    }

    if (el.name) {
      return `name:${el.name}`;
    }

    return (
      `${el.tagName}:` +
      `${el.getAttribute("aria-label") || ""}:` +
      `${el.getAttribute("placeholder") || ""}`
    );
  };

  const selectors = (el) => {
    const result = [];

    const add = (kind, value, name) => {
      value = cleanText(value);

      if (!value) return;

      const candidate = {
        kind,
        value,
        ...(name ? { name: cleanText(name) } : {}),
      };

      const duplicate = result.some(
        (item) =>
          item.kind === candidate.kind &&
          item.value === candidate.value &&
          item.name === candidate.name,
      );

      if (!duplicate) {
        result.push(candidate);
      }
    };

    add(
      "testid",
      el.getAttribute("data-testid"),
    );

    if (el.id) {
      add(
        "css",
        "#" + escapeCss(el.id),
      );
    }

    if (el.name) {
      add(
        "css",
        `${el.tagName.toLowerCase()}[name="${escapeCss(el.name)}"]`,
      );
    }

    const role =
      el.getAttribute("role") ||
      {
        BUTTON: "button",
        A: "link",
        SELECT: "combobox",
      }[el.tagName];

    const label =
      el.getAttribute("aria-label") ||
      el.labels?.[0]?.textContent ||
      "";

    if (role) {
      add(
        "role",
        role,
        label || cleanText(el.textContent),
      );
    }

    add("label", label);

    add(
      "placeholder",
      el.getAttribute("placeholder"),
    );

    if (
      ["BUTTON", "A"].includes(el.tagName)
    ) {
      add(
        "text",
        cleanText(el.textContent),
      );
    }

    if (result.length === 0) {
      let path = "";
      let node = el;

      while (
        node &&
        node !== document.body
      ) {
        const parent =
          node.parentElement;

        if (!parent) {
          break;
        }

        const siblings =
          [...parent.children].filter(
            (candidate) =>
              candidate.tagName ===
              node.tagName,
          );

        const position =
          siblings.indexOf(node) + 1;

        path =
          node.tagName.toLowerCase() +
          `:nth-of-type(${position})` +
          (path
            ? " > " + path
            : "");

        node = parent;
      }

      if (path) {
        add(
          "css",
          "body > " + path,
        );
      }
    }

    return result.slice(0, 10);
  };

  const send = (
    type,
    el,
    extra = {},
  ) => {
    if (!el) return;

    window.studioRecord({
      type,
      selectors:
        type === "navigate"
          ? []
          : selectors(el),
      ...extra,
    });
  };

  /*
   * SELECT
   */

  const recordSelect = (el) => {
    if (!el) return;

    if (el.tagName !== "SELECT") {
      return;
    }

    if (el.disabled) {
      return;
    }

    const key =
      elementKey(el);

    if (
      recordedSelects.has(key)
    ) {
      return;
    }

    const variable =
      variableName(el);

    recordedSelects.add(key);

    send(
      "select",
      el,
      {
        value:
          "{{" +
          variable +
          "}}",
      },
    );
  };

  const captureFormSelects = (
    form,
  ) => {
    if (!form) return;

    form
      .querySelectorAll("select")
      .forEach(
        (select) =>
          recordSelect(select),
      );
  };

  /*
   * RESULT DETECTION
   */

  const isVisible = (el) => {
    if (!el) return false;

    const style =
      window.getComputedStyle(el);

    if (
      style.display === "none" ||
      style.visibility === "hidden" ||
      Number(style.opacity) === 0
    ) {
      return false;
    }

    return (
      el.getClientRects().length > 0
    );
  };

  const successPattern =
    /\b(success|successful|successfully|created|saved|completed|updated|enabled|disabled|granted|provisioned|added|removed|deleted|sucesso|criado|criada|salvo|salva|concluido|concluído|concluida|concluída|atualizado|atualizada|ativado|ativada|desativado|desativada|concedido|concedida|provisionado|provisionada|adicionado|adicionada|removido|removida|excluido|excluído|excluida|excluída)\b/i;

  const failurePattern =
    /\b(error|failed|failure|invalid|denied|rejected|erro|falhou|falha|invalido|inválido|invalida|inválida|negado|negada|rejeitado|rejeitada)\b/i;

  const captureSuccessMessage = () => {
    const query = [
      '[role="status"]',
      '[role="alert"]',
      '#result',
      '[id*="result" i]',
      '[id*="success" i]',
      '[class*="success" i]',
      '[class*="result" i]',
      '[class*="message" i]',
    ].join(",");

    const candidates =
      document.querySelectorAll(query);

    for (const el of candidates) {
      if (!isVisible(el)) {
        continue;
      }

      const value =
        cleanText(el.innerText);

      if (
        value.length < 3 ||
        value.length > 180
      ) {
        continue;
      }

      if (
        !successPattern.test(value)
      ) {
        continue;
      }

      if (
        failurePattern.test(value)
      ) {
        continue;
      }

      const key =
        `${elementKey(el)}:${value}`;

      if (
        recordedAssertions.has(key)
      ) {
        continue;
      }

      recordedAssertions.add(key);

      send(
        "assert_text",
        el,
        {
          value,
        },
      );

      return true;
    }

    return false;
  };

  const captureOutputs = () => {
    const query = [
      '[id*="account-id" i]',
      '[id*="account_id" i]',
      '[id*="accountid" i]',
      '[id*="user-id" i]',
      '[id*="user_id" i]',
      '[id*="userid" i]',
      '[id*="identity-id" i]',
      '[id*="identity_id" i]',
      '[id*="native-identity" i]',
      '[data-testid*="account-id" i]',
      '[data-testid*="user-id" i]',
      '[data-testid*="identity-id" i]',
    ].join(",");

    const candidates =
      document.querySelectorAll(query);

    let captured = false;

    for (const el of candidates) {
      if (!isVisible(el)) {
        continue;
      }

      if (
        ["INPUT", "TEXTAREA", "SELECT"]
          .includes(el.tagName)
      ) {
        continue;
      }

      const currentValue =
        cleanText(el.innerText);

      if (!currentValue) {
        continue;
      }

      const output =
        outputName(el);

      const key =
        `${elementKey(el)}:${output}`;

      if (
        recordedOutputs.has(key)
      ) {
        continue;
      }

      recordedOutputs.add(key);

      /*
       * IMPORTANTE:
       *
       * Não enviamos o valor encontrado.
       *
       * Só enviamos:
       * - seletor
       * - nome da variável de saída
       *
       * O Worker vai extrair o valor
       * durante a execução real.
       */
      send(
        "extract_text",
        el,
        {
          output,
        },
      );

      captured = true;
    }

    return captured;
  };

  const inspectPostAction = () => {
    const success =
      captureSuccessMessage();

    const output =
      captureOutputs();

    return {
      success,
      output,
    };
  };

  const clearPostActionWatch = () => {
    try {
      sessionStorage.removeItem(
        POST_ACTION_KEY,
      );
    } catch {}

    if (
      window.__studioPostObserver
    ) {
      window.__studioPostObserver
        .disconnect();

      window.__studioPostObserver =
        null;
    }

    if (
      window.__studioPostTimer
    ) {
      clearInterval(
        window.__studioPostTimer,
      );

      window.__studioPostTimer =
        null;
    }

    if (
      window.__studioPostTimeout
    ) {
      clearTimeout(
        window.__studioPostTimeout,
      );

      window.__studioPostTimeout =
        null;
    }
  };

  const startPostActionWatch = (
    deadline = Date.now() + 8000,
  ) => {
    clearPostActionWatch();

    try {
      sessionStorage.setItem(
        POST_ACTION_KEY,
        String(deadline),
      );
    } catch {}

    const check = () => {
      const found =
        inspectPostAction();

      /*
       * Se encontramos tanto confirmação
       * quanto retorno, não precisamos mais
       * continuar observando.
       */
      if (
        found.success &&
        found.output
      ) {
        clearPostActionWatch();
        return;
      }

      if (
        Date.now() >= deadline
      ) {
        clearPostActionWatch();
      }
    };

    window.__studioPostObserver =
      new MutationObserver(check);

    window.__studioPostObserver
      .observe(
        document.documentElement,
        {
          childList: true,
          subtree: true,
          characterData: true,
          attributes: true,
        },
      );

    window.__studioPostTimer =
      setInterval(
        check,
        200,
      );

    window.__studioPostTimeout =
      setTimeout(
        clearPostActionWatch,
        Math.max(
          0,
          deadline - Date.now(),
        ),
      );

    setTimeout(
      check,
      50,
    );
  };

  /*
   * Se o submit causou navegação na mesma origem,
   * sessionStorage permite continuar procurando
   * resultado na nova página.
   */
  try {
    const pendingUntil =
      Number(
        sessionStorage.getItem(
          POST_ACTION_KEY,
        ) || 0,
      );

    if (
      pendingUntil >
      Date.now()
    ) {
      setTimeout(
        () =>
          startPostActionWatch(
            pendingUntil,
          ),
        150,
      );
    }
  } catch {}

  /*
   * SUBMIT DETECTION
   */

  const isSubmitControl = (el) => {
    if (
      el instanceof
      HTMLButtonElement
    ) {
      return (
        !el.type ||
        el.type === "submit"
      );
    }

    if (
      el instanceof
      HTMLInputElement
    ) {
      return (
        el.type === "submit" ||
        el.type === "image"
      );
    }

    return false;
  };

  const shouldInspectResult = (
    el,
    form,
  ) => {
    const description =
      cleanText(
        [
          el.id,
          el.name,
          el.textContent,
          el.value,
          form?.id,
          form?.name,
        ]
          .filter(Boolean)
          .join(" "),
      ).toLowerCase();

    /*
     * Login não é uma operação de
     * provisionamento.
     */
    if (
      /\b(login|log in|signin|sign in|entrar|authenticate|autenticar)\b/i
        .test(description)
    ) {
      return false;
    }

    /*
     * Operações mutáveis comuns.
     */
    return (
      /\b(save|create|submit|confirm|apply|update|provision|add|grant|enable|disable|delete|remove|unlock|change|salvar|criar|confirmar|aplicar|atualizar|provisionar|adicionar|conceder|ativar|desativar|excluir|remover|desbloquear|alterar)\b/i
        .test(description)
    );
  };

  /*
   * CLIQUES
   */

  document.addEventListener(
    "click",

    (event) => {
      const el =
        event.target.closest(
          [
            "button",
            "a[href]",
            '[role="button"]',
            'input[type="button"]',
            'input[type="submit"]',
            'input[type="reset"]',
            'input[type="image"]',
          ].join(","),
        );

      if (!el) return;

      if (el.disabled) {
        return;
      }

      if (
        isSubmitControl(el)
      ) {
        const form =
          el.form ||
          el.closest("form");

        captureFormSelects(
          form,
        );

        if (
          shouldInspectResult(
            el,
            form,
          )
        ) {
          startPostActionWatch();
        }
      }

      send(
        "click",
        el,
      );
    },

    true,
  );

  /*
   * CHANGE
   */

  document.addEventListener(
    "change",

    (event) => {
      const el =
        event.target;

      if (
        !(
          el instanceof
          HTMLElement
        )
      ) {
        return;
      }

      if (
        el.tagName ===
        "SELECT"
      ) {
        recordSelect(el);

        return;
      }

      if (
        el instanceof
          HTMLInputElement &&
        [
          "checkbox",
          "radio",
        ].includes(el.type)
      ) {
        send(
          "check",
          el,
          {
            value:
              String(
                el.checked,
              ),
          },
        );

        return;
      }

      if (
        ![
          "INPUT",
          "TEXTAREA",
        ].includes(
          el.tagName,
        )
      ) {
        return;
      }

      if (
        el instanceof
          HTMLInputElement &&
        [
          "file",
          "button",
          "submit",
          "reset",
          "image",
        ].includes(
          el.type,
        )
      ) {
        return;
      }

      const variable =
        variableName(el);

      send(
        "fill",
        el,
        {
          value:
            "{{" +
            variable +
            "}}",

          secret:
            el instanceof
              HTMLInputElement &&
            el.type ===
              "password",
        },
      );
    },

    true,
  );

  /*
   * TECLADO
   */

  document.addEventListener(
    "keydown",

    (event) => {
      if (
        event.key === "Tab"
      ) {
        if (
          [
            "INPUT",
            "TEXTAREA",
          ].includes(
            event.target.tagName,
          )
        ) {
          event.target.dispatchEvent(
            new Event(
              "change",
              {
                bubbles: true,
              },
            ),
          );
        }

        return;
      }

      if (
        event.key === "Enter"
      ) {
        const form =
          event.target.form ||
          event.target.closest?.(
            "form",
          );

        captureFormSelects(
          form,
        );

        const submit =
          form?.querySelector(
            [
              'button[type="submit"]',
              'button:not([type])',
              'input[type="submit"]',
            ].join(","),
          );

        if (
          submit &&
          shouldInspectResult(
            submit,
            form,
          )
        ) {
          startPostActionWatch();
        }
      }

      if (
        ![
          "Enter",
          "Escape",
        ].includes(
          event.key,
        )
      ) {
        return;
      }

      if (
        [
          "INPUT",
          "TEXTAREA",
        ].includes(
          event.target.tagName,
        )
      ) {
        event.target.dispatchEvent(
          new Event(
            "change",
            {
              bubbles: true,
            },
          ),
        );
      }

      send(
        "press",
        event.target,
        {
          value:
            event.key,
        },
      );
    },

    true,
  );
})();