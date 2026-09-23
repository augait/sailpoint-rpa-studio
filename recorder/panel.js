const status = document.querySelector("#status");
const statusPill = document.querySelector("#status-pill");
const statusLabel = document.querySelector("#status-label");

const startButton = document.querySelector("#start-button");
const stopButton = document.querySelector("#stop");
const clearButton = document.querySelector("#clear");
const exportButton = document.querySelector("#export");

const urlInput = document.querySelector("#url");

const timeline = document.querySelector("#timeline");
const empty = document.querySelector("#empty");

const metricSteps = document.querySelector("#metric-steps");
const metricState = document.querySelector("#metric-state");
const metricTarget = document.querySelector("#metric-target");

const timelineCount = document.querySelector("#timeline-count");

let lastCount = -1;
let wasRecording = false;


async function post(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || "Falha na operação",
    );
  }

  return data;
}


function setMessage(message, type = "") {
  status.textContent = message;

  status.className =
    "message" +
    (type ? ` ${type}` : "");
}


function setRecorderState(state) {
  statusPill.classList.remove(
    "recording",
    "finished",
  );

  if (state === "recording") {
    statusPill.classList.add("recording");

    statusLabel.textContent =
      "GRAVANDO";

    metricState.textContent =
      "Gravando";

    startButton.disabled = true;
    stopButton.disabled = false;
    urlInput.disabled = true;

    return;
  }

  if (state === "finished") {
    statusPill.classList.add("finished");

    statusLabel.textContent =
      "FINALIZADO";

    metricState.textContent =
      "Finalizado";

    startButton.disabled = false;
    stopButton.disabled = true;
    urlInput.disabled = false;

    return;
  }

  statusLabel.textContent =
    "PRONTO";

  metricState.textContent =
    "Pronto";

  startButton.disabled = false;
  stopButton.disabled = true;
  urlInput.disabled = false;
}


function iconFor(type) {
  const icons = {
    navigate: "↗",
    fill: "✎",
    click: "●",
    select: "⌄",
    press: "⌨",
    check: "✓",
    wait: "◷",
    screenshot: "▣",
    hover: "◇",
    extract_text: "T",
    assert_text: "✓",
  };

  return icons[type] || "•";
}


function targetFor(step) {
  if (step.url) {
    return step.url;
  }

  if (
    step.selectors &&
    step.selectors.length
  ) {
    const best =
      step.selectors.find(
        (selector) =>
          selector.kind === "css",
      ) ||
      step.selectors[0];

    return best.value || "";
  }

  if (step.value) {
    return step.value;
  }

  return "";
}


function createStep(step) {
  const item =
    document.createElement("li");

  item.className =
    `step ${step.type || ""}`;

  const icon =
    document.createElement("div");

  icon.className =
    "step-icon";

  icon.textContent =
    iconFor(step.type);

  const main =
    document.createElement("div");

  main.className =
    "step-main";

  const name =
    document.createElement("div");

  name.className =
    "step-name";

  name.textContent =
    step.name ||
    step.type ||
    "Action";

  const target =
    document.createElement("div");

  target.className =
    "step-target";

  target.textContent =
    targetFor(step) || "—";

  main.append(
    name,
    target,
  );

  const time =
    document.createElement("span");

  time.className =
    "step-time";

  if (
    typeof step.recorded_at ===
    "number"
  ) {
    time.textContent =
      `${step.recorded_at.toFixed(1)}s`;
  } else {
    time.textContent = "";
  }

  item.append(
    icon,
    main,
    time,
  );

  return item;
}


function renderSteps(steps) {
  const count =
    steps.length;

  metricSteps.textContent =
    String(count);

  timelineCount.textContent =
    String(count);

  if (!count) {
    timeline.hidden = true;
    empty.hidden = false;
    timeline.replaceChildren();

    return;
  }

  empty.hidden = true;
  timeline.hidden = false;

  timeline.replaceChildren(
    ...steps.map(createStep),
  );

  if (count !== lastCount) {
    timeline.lastElementChild?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }

  lastCount = count;
}


function updateTarget(sourceUrl) {
  if (!sourceUrl) {
    metricTarget.textContent = "—";
    metricTarget.title = "Nenhuma";

    return;
  }

  metricTarget.textContent =
    sourceUrl;

  metricTarget.title =
    sourceUrl;
}


async function refresh() {
  try {
    const response =
      await fetch("/events", {
        cache: "no-store",
      });

    if (!response.ok) {
      throw new Error(
        "Agente indisponível",
      );
    }

    const data =
      await response.json();

    renderSteps(
      data.steps || [],
    );

    updateTarget(
      data.source_url,
    );

    if (data.recording) {
      setRecorderState(
        "recording",
      );

      wasRecording = true;

      setMessage(
        "Gravando — execute o processo normalmente no navegador aberto.",
      );

      return;
    }

    if (
      wasRecording ||
      (data.steps || []).length > 0
    ) {
      setRecorderState(
        "finished",
      );
    } else {
      setRecorderState(
        "ready",
      );
    }
  } catch {
    setMessage(
      "Não foi possível comunicar com o agente local.",
      "error",
    );
  }
}


document
  .querySelector("#start")
  .addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const url =
        urlInput.value.trim();

      if (!url) {
        setMessage(
          "Informe a URL da aplicação.",
          "error",
        );

        return;
      }

      setMessage(
        "Abrindo navegador...",
      );

      startButton.disabled = true;

      try {
        await post(
          "/start",
          {
            url,
          },
        );

        wasRecording = true;

        setRecorderState(
          "recording",
        );

        setMessage(
          "Gravação iniciada. Execute o fluxo no navegador aberto.",
          "success",
        );

        await refresh();
      } catch (error) {
        setRecorderState(
          "ready",
        );

        setMessage(
          error.message,
          "error",
        );
      }
    },
  );


stopButton.addEventListener(
  "click",
  async () => {
    stopButton.disabled = true;

    setMessage(
      "Finalizando gravação...",
    );

    try {
      const data =
        await post("/stop");

      setRecorderState(
        "finished",
      );

      setMessage(
        `Gravação concluída com ${data.count} etapas.`,
        "success",
      );

      await refresh();
    } catch (error) {
      setMessage(
        error.message,
        "error",
      );
    }
  },
);


clearButton.addEventListener(
  "click",
  async () => {
    if (
      !confirm(
        "Limpar todas as etapas gravadas?",
      )
    ) {
      return;
    }

    try {
      await post("/reset");

      lastCount = -1;
      wasRecording = false;

      renderSteps([]);

      updateTarget(null);

      setRecorderState(
        "ready",
      );

      setMessage(
        "Gravação limpa.",
        "success",
      );
    } catch (error) {
      setMessage(
        error.message,
        "error",
      );
    }
  },
);


exportButton.addEventListener(
  "click",
  () => {
    setMessage(
      "Exportando recording.json...",
      "success",
    );
  },
);


setRecorderState("ready");
refresh();

setInterval(
  refresh,
  700,
);