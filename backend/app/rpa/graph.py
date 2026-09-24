from typing import Literal

from pydantic import Field, model_validator

from backend.app.schemas.contracts import Step, StrictModel


NodeKind = Literal[
    "start",
    "end",
    "action",
    "condition",
    "loop",
]

EdgeBranch = Literal[
    "default",
    "true",
    "false",
    "body",
    "exit",
]


class GraphNode(StrictModel):
    id: str = Field(
        pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )

    kind: NodeKind

    #
    # ACTION reutiliza exatamente o contrato Step que
    # já existe hoje.
    #
    step: Step | None = None

    #
    # CONDITION será interpretada pelo engine depois.
    #
    expression: str = Field(
        default="",
        max_length=2000,
    )

    #
    # LOOP sempre precisa de limite explícito.
    #
    max_iterations: int | None = Field(
        default=None,
        ge=1,
        le=1000,
    )

    @model_validator(mode="after")
    def validate_node(self):
        if self.kind == "action":
            if self.step is None:
                raise ValueError(
                    "Nó ACTION precisa de step"
                )

            if self.expression:
                raise ValueError(
                    "Nó ACTION não aceita expression"
                )

            if self.max_iterations is not None:
                raise ValueError(
                    "Nó ACTION não aceita max_iterations"
                )

        elif self.kind == "condition":
            if not self.expression.strip():
                raise ValueError(
                    "Nó CONDITION precisa de expression"
                )

            if self.step is not None:
                raise ValueError(
                    "Nó CONDITION não aceita step"
                )

            if self.max_iterations is not None:
                raise ValueError(
                    "Nó CONDITION não aceita max_iterations"
                )

        elif self.kind == "loop":
            if not self.expression.strip():
                raise ValueError(
                    "Nó LOOP precisa de expression"
                )

            if self.max_iterations is None:
                raise ValueError(
                    "Nó LOOP precisa de max_iterations"
                )

            if self.step is not None:
                raise ValueError(
                    "Nó LOOP não aceita step"
                )

        else:
            if self.step is not None:
                raise ValueError(
                    "START/END não aceitam step"
                )

            if self.expression:
                raise ValueError(
                    "START/END não aceitam expression"
                )

            if self.max_iterations is not None:
                raise ValueError(
                    "START/END não aceitam max_iterations"
                )

        return self


class GraphEdge(StrictModel):
    id: str = Field(
        pattern=r"^[A-Za-z0-9_.:-]{1,220}$"
    )

    source: str = Field(
        pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )

    target: str = Field(
        pattern=r"^[A-Za-z0-9_-]{1,100}$"
    )

    branch: EdgeBranch = "default"


class WorkflowGraph(StrictModel):
    nodes: list[GraphNode] = Field(
        min_length=2,
        max_length=500,
    )

    edges: list[GraphEdge] = Field(
        min_length=1,
        max_length=1000,
    )

    start_node_id: str = "__start__"
    end_node_id: str = "__end__"

    @model_validator(mode="after")
    def validate_graph(self):
        node_ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError(
                "IDs de nós duplicados"
            )

        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError(
                "IDs de edges duplicados"
            )

        if self.start_node_id == self.end_node_id:
            raise ValueError(
                "START e END precisam ser diferentes"
            )

        nodes = {
            node.id: node
            for node in self.nodes
        }

        start = nodes.get(self.start_node_id)
        end = nodes.get(self.end_node_id)

        if not start:
            raise ValueError(
                "START não encontrado"
            )

        if not end:
            raise ValueError(
                "END não encontrado"
            )

        if start.kind != "start":
            raise ValueError(
                "start_node_id precisa apontar para START"
            )

        if end.kind != "end":
            raise ValueError(
                "end_node_id precisa apontar para END"
            )

        outgoing: dict[str, list[GraphEdge]] = {
            node_id: []
            for node_id in nodes
        }

        incoming: dict[str, list[GraphEdge]] = {
            node_id: []
            for node_id in nodes
        }

        edge_keys = set()

        for edge in self.edges:
            if edge.source not in nodes:
                raise ValueError(
                    f"Edge {edge.id} possui source inexistente"
                )

            if edge.target not in nodes:
                raise ValueError(
                    f"Edge {edge.id} possui target inexistente"
                )

            if edge.source == edge.target:
                raise ValueError(
                    "Self-loop não é permitido"
                )

            key = (
                edge.source,
                edge.target,
                edge.branch,
            )

            if key in edge_keys:
                raise ValueError(
                    "Edge duplicada"
                )

            edge_keys.add(key)

            outgoing[edge.source].append(edge)
            incoming[edge.target].append(edge)

        if incoming[self.start_node_id]:
            raise ValueError(
                "START não pode possuir entrada"
            )

        if outgoing[self.end_node_id]:
            raise ValueError(
                "END não pode possuir saída"
            )

        #
        # Regras de saída por tipo de nó.
        #
        for node in self.nodes:
            edges = outgoing[node.id]
            branches = [edge.branch for edge in edges]

            if node.kind == "start":
                if (
                    len(edges) != 1
                    or branches != ["default"]
                ):
                    raise ValueError(
                        "START precisa de exatamente uma saída default"
                    )

            elif node.kind == "end":
                if edges:
                    raise ValueError(
                        "END não pode possuir saída"
                    )

            elif node.kind == "action":
                if (
                    len(edges) != 1
                    or branches != ["default"]
                ):
                    raise ValueError(
                        f"ACTION {node.id} precisa de uma saída default"
                    )

            elif node.kind == "condition":
                if (
                    len(edges) != 2
                    or set(branches)
                    != {"true", "false"}
                ):
                    raise ValueError(
                        f"CONDITION {node.id} precisa das branches true e false"
                    )

            elif node.kind == "loop":
                if (
                    len(edges) != 2
                    or set(branches)
                    != {"body", "exit"}
                ):
                    raise ValueError(
                        f"LOOP {node.id} precisa das branches body e exit"
                    )

        #
        # Todos os nós precisam ser alcançáveis pelo START.
        #
        reachable = set()
        stack = [self.start_node_id]

        while stack:
            node_id = stack.pop()

            if node_id in reachable:
                continue

            reachable.add(node_id)

            stack.extend(
                edge.target
                for edge in outgoing[node_id]
            )

        unreachable = set(nodes) - reachable

        if unreachable:
            raise ValueError(
                "Nós inalcançáveis: "
                + ", ".join(sorted(unreachable))
            )

        #
        # Todos os nós precisam possuir algum caminho até END.
        #
        reaches_end = set()
        stack = [self.end_node_id]

        while stack:
            node_id = stack.pop()

            if node_id in reaches_end:
                continue

            reaches_end.add(node_id)

            stack.extend(
                edge.source
                for edge in incoming[node_id]
            )

        dead_ends = set(nodes) - reaches_end

        if dead_ends:
            raise ValueError(
                "Nós sem caminho até END: "
                + ", ".join(sorted(dead_ends))
            )

        #
        # Detecta ciclos.
        #
        # Um ciclo só é permitido quando contém explicitamente
        # pelo menos um nó LOOP. Isso impede ciclos acidentais
        # criados pelo editor.
        #
        visited = set()
        active = []
        active_set = set()

        def visit(node_id: str):
            if node_id in active_set:
                index = active.index(node_id)
                cycle = active[index:]

                if not any(
                    nodes[item].kind == "loop"
                    for item in cycle
                ):
                    raise ValueError(
                        "Ciclo sem nó LOOP detectado: "
                        + " -> ".join(cycle)
                    )

                return

            if node_id in visited:
                return

            active.append(node_id)
            active_set.add(node_id)

            for edge in outgoing[node_id]:
                visit(edge.target)

            active.pop()
            active_set.remove(node_id)
            visited.add(node_id)

        visit(self.start_node_id)

        return self


def linear_graph_from_steps(
    steps: list[Step | dict],
) -> WorkflowGraph:
    validated_steps = [
        step
        if isinstance(step, Step)
        else Step.model_validate(step)
        for step in steps
    ]

    nodes = [
        GraphNode(
            id="__start__",
            kind="start",
        )
    ]

    nodes.extend(
        GraphNode(
            id=f"node_{step.id}",
            kind="action",
            step=step,
        )
        for step in validated_steps
    )

    nodes.append(
        GraphNode(
            id="__end__",
            kind="end",
        )
    )

    node_ids = [
        node.id
        for node in nodes
    ]

    edges = []

    for source, target in zip(
        node_ids,
        node_ids[1:],
    ):
        edges.append(
            GraphEdge(
                id=f"edge_{source}__{target}",
                source=source,
                target=target,
                branch="default",
            )
        )

    return WorkflowGraph(
        nodes=nodes,
        edges=edges,
        start_node_id="__start__",
        end_node_id="__end__",
    )
