import asyncio
import time
from pathlib import Path
from urllib.parse import urlsplit

from backend.app.core.security import SENSITIVE, mask, secret_values
from backend.app.rpa.actions.basic import perform
from backend.app.rpa.browser_manager import browser_session
from backend.app.rpa.condition_engine import evaluate_condition
from backend.app.rpa.graph import WorkflowGraph
from backend.app.rpa.variable_engine import resolve
from backend.app.schemas.contracts import Step


class ExecutionCancelled(Exception):
    pass


class GraphNodeNotSupported(Exception):
    pass


class LoopIterationLimit(Exception):
    pass


class Engine:
    def __init__(
        self,
        snapshot: dict,
        inputs: dict,
        artifact_dir: Path,
        emit,
        cancelled,
        credentials: dict | None = None,
    ):
        self.snapshot = snapshot

        credentials = credentials or {}

        self.variables = {
            **inputs,
            "application": snapshot["application"],
            "credential": credentials,
        }

        self.artifact_dir = artifact_dir
        self.emit = emit
        self.cancelled = cancelled

        credential_secrets = list(
            secret_values(credentials)
        )

        self.secrets = [
            *secret_values(inputs),
            *credential_secrets,
        ]

        self.output_secrets = [
            *secret_values(
                {
                    k: v
                    for k, v in inputs.items()
                    if SENSITIVE.search(k)
                }
            ),
            *credential_secrets,
        ]

        self.output: dict = {}
        self.step_id: str | None = None

    async def capture(
        self,
        page,
        step_id: str,
    ) -> None:
        filename = f"{step_id}.png"

        marks = await page.evaluate(
            """(values) => {
          const marked=[];
          for(const el of document.querySelectorAll('body *')) {
            if(
              ['INPUT','TEXTAREA','SELECT'].includes(el.tagName) ||
              [...el.childNodes].some(
                n =>
                  n.nodeType === 3 &&
                  values.some(
                    v =>
                      v &&
                      n.textContent.includes(v)
                  )
              )
            ) {
              if(!el.hasAttribute('data-rpa-private')) {
                el.setAttribute('data-rpa-private','');
                marked.push(el);
              }
            }
          }

          window.__rpaMarked=marked;
          return marked.length;
        }""",
            self.secrets,
        )

        try:
            await page.screenshot(
                path=str(
                    self.artifact_dir / filename
                ),
                full_page=True,
                mask=[
                    page.locator(
                        "[data-rpa-private]"
                    )
                ],
                timeout=5000,
            )

            self.emit(
                "SCREENSHOT",
                step_id,
                artifact=filename,
                masked_elements=marks,
            )

        finally:
            await page.evaluate(
                "() => "
                "(window.__rpaMarked||[])"
                ".forEach("
                "e=>e.removeAttribute('data-rpa-private')"
                ")"
            )

    async def execute_step(
        self,
        page,
        step: Step,
    ) -> None:
        self.step_id = step.id

        if self.cancelled():
            raise ExecutionCancelled()

        if not step.enabled:
            self.emit(
                "STEP_SKIPPED",
                step.id,
            )
            return

        if step.secret:
            value = resolve(
                step.value,
                self.variables,
            )

            self.secrets.append(value)
            self.output_secrets.append(value)

        started = time.monotonic()

        self.emit(
            "STEP_STARTED",
            step.id,
            action=step.type,
        )

        result = await perform(
            page,
            step,
            self.variables,
            self.emit,
            lambda sid: self.capture(
                page,
                sid,
            ),
        )

        if result:
            self.output.update(
                mask(
                    result,
                    tuple(
                        self.output_secrets
                    ),
                )
            )

        self.emit(
            "STEP_FINISHED",
            step.id,
            duration=round(
                time.monotonic() - started,
                3,
            ),
        )

    async def run_legacy_steps(
        self,
        page,
    ) -> None:
        self.emit(
            "ENGINE_LEGACY_MODE",
            None,
            steps=len(
                self.snapshot.get(
                    "steps",
                    [],
                )
            ),
        )

        for raw in self.snapshot["steps"]:
            step = Step.model_validate(raw)

            await self.execute_step(
                page,
                step,
            )

        if self.cancelled():
            raise ExecutionCancelled()

    async def run_graph(
        self,
        page,
        graph: WorkflowGraph,
    ) -> None:
        self.emit(
            "ENGINE_GRAPH_MODE",
            None,
            nodes=len(graph.nodes),
            edges=len(graph.edges),
        )

        nodes = {
            node.id: node
            for node in graph.nodes
        }

        outgoing = {
            node.id: {}
            for node in graph.nodes
        }

        for edge in graph.edges:
            outgoing[
                edge.source
            ][edge.branch] = edge.target

        current_id = graph.start_node_id

        loop_iterations = {
            node.id: 0
            for node in graph.nodes
            if node.kind == "loop"
        }

        #
        # Proteção global adicional.
        #
        # O limite individual de cada LOOP continua sendo
        # a principal proteção. Este teto também cobre
        # grafos malformados ou combinações inesperadas.
        #
        base_transitions = (
            len(graph.nodes)
            + len(graph.edges)
            + 1
        )

        loop_budget = sum(
            node.max_iterations or 0
            for node in graph.nodes
            if node.kind == "loop"
        )

        max_transitions = min(
            1_000_000,
            base_transitions
            * (loop_budget + 1),
        )

        transitions = 0

        while True:
            if self.cancelled():
                raise ExecutionCancelled()

            if transitions > max_transitions:
                raise RuntimeError(
                    "GRAPH_TRANSITION_LIMIT"
                )

            node = nodes[current_id]

            if node.kind == "end":
                return

            if node.kind == "start":
                current_id = outgoing[
                    node.id
                ]["default"]

                transitions += 1
                continue

            if node.kind == "action":
                await self.execute_step(
                    page,
                    node.step,
                )

                current_id = outgoing[
                    node.id
                ]["default"]

                transitions += 1
                continue

            if node.kind == "condition":
                #
                # Usa o ID do nó como referência caso
                # a avaliação da condição falhe.
                #
                self.step_id = node.id

                result = evaluate_condition(
                    node.expression,
                    self.variables,
                )

                branch = (
                    "true"
                    if result
                    else "false"
                )

                #
                # Não registrar expression nem valores.
                #
                self.emit(
                    "CONDITION_EVALUATED",
                    node.id,
                    result=result,
                    branch=branch,
                )

                current_id = outgoing[
                    node.id
                ][branch]

                transitions += 1
                continue

            if node.kind == "loop":
                self.step_id = node.id

                result = evaluate_condition(
                    node.expression,
                    self.variables,
                )

                completed = loop_iterations[
                    node.id
                ]

                if not result:
                    self.emit(
                        "LOOP_EVALUATED",
                        node.id,
                        result=False,
                        branch="exit",
                        iteration=completed,
                        max_iterations=node.max_iterations,
                    )

                    current_id = outgoing[
                        node.id
                    ]["exit"]

                    transitions += 1
                    continue

                if completed >= node.max_iterations:
                    self.emit(
                        "LOOP_LIMIT_REACHED",
                        node.id,
                        iteration=completed,
                        max_iterations=node.max_iterations,
                    )

                    raise LoopIterationLimit(
                        node.id
                    )

                completed += 1

                loop_iterations[
                    node.id
                ] = completed

                self.emit(
                    "LOOP_EVALUATED",
                    node.id,
                    result=True,
                    branch="body",
                    iteration=completed,
                    max_iterations=node.max_iterations,
                )

                current_id = outgoing[
                    node.id
                ]["body"]

                transitions += 1
                continue

            raise GraphNodeNotSupported(
                node.kind
            )

    async def run(self) -> dict:
        self.artifact_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        async with browser_session(
            self.snapshot["application"]
        ) as (_, page):
            try:
                async with asyncio.timeout(
                    self.snapshot[
                        "timeout_seconds"
                    ]
                ):
                    graph_data = self.snapshot.get(
                        "graph"
                    )

                    if graph_data:
                        graph = (
                            WorkflowGraph
                            .model_validate(
                                graph_data
                            )
                        )

                        await self.run_graph(
                            page,
                            graph,
                        )

                    else:
                        await self.run_legacy_steps(
                            page
                        )

                return self.output

            except ExecutionCancelled:
                raise

            except Exception as exc:
                #
                # Nunca salvar exception message.
                # Playwright pode incluir valores digitados.
                #
                parsed = urlsplit(
                    page.url
                )

                self.emit(
                    "STEP_FAILED",
                    self.step_id,
                    exception=type(
                        exc
                    ).__name__,
                    url=mask(
                        (
                            f"{parsed.scheme}://"
                            f"{parsed.netloc}"
                            f"{parsed.path}"
                        ),
                        tuple(
                            self.secrets
                        ),
                    ),
                )

                try:
                    await self.capture(
                        page,
                        self.step_id
                        or "error",
                    )

                    structure = await (
                        page.locator("body")
                        .evaluate(
                            "el => "
                            "[...el.querySelectorAll('*')]"
                            ".slice(0,100)"
                            ".map(e=>e.tagName)"
                            ".join(' > ')"
                        )
                    )

                    self.emit(
                        "PAGE_STRUCTURE",
                        self.step_id,
                        tags=structure,
                    )

                except Exception as capture_error:
                    self.emit(
                        "EVIDENCE_UNAVAILABLE",
                        self.step_id,
                        exception=type(
                            capture_error
                        ).__name__,
                    )

                raise
