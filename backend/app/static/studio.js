import {
  api,
  esc,
  button,
  modal,
  toast,
  state,
  bind,
  badge,
  time,
  empty,
} from "./utils.js";
const view = document.querySelector("#view");
const actions = [
  "navigate",
  "click",
  "fill",
  "wait",
  "select",
  "screenshot",
  "extract_text",
  "assert_text",
  "check",
  "press",
  "hover",
];
const labels = {
  navigate: "Abrir URL",
  click: "Clicar",
  fill: "Preencher campo",
  wait: "Aguardar",
  select: "Selecionar opção",
  screenshot: "Capturar tela",
  extract_text: "Extrair texto",
  assert_text: "Validar texto",
  check: "Marcar opção",
  press: "Pressionar tecla",
  hover: "Passar o mouse",
};
let page = "dashboard",
  selected = null,
  workflow = null,
  poll = null;
const head = (title, subtitle, buttons = "") =>
  `<div class="page-head"><div><p class="eyebrow">AUTOMAÇÃO DE IDENTIDADES</p><h1>${title}</h1><p class="muted">${subtitle}</p></div><div class="actions">${buttons}</div></div>`;
const canEdit = () => ["ADMIN", "DEVELOPER"].includes(state.role);
const canRun = () => ["ADMIN", "DEVELOPER", "OPERATOR"].includes(state.role);

function isLinearGraphForSteps(graph, steps = []) {
  if (!graph) return true;

  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];

  const expectedIds = [
    "__start__",
    ...steps.map((step) => `node_${step.id}`),
    "__end__",
  ];

  if (
    graph.start_node_id !== "__start__" ||
    graph.end_node_id !== "__end__" ||
    nodes.length !== expectedIds.length ||
    edges.length !== expectedIds.length - 1
  ) {
    return false;
  }

  const nodeById = new Map(
    nodes.map((node) => [node.id, node]),
  );

  if (
    nodeById.get("__start__")?.kind !== "start" ||
    nodeById.get("__end__")?.kind !== "end"
  ) {
    return false;
  }

  for (const step of steps) {
    const node = nodeById.get(`node_${step.id}`);

    if (
      node?.kind !== "action" ||
      node.step?.id !== step.id
    ) {
      return false;
    }
  }

  for (let index = 0; index < expectedIds.length - 1; index += 1) {
    const source = expectedIds[index];
    const target = expectedIds[index + 1];

    const matches = edges.filter(
      (edge) =>
        edge.source === source &&
        edge.target === target &&
        edge.branch === "default",
    );

    if (matches.length !== 1) {
      return false;
    }
  }

  return edges.every(
    (edge) => edge.branch === "default",
  );
}

const hasNativeGraph = (graph, steps = []) =>
  !!graph && !isLinearGraphForSteps(graph, steps);
const metric = (label, value, sub) =>
  `<div class="metric"><div class="label">${label}<span>↗</span></div><strong>${value ?? "—"}</strong><small>${sub}</small></div>`;
function table(rows) {
  return rows.length
    ? `<div class="scroll-table"><table><thead><tr><th>WORKFLOW / EXECUÇÃO</th><th>STATUS</th><th>INÍCIO</th><th>DURAÇÃO</th><th></th></tr></thead><tbody>${rows.map((r) => `<tr><td><b>${esc(r.snapshot.name)}</b><br><small class="muted">${esc(r.id.slice(0, 8))} · rev. ${r.snapshot.revision}</small></td><td>${badge(r.status)}</td><td>${time(r.created_at)}</td><td>${r.duration == null ? "—" : r.duration.toFixed(1) + " s"}</td><td>${button("Abrir", "execution", r.id)}</td></tr>`).join("")}</tbody></table></div>`
    : empty(
        "Nenhuma execução ainda",
        "Crie um workflow e execute seu primeiro processo.",
      );
}
async function dashboard() {
  const [d, rows] = await Promise.all([
    api("/dashboard"),
    api("/executions?limit=6"),
  ]);
  view.innerHTML =
    head(
      "Visão geral",
      "Acompanhe sua operação de automação em um só lugar.",
      canEdit() ? button("+ Novo workflow", "new-workflow", "", "primary") : "",
    ) +
    `<div class="hero"><div><h2>Seu próximo processo começa aqui.</h2><p>Conecte aplicações legadas a fluxos consistentes e rastreáveis.</p></div><span class="hero-icon">◇</span></div><div class="metrics">${metric("APLICAÇÕES", d.applications, "Sistemas cadastrados")}${metric("WORKFLOWS", d.workflows, "Processos disponíveis")}${metric("EXECUÇÕES HOJE", d.executions_today, "Desde 00:00 UTC")}${metric("WORKERS ONLINE", d.workers_online, "Registro atual no Redis")}</div><div class="grid-two"><section class="panel"><div class="panel-head"><h2>Últimas execuções</h2>${button("Ver todas →", "nav", "executions")}</div>${table(rows)}</section><section class="panel"><div class="panel-head"><h2>Saúde da operação</h2><span class="pill">Todo o período</span></div><div class="panel-body">${[
      ["SUCCESS", "Concluídas"],
      ["RUNNING", "Em execução"],
      ["FAILED", "Com falha"],
      ["TIMEOUT", "Timeout"],
    ]
      .map(
        ([s, l]) =>
          `<div class="status-row">${badge(s)}<span>${l}</span><b>${d.counts[s] || 0}</b></div>`,
      )
      .join(
        "",
      )}<div class="status-row"><span>Jobs na fila</span><b>${d.queue ?? "Indisponível"}</b></div><div class="status-row"><span>Tempo médio</span><b>${d.average_seconds == null ? "—" : d.average_seconds.toFixed(1) + " s"}</b></div></div></section></div>`;
}
async function applications() {
  const rows = await api("/applications");
  view.innerHTML =
    head(
      "Aplicações",
      "Cadastre os sistemas web que serão automatizados.",
      canEdit() ? button("+ Nova aplicação", "new-app", "", "primary") : "",
    ) +
    (rows.length
      ? `<div class="cards">${rows.map((r) => `<article class="app-card"><span class="badge">${esc(r.environment)}</span><h2>${esc(r.name)}</h2><p class="muted">${esc(r.description || "Aplicação web")}</p><div class="url">${esc(r.url)}</div><div class="status-row"><span>${esc(r.browser)}</span><small>${r.headless ? "HEADLESS" : "NAVEGADOR VISÍVEL"}</small></div></article>`).join("")}</div>`
      : empty(
          "Conecte sua primeira aplicação",
          "O destino precisa estar permitido na configuração ALLOWED_ORIGINS.",
        ));
}
function applicationForm() {
  modal(
    `<h2>Nova aplicação</h2><form id="app-form"><div class="form-grid"><label>Nome<input name="name" required maxlength="120" placeholder="Legacy IAM Portal"></label><label>Ambiente<select name="environment"><option>DEV</option><option>HML</option><option>PRD</option></select></label><label class="wide">URL<input name="url" type="url" required placeholder="http://legacy:8081"></label><label class="wide">Descrição<input name="description"></label><label>Navegador<select name="browser"><option value="chromium">Chromium</option><option value="firefox">Firefox</option><option value="chrome">Chrome instalado no worker</option><option value="msedge">Edge instalado no worker</option></select></label><label>Timeout (ms)<input name="timeout_ms" type="number" value="30000" min="500" max="60000"></label></div><label class="checkbox"><input name="headless" type="checkbox" checked> Executar sem janela (headless)</label><p class="hint">Modo visível exige um worker com sessão gráfica. Dentro do Docker, mantenha headless habilitado.</p><button class="primary">Cadastrar aplicação</button><p class="error" id="form-error"></p></form>`,
  );
  bind("#app-form", "submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const data = Object.fromEntries(new FormData(f));
    data.timeout_ms = Number(data.timeout_ms);
    data.headless = f.headless.checked;
    await api("/applications", "POST", data);
    document.querySelector("#modal").close();
    await applications();
    toast("Aplicação cadastrada.");
  });
}
async function workflows() {
  const rows = await api("/workflows");

  const enriched = await Promise.all(
    rows.map(async (workflow) => {
      const versions = await api(`/workflows/${workflow.id}/versions`);
      const current =
        versions.find((v) => v.version === workflow.current_version) || null;

      return {
        ...workflow,
        version_status: current?.status || "UNKNOWN",
      };
    }),
  );

  view.innerHTML =
    head(
      "Workflows",
      "Desenhe, publique e mantenha versões imutáveis dos seus processos.",
      canEdit() ? button("+ Novo workflow", "new-workflow", "", "primary") : "",
    ) +
    `<section class="panel">${
      enriched.length
        ? `<table>
            <thead>
              <tr>
                <th>PROCESSO</th>
                <th>OPERAÇÃO</th>
                <th>ETAPAS</th>
                <th>VERSÃO</th>
                <th>STATUS</th>
                <th>REVISÃO</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${enriched
                .map(
                  (r) => `
                    <tr>
                      <td><b>${esc(r.name)}</b></td>
                      <td><span class="badge">${esc(r.operation)}</span></td>
                      <td>${r.steps.length}</td>
                      <td>v${r.current_version}</td>
                      <td><span class="badge ${esc(r.version_status)}">${esc(r.version_status)}</span></td>
                      <td>${r.revision}</td>
                      <td>${button("Abrir designer", "edit-workflow", r.id)}</td>
                    </tr>
                  `,
                )
                .join("")}
            </tbody>
          </table>`
        : empty(
            "Um processo, várias possibilidades",
            "Comece adicionando uma aplicação e um workflow.",
          )
    }</section>`;
}
async function designer(id) {
  const apps = await api("/applications");
  if (!apps.length) {
    toast("Cadastre uma aplicação primeiro.");
    return navigate("applications");
  }

  workflow = id
    ? await api("/workflows/" + id)
    : {
        name: "Novo workflow",
        application_id: apps[0].id,
        operation: "CREATE_ACCOUNT",
        timeout_seconds: 600,
        steps: [],
        current_version: 1,
      };

  let versionStatus = "DRAFT";

  if (workflow.id) {
    const versions = await api(`/workflows/${workflow.id}/versions`);
    const current = versions.find(
      (v) => v.version === workflow.current_version,
    );

    versionStatus = current?.status || "UNKNOWN";

    //
    // Workflow mantém steps por compatibilidade,
    // mas a estrutura funcional da Fase 2 vive na versão.
    //
    workflow.graph = current?.graph || null;
  }

  workflow.version_status = versionStatus;
  workflow.native_graph = hasNativeGraph(
    workflow.graph,
    workflow.steps,
  );

  page = "designer";
  clearInterval(poll);

  const versionActions = workflow.id
    ? `${button("Histórico", "workflow-history", workflow.id)}
       ${
         canEdit() && versionStatus === "DRAFT"
           ? button("Publicar", "publish-workflow", workflow.id, "secondary")
           : ""
       }`
    : "";

  const paletteBody = workflow.native_graph
    ? `<p class="notice">
         Este workflow possui um grafo ramificado.
         O designer sequencial está em modo de preservação:
         metadados e execução continuam disponíveis, mas a
         estrutura do grafo não será convertida para uma lista linear.
       </p>`
    : `${actions
        .map(
          (action, index) =>
            button(
              `${String(index + 1).padStart(2, "0")} · ${labels[action]}`,
              "add-step",
              action,
            ),
        )
        .join("")}
       <hr>
       ${button("◉ Abrir Recorder", "recorder")}
       ${button("↥ Importar gravação", "import")}
       <input
         id="import-file"
         type="file"
         accept="application/json"
         hidden
       >`;

  view.innerHTML =
    head(
      "Workflow designer",
      `v${workflow.current_version || 1} · ${versionStatus} · alterações entram em vigor após salvar.`,
      `${button("← Voltar", "nav", "workflows")}
       ${versionActions}
       ${
         canEdit()
           ? button("Salvar workflow", "save-workflow", "", "primary")
           : ""
       }
       ${
         canRun()
           ? button("Executar teste", "run-workflow", "", "secondary")
           : ""
       }`,
    ) +
    `<div class="workflow-meta form-grid"><label>Nome do processo<input id="wf-name" value="${esc(workflow.name)}"></label><label>Aplicação<select id="wf-app">${apps.map((a) => `<option value="${a.id}" ${a.id === workflow.application_id ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</select></label><label>Operação IAM<input id="wf-operation" value="${esc(workflow.operation)}"></label><label>Timeout total (segundos)<input id="wf-timeout" type="number" min="5" max="3600" value="${workflow.timeout_seconds}"></label></div><div class="designer"><section class="panel palette"><div class="panel-head"><h2>Ações</h2></div><div class="panel-body">${paletteBody}</div></section><section><div class="step-list"><div class="start-end">● START</div><div id="steps"></div><div class="start-end">● END</div></div><p class="hint">Variáveis: {{username}}, {{email}}, {{password}}. Senhas devem ser fornecidas na execução. Fallbacks são tentados na ordem configurada.</p></section></div>`;
  renderSteps();

  if (!workflow.native_graph) {
    bind("#import-file", "change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (file.size > 1000000) throw Error("Arquivo excede 1 MB");
      const data = JSON.parse(await file.text());
      const steps = Array.isArray(data) ? data : data.steps;
      if (!Array.isArray(steps) || steps.length > 200)
        throw Error("Gravação inválida");
      workflow.steps = steps;
      renderSteps();
      toast("Gravação importada. Revise as etapas antes de salvar.");
    });
  }
}
function renderSteps() {
  const container = document.querySelector("#steps");

  if (workflow.native_graph) {
    const nodes = workflow.graph?.nodes || [];
    const edges = workflow.graph?.edges || [];

    const visibleNodes = nodes.filter(
      (node) =>
        node.kind !== "start" &&
        node.kind !== "end",
    );

    container.innerHTML =
      visibleNodes
        .map((node, index) => {
          const outgoing = edges
            .filter((edge) => edge.source === node.id)
            .map(
              (edge) =>
                `${edge.branch} → ${edge.target}`,
            )
            .join(" · ");

          if (node.kind === "condition") {
            return `
              <div class="step">
                <span class="step-index">◇</span>
                <div>
                  <b>CONDITION</b>
                  <small>
                    ${esc(node.expression)}
                    ${outgoing ? ` · ${esc(outgoing)}` : ""}
                  </small>
                </div>
                <div class="actions">
                  <span class="badge">READ ONLY</span>
                </div>
              </div>
            `;
          }

          if (node.kind === "loop") {
            return `
              <div class="step">
                <span class="step-index">↻</span>
                <div>
                  <b>LOOP</b>
                  <small>
                    ${esc(node.id)}
                    · máximo ${esc(node.max_iterations)}
                    ${outgoing ? ` · ${esc(outgoing)}` : ""}
                  </small>
                </div>
                <div class="actions">
                  <span class="badge">READ ONLY</span>
                </div>
              </div>
            `;
          }

          const step = node.step || {};

          return `
            <div class="step ${step.enabled === false ? "disabled" : ""}">
              <span class="step-index">${index + 1}</span>
              <div>
                <b>${esc(step.name || labels[step.type] || step.type || "ACTION")}</b>
                <small>
                  ${esc(step.type || "action")}
                  · ${esc(step.id || node.id)}
                  ${outgoing ? ` · ${esc(outgoing)}` : ""}
                </small>
              </div>
              <div class="actions">
                <span class="badge">READ ONLY</span>
              </div>
            </div>
          `;
        })
        .join("") ||
      empty(
        "Grafo sem nós executáveis",
        "A versão atual não possui ACTION, CONDITION ou LOOP.",
      );

    return;
  }

  container.innerHTML =
    workflow.steps
      .map(
        (s, i) =>
          `<div class="step ${s.enabled === false ? "disabled" : ""}"><span class="step-index">${i + 1}</span><div><b>${esc(s.name || labels[s.type] || s.type)}</b><small>${esc(s.type)} · ${esc(s.selectors?.[0]?.value || s.url || "")}</small></div><div class="actions">${button("↑", "up-step", i)}${button("↓", "down-step", i)}${button("Editar", "edit-step", i)}${button("⧉", "duplicate-step", i)}${button("×", "delete-step", i)}</div></div>`,
      )
      .join("") ||
    empty(
      "Adicione a primeira etapa",
      "Escolha uma ação na paleta ou importe uma gravação.",
    );
}

function stepForm(index, type) {
  const old = index === null ? null : workflow.steps[index];
  const s = old || {
    id: crypto.randomUUID(),
    type,
    name: labels[type],
    enabled: true,
    selectors: [],
    value: "",
    url: type === "navigate" ? "{{application.url}}" : "",
    output: "result",
    timeout_ms: 10000,
    wait_ms: 1000,
    secret: false,
  };
  modal(
    `<h2>${esc(labels[s.type])} · Propriedades</h2><form id="step-form"><label>Nome da etapa<input name="name" value="${esc(s.name || "")}"></label>${s.type === "navigate" ? `<label>URL<input name="url" value="${esc(s.url || "")}"></label>` : ""}${!["navigate", "screenshot", "wait"].includes(s.type) ? `<label>Seletor principal e alternativas</label><div id="selectors">${(s.selectors.length ? s.selectors : [{ kind: "css", value: "" }]).map(selectorRow).join("")}</div>${button("+ Seletor alternativo", "selector-add")}<p class="hint">Prefira testid, ID/CSS, role ou label. Um seletor precisa identificar exatamente um elemento visível.</p>` : ""}${["fill", "select", "assert_text", "check", "press"].includes(s.type) ? `<label>Valor ou variável<input name="value" value="${esc(s.value || "")}" placeholder="{{username}}"></label>` : ""}${s.type === "extract_text" ? `<label>Variável de saída<input name="output" value="${esc(s.output || "result")}"></label>` : ""}<div class="form-grid"><label>Timeout (ms)<input name="timeout_ms" type="number" value="${s.timeout_ms || 10000}" min="200" max="60000"></label>${s.type === "wait" ? `<label>Espera (ms)<input name="wait_ms" type="number" min="0" max="30000" value="${s.wait_ms || 1000}"></label>` : ""}</div><label class="checkbox"><input name="enabled" type="checkbox" ${s.enabled !== false ? "checked" : ""}> Etapa habilitada</label>${s.type === "fill" ? `<label class="checkbox"><input name="secret" type="checkbox" ${s.secret ? "checked" : ""}> Campo sensível (exige referência de variável)</label>` : ""}<button class="primary">Aplicar etapa</button><p id="form-error" class="error"></p></form>`,
  );
  bind("#step-form", "submit", (e) => {
    e.preventDefault();
    const f = e.target;
    const v = Object.fromEntries(new FormData(f));
    const selectors = [...f.querySelectorAll(".selector-row")].map((row) => ({
      kind: row.querySelector("select").value,
      value: row.querySelector("[data-selector-value]").value,
      ...(row.querySelector("[data-selector-name]").value
        ? { name: row.querySelector("[data-selector-name]").value }
        : {}),
    }));
    const step = {
      ...s,
      ...v,
      selectors,
      enabled: f.enabled.checked,
      secret: !!f.secret?.checked,
      timeout_ms: Number(v.timeout_ms),
      wait_ms: Number(v.wait_ms ?? s.wait_ms ?? 1000),
    };
    if (index === null) workflow.steps.push(step);
    else workflow.steps[index] = step;
    document.querySelector("#modal").close();
    renderSteps();
  });
}
function selectorRow(s) {
  return `<div class="selector-row form-grid"><label>Tipo<select>${["css", "testid", "role", "label", "placeholder", "text", "xpath"].map((k) => `<option ${s.kind === k ? "selected" : ""}>${k}</option>`).join("")}</select></label><label>Valor<input data-selector-value value="${esc(s.value)}" required></label><label>Nome acessível (somente role)<input data-selector-name value="${esc(s.name || "")}"></label><div>${button("Remover", "selector-remove")}</div></div>`;
}
async function workflowHistory(id) {
  const versions = await api(`/workflows/${id}/versions`);

  modal(
    `<h2>Histórico de versões</h2>
     <p class="hint">Versões publicadas são imutáveis. Uma nova edição após publicação cria automaticamente um novo DRAFT.</p>
     <div class="version-list">
       ${versions
         .map(
           (v) => `
             <div class="version-row">
               <div>
                 <b>v${v.version}</b>
                 <small>${esc(v.name)}</small>
               </div>
               <span class="badge ${esc(v.status)}">${esc(v.status)}</span>
               <div class="version-date">
                 ${
                   v.published_at
                     ? `Publicado ${time(v.published_at)}`
                     : `Criado ${time(v.created_at)}`
                 }
               </div>
             </div>
           `,
         )
         .join("")}
     </div>`,
  );
}


async function publishWorkflow() {
  if (!workflow?.id) {
    throw Error("Salve o workflow antes de publicar.");
  }

  if (!canEdit()) {
    throw Error("Seu perfil não permite publicar.");
  }

  await saveWorkflow();

  const published = await api(
    `/workflows/${workflow.id}/publish`,
    "POST",
    {},
  );

  toast(`Workflow v${published.version} publicado.`);

  await designer(workflow.id);
}


async function saveWorkflow() {
  if (!canEdit()) throw Error("Seu perfil não permite editar.");
  const body = {
    application_id: document.querySelector("#wf-app").value,
    name: document.querySelector("#wf-name").value,
    operation: document.querySelector("#wf-operation").value,
    timeout_seconds: Number(document.querySelector("#wf-timeout").value),
    steps: workflow.steps,

    //
    // Graph linear é regenerado pelo backend a partir de steps.
    // Graph nativo precisa ser explicitamente preservado.
    //
    ...(workflow.native_graph && workflow.graph
      ? { graph: workflow.graph }
      : {}),

    ...(workflow.revision ? { revision: workflow.revision } : {}),
  };
  workflow = await api(
    "/workflows" + (workflow.id ? "/" + workflow.id : ""),
    workflow.id ? "PUT" : "POST",
    body,
  );
  toast(
    `Workflow salvo · v${workflow.current_version || 1} · revisão ${workflow.revision}`,
  );

  if (workflow.id && page === "designer") {
    await designer(workflow.id);
  }

  return workflow;
}
async function runForm() {
  if (canEdit()) await saveWorkflow();
  if (!workflow.id) throw Error("Salve o workflow antes de executar.");
  const variableSource = {
    steps: workflow.steps,
    graph: workflow.graph || null,
  };

  const names = [
    ...new Set(
      JSON.stringify(variableSource).match(/{{\s*[\w.]+\s*}}/g) || [],
    ),
  ]
    .map((x) => x.replace(/[{}\s]/g, ""))
    .filter((x) => !x.startsWith("application."));
  modal(
    `<h2>Executar teste</h2><p class="hint">O workflow atua de verdade na aplicação selecionada. Utilize o ambiente DEV e dados fictícios.</p><form id="run-form">${names.length ? names.map((n) => `<label>${esc(n)}<input data-var="${esc(n)}" ${/password|secret|token/i.test(n) ? 'type="password" autocomplete="new-password"' : ""} required></label>`).join("") : '<p class="notice">Este workflow não requer variáveis de entrada.</p>'}<button class="primary">Enviar para execução →</button><p id="form-error" class="error"></p></form>`,
  );
  bind("#run-form", "submit", async (e) => {
    e.preventDefault();
    const input = {};
    for (const el of e.target.querySelectorAll("[data-var]")) {
      const parts = el.dataset.var.split(".");
      if (
        parts.some((p) => ["__proto__", "constructor", "prototype"].includes(p))
      )
        throw Error("Nome de variável inválido");
      let cur = input;
      parts.slice(0, -1).forEach((p) => {
        cur[p] ??= {};
        cur = cur[p];
      });
      cur[parts.at(-1)] = el.value;
    }
    const r = await api(
      "/workflows/" + workflow.id + "/execute",
      "POST",
      { input },
      { "Idempotency-Key": crypto.randomUUID() },
    );
    document.querySelector("#modal").close();
    await openExecution(r.id);
  });
}
async function executions(queueOnly = false) {
  const rows = await api("/executions?limit=200");
  view.innerHTML =
    head(
      queueOnly ? "Fila de execução" : "Execuções",
      queueOnly
        ? "Jobs aguardando processamento ou em execução."
        : "Histórico real de execução, logs e evidências.",
    ) +
    `<section class="panel">${table(queueOnly ? rows.filter((r) => ["QUEUED", "RUNNING"].includes(r.status)) : rows)}</section>`;
}
async function openExecution(id) {
  selected = id;
  page = "execution";
  clearInterval(poll);
  await execution();
  poll = setInterval(() => execution().catch(() => {}), 2000);
}
async function execution() {
  const [r, logs] = await Promise.all([
    api("/executions/" + selected),
    api("/executions/" + selected + "/logs"),
  ]);
  if (page !== "execution") return;
  if (!["RUNNING", "QUEUED"].includes(r.status)) clearInterval(poll);
  view.innerHTML =
    head(
      esc(r.snapshot.name),
      `Execução ${esc(r.id)} · Correlação ${esc(r.correlation_id)}`,
      `${badge(r.status)}${canRun() && ["RUNNING", "QUEUED"].includes(r.status) ? button("Cancelar", "cancel", r.id) : ""}`,
    ) +
    `<div class="grid-two"><section class="panel"><div class="panel-head"><h2>Etapas · snapshot revisão ${r.snapshot.revision}</h2></div>${r.snapshot.steps
      .map((s) => {
        const events = logs
          .filter((l) => l.step_id === s.id)
          .map((l) => l.event);
        const failed = events.includes("STEP_FAILED"),
          done = events.includes("STEP_FINISHED");
        return `<div class="run-step"><span class="mark ${failed ? "failed" : ""}">${failed ? "✕" : done ? "✓" : events.includes("STEP_STARTED") ? "→" : "○"}</span><div><b>${esc(s.name || labels[s.type])}</b><small>${esc(s.type)} · ${esc(s.id)}</small></div></div>`;
      })
      .join(
        "",
      )}</section><section class="panel"><div class="panel-head"><h2>Resultado</h2></div><div class="panel-body"><p>Worker: <b>${esc(r.worker || "Aguardando")}</b></p><p>Duração: ${r.duration == null ? "—" : r.duration.toFixed(2) + " s"}</p>${r.error ? `<p class="error">${esc(r.error)}</p>` : ""}<pre>${esc(JSON.stringify(r.output, null, 2))}</pre>${logs
      .filter((l) => l.event === "SCREENSHOT")
      .map((l) =>
        button(
          "Abrir screenshot · " + l.step_id,
          "artifact",
          l.details.artifact,
        ),
      )
      .join(
        "",
      )}</div></section></div><section class="panel"><div class="panel-head"><h2>Logs de execução</h2><small class="muted">Atualização a cada 2 segundos</small></div><div class="panel-body">${logs.map((l) => `<div class="log-line"><time>${time(l.timestamp)}</time><b>${esc(l.event)}</b> ${esc(l.step_id || "")} ${esc(JSON.stringify(l.details))}</div>`).join("") || '<p class="muted">Aguardando o worker…</p>'}</div></section>`;
}
async function workers() {
  const rows = await api("/health/workers", "GET", null, {}, true);
  view.innerHTML =
    head(
      "Workers",
      "Processos registrados no Redis. Workers expirados deixam este registro.",
    ) +
    `<section class="panel">${rows.length ? `<table><thead><tr><th>NOME</th><th>ESTADO</th><th>HOST</th><th>HEARTBEAT</th><th>JOBS CONCLUÍDOS</th></tr></thead><tbody>${rows.map((w) => `<tr><td>${esc(w.name)}</td><td>${esc(w.state)}</td><td>${esc(w.hostname)}</td><td>${time(w.last_heartbeat)}</td><td>${w.successful_jobs}</td></tr>`).join("")}</tbody></table>` : empty("Nenhum worker conectado", "Inicie o serviço worker para processar as execuções.")}</section>`;
}
async function audit() {
  if (state.role !== "ADMIN") {
    view.innerHTML = empty(
      "Acesso restrito",
      "Auditoria está disponível para administradores.",
    );
    return;
  }
  const rows = await api("/audit");
  view.innerHTML =
    head("Auditoria", "Eventos administrativos. Últimos 200 registros.") +
    `<section class="panel"><table><thead><tr><th>QUANDO</th><th>ATOR</th><th>EVENTO</th><th>ORIGEM</th></tr></thead><tbody>${rows.map((r) => `<tr><td>${time(r.timestamp)}</td><td>${esc(r.actor)}</td><td>${esc(r.event)}</td><td>${esc(r.ip || "worker")}</td></tr>`).join("")}</tbody></table></section>`;
}
function settings() {
  view.innerHTML =
    head("Configuração", "Fase 1 · recursos e operação.") +
    `<section class="panel"><div class="panel-body"><h2>Gravador local</h2><p>Execute no computador com interface gráfica:</p><pre>python -m recorder.agent</pre><p class="hint">Depois abra o Recorder, informe a URL e grave suas ações. Ao parar, exporte o JSON e importe no designer. O gravador substitui preenchimentos por variáveis; informe os valores ao executar.</p>${button("Abrir Recorder ↗", "recorder")}<hr><h2>Configuração do servidor</h2><p class="hint">Destinos permitidos, PostgreSQL, Redis e chaves ficam em .env. Consulte o README para instalação e criação de usuários.</p><h2>Próximas fases</h2><p class="hint">React Flow, condições, loops, versões publicadas, vault persistente, scheduler e integração SailPoint fazem parte do roadmap. Não estão ativos nesta versão.</p><p class="notice">Projeto independente; não é um produto oficial da SailPoint.</p></div></section>`;
}
async function navigate(next) {
  clearInterval(poll);
  page = next;
  document
    .querySelectorAll("[data-view]")
    .forEach((b) => b.classList.toggle("active", b.dataset.view === next));
  document.querySelector("#breadcrumb").textContent =
    {
      dashboard: "Visão geral",
      applications: "Aplicações",
      workflows: "Workflows",
      executions: "Execuções",
      queue: "Fila",
      workers: "Workers",
      audit: "Auditoria",
      settings: "Configuração",
    }[next] || next;
  await {
    dashboard,
    applications,
    workflows,
    executions,
    queue: () => executions(true),
    workers,
    audit,
    settings,
  }[next]();
}
function activate() {
  document.querySelector("#login-screen").hidden = true;
  document.querySelector("#studio").hidden = false;
  document.querySelector("#user-label").innerHTML =
    `${esc(state.username)}<small>${esc(state.role)}</small>`;
  return navigate("dashboard");
}
bind("#login-form", "submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  const r = await api("/auth/login", "POST", data);
  Object.assign(state, {
    token: r.access_token,
    role: r.role,
    username: r.username,
  });
  e.target.reset();
  await activate();
});
bind("#logout", "click", () => location.reload());
bind("#close-modal", "click", () => document.querySelector("#modal").close());
bind("#navigation", "click", (e) => {
  const b = e.target.closest("[data-view]");
  if (b) return navigate(b.dataset.view);
});
bind(document, "click", async (e) => {
  const b = e.target.closest("[data-action]");
  if (!b) return;
  const a = b.dataset.action,
    id = b.dataset.id;
  switch (a) {
    case "nav":
      return navigate(id);
    case "new-app":
      return applicationForm();
    case "new-workflow":
      return designer();
    case "edit-workflow":
      return designer(id);
    case "add-step":
      return stepForm(null, id);
    case "edit-step":
      return stepForm(Number(id));
    case "delete-step":
      workflow.steps.splice(Number(id), 1);
      return renderSteps();
    case "duplicate-step":
      workflow.steps.splice(Number(id) + 1, 0, {
        ...structuredClone(workflow.steps[id]),
        id: crypto.randomUUID(),
      });
      return renderSteps();
    case "up-step":
    case "down-step": {
      const from = Number(id),
        to = from + (a === "up-step" ? -1 : 1);
      if (to >= 0 && to < workflow.steps.length)
        [workflow.steps[from], workflow.steps[to]] = [
          workflow.steps[to],
          workflow.steps[from],
        ];
      return renderSteps();
    }
    case "save-workflow":
      return saveWorkflow();
    case "publish-workflow":
      return publishWorkflow();
    case "workflow-history":
      return workflowHistory(id);
    case "run-workflow":
      return runForm();
    case "execution":
      return openExecution(id);
    case "cancel":
      await api("/executions/" + id + "/cancel", "POST", {});
      toast("Cancelamento solicitado; aplicado entre etapas.");
      return execution();
    case "artifact": {
      const response = await fetch(
        "/api/v1/executions/" +
          selected +
          "/artifacts/" +
          encodeURIComponent(id),
        { headers: { Authorization: "Bearer " + state.token } },
      );
      if (!response.ok) throw Error("Evidência indisponível");
      const url = URL.createObjectURL(await response.blob());
      modal(
        `<h2>Evidência · ${esc(id)}</h2><img class="evidence" src="${url}" alt="Screenshot da execução">`,
      );
      document
        .querySelector("#modal")
        .addEventListener("close", () => URL.revokeObjectURL(url), {
          once: true,
        });
      return;
    }
    case "recorder":
      window.open("http://127.0.0.1:8877", "_blank", "noopener");
      toast(
        "O agente local precisa estar em execução: python -m recorder.agent",
      );
      return;
    case "import":
      return document.querySelector("#import-file").click();
    case "selector-add":
      return document
        .querySelector("#selectors")
        .insertAdjacentHTML(
          "beforeend",
          selectorRow({ kind: "css", value: "" }),
        );
    case "selector-remove":
      return b.closest(".selector-row").remove();
  }
});
