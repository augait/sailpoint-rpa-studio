import pytest

from backend.app.rpa.graph import (
    GraphEdge,
    GraphNode,
    WorkflowGraph,
    linear_graph_from_steps,
)


def test_linear_graph_from_steps():
    graph = linear_graph_from_steps(
        [
            {
                "id": "first",
                "type": "wait",
                "wait_ms": 10,
            },
            {
                "id": "second",
                "type": "wait",
                "wait_ms": 10,
            },
        ]
    )

    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3

    assert graph.nodes[0].kind == "start"
    assert graph.nodes[-1].kind == "end"

    assert (
        graph.nodes[1].step.id
        == "first"
    )

    assert (
        graph.nodes[2].step.id
        == "second"
    )


def test_graph_rejects_dangling_edge():
    with pytest.raises(
        ValueError,
        match="target inexistente",
    ):
        WorkflowGraph(
            nodes=[
                GraphNode(
                    id="__start__",
                    kind="start",
                ),
                GraphNode(
                    id="__end__",
                    kind="end",
                ),
            ],
            edges=[
                GraphEdge(
                    id="edge1",
                    source="__start__",
                    target="missing",
                ),
            ],
        )


def test_graph_rejects_uncontrolled_cycle():
    with pytest.raises(
        ValueError,
        match="Ciclo sem nó LOOP",
    ):
        WorkflowGraph(
            nodes=[
                GraphNode(
                    id="__start__",
                    kind="start",
                ),
                GraphNode(
                    id="condition1",
                    kind="condition",
                    expression="{{approved}}",
                ),
                GraphNode(
                    id="action1",
                    kind="action",
                    step={
                        "id": "wait1",
                        "type": "wait",
                        "wait_ms": 10,
                    },
                ),
                GraphNode(
                    id="__end__",
                    kind="end",
                ),
            ],
            edges=[
                GraphEdge(
                    id="e1",
                    source="__start__",
                    target="condition1",
                ),
                GraphEdge(
                    id="e2",
                    source="condition1",
                    target="action1",
                    branch="true",
                ),
                GraphEdge(
                    id="e3",
                    source="condition1",
                    target="__end__",
                    branch="false",
                ),
                GraphEdge(
                    id="e4",
                    source="action1",
                    target="condition1",
                ),
            ],
        )


def test_explicit_loop_cycle_is_valid():
    graph = WorkflowGraph(
        nodes=[
            GraphNode(
                id="__start__",
                kind="start",
            ),
            GraphNode(
                id="loop1",
                kind="loop",
                max_iterations=5,
            ),
            GraphNode(
                id="action1",
                kind="action",
                step={
                    "id": "wait1",
                    "type": "wait",
                    "wait_ms": 10,
                },
            ),
            GraphNode(
                id="__end__",
                kind="end",
            ),
        ],
        edges=[
            GraphEdge(
                id="e1",
                source="__start__",
                target="loop1",
            ),
            GraphEdge(
                id="e2",
                source="loop1",
                target="action1",
                branch="body",
            ),
            GraphEdge(
                id="e3",
                source="loop1",
                target="__end__",
                branch="exit",
            ),
            GraphEdge(
                id="e4",
                source="action1",
                target="loop1",
            ),
        ],
    )

    assert graph.nodes[1].max_iterations == 5


def test_condition_requires_true_and_false():
    with pytest.raises(
        ValueError,
        match="branches true e false",
    ):
        WorkflowGraph(
            nodes=[
                GraphNode(
                    id="__start__",
                    kind="start",
                ),
                GraphNode(
                    id="condition1",
                    kind="condition",
                    expression="{{approved}}",
                ),
                GraphNode(
                    id="action1",
                    kind="action",
                    step={
                        "id": "wait1",
                        "type": "wait",
                        "wait_ms": 10,
                    },
                ),
                GraphNode(
                    id="__end__",
                    kind="end",
                ),
            ],
            edges=[
                GraphEdge(
                    id="e1",
                    source="__start__",
                    target="condition1",
                ),
                GraphEdge(
                    id="e2",
                    source="condition1",
                    target="action1",
                    branch="true",
                ),
                GraphEdge(
                    id="e3",
                    source="condition1",
                    target="__end__",
                    branch="true",
                ),
                GraphEdge(
                    id="e4",
                    source="action1",
                    target="__end__",
                ),
            ],
        )
