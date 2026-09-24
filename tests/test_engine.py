from contextlib import asynccontextmanager

import pytest

from backend.app.rpa import engine as module
from backend.app.rpa.engine import Engine, ExecutionCancelled


class FakePage:
    url = "http://127.0.0.1:18081"


@pytest.fixture
def fake_browser(monkeypatch):
    @asynccontextmanager
    async def session(application):
        yield None, FakePage()

    monkeypatch.setattr(module, "browser_session", session)


def snapshot(steps, timeout=5):
    return {"application": {}, "timeout_seconds": timeout, "steps": steps}


async def test_step_order_and_disabled(fake_browser, tmp_path, monkeypatch):
    order, events = [], []

    async def perform(page, step, *args):
        order.append(step.id)

    monkeypatch.setattr(module, "perform", perform)
    rpa = Engine(
        snapshot(
            [
                {"id": "a", "type": "wait"},
                {"id": "b", "type": "wait", "enabled": False},
                {"id": "c", "type": "wait"},
            ]
        ),
        {},
        tmp_path,
        lambda event, *a, **kw: events.append(event),
        lambda: False,
    )
    assert await rpa.run() == {}
    assert order == ["a", "c"]
    assert "STEP_SKIPPED" in events


async def test_cancel_before_action(fake_browser, tmp_path):
    rpa = Engine(
        snapshot([{"id": "a", "type": "wait"}]), {}, tmp_path, lambda *a, **kw: None, lambda: True
    )
    with pytest.raises(ExecutionCancelled):
        await rpa.run()


async def test_failure_attempts_screenshot_without_logging_exception(
    fake_browser, tmp_path, monkeypatch
):
    events, captures = [], []

    async def fail(*a):
        raise ValueError("SENSITIVE-PASSWORD")

    async def capture(page, step):
        captures.append(step)

    monkeypatch.setattr(module, "perform", fail)
    rpa = Engine(
        snapshot([{"id": "a", "type": "wait"}]),
        {},
        tmp_path,
        lambda *a, **kw: events.append((a, kw)),
        lambda: False,
    )
    monkeypatch.setattr(rpa, "capture", capture)
    with pytest.raises(ValueError):
        await rpa.run()
    assert captures == ["a"]
    assert "SENSITIVE-PASSWORD" not in str(events)


async def test_workflow_timeout(fake_browser, tmp_path, monkeypatch):
    import asyncio

    async def delay(*a):
        await asyncio.sleep(1)

    monkeypatch.setattr(module, "perform", delay)
    rpa = Engine(
        snapshot([{"id": "a", "type": "wait"}], timeout=0.02),
        {},
        tmp_path,
        lambda *a, **kw: None,
        lambda: False,
    )
    with pytest.raises(TimeoutError):
        await rpa.run()


async def test_graph_executes_edge_order(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    from backend.app.rpa.graph import (
        linear_graph_from_steps,
    )

    order = []
    events = []

    async def perform(
        page,
        step,
        *args,
    ):
        order.append(step.id)

    monkeypatch.setattr(
        module,
        "perform",
        perform,
    )

    graph = linear_graph_from_steps(
        [
            {
                "id": "graph_a",
                "type": "wait",
                "wait_ms": 1,
            },
            {
                "id": "graph_b",
                "type": "wait",
                "wait_ms": 1,
            },
        ]
    ).model_dump(
        mode="json"
    )

    #
    # Bagunça propositalmente a ordem física
    # do array. As edges continuam:
    #
    # START -> graph_a -> graph_b -> END
    #
    graph["nodes"] = [
        graph["nodes"][0],
        graph["nodes"][2],
        graph["nodes"][1],
        graph["nodes"][3],
    ]

    rpa = Engine(
        {
            "application": {},
            "timeout_seconds": 5,

            #
            # Se o Engine usar steps incorretamente,
            # executaria "legacy".
            #
            "steps": [
                {
                    "id": "legacy",
                    "type": "wait",
                    "wait_ms": 1,
                }
            ],

            "graph": graph,
        },
        {},
        tmp_path,
        lambda event, *a, **kw:
            events.append(event),
        lambda: False,
    )

    assert await rpa.run() == {}

    assert order == [
        "graph_a",
        "graph_b",
    ]

    assert (
        "ENGINE_GRAPH_MODE"
        in events
    )

    assert (
        "ENGINE_LEGACY_MODE"
        not in events
    )


def condition_graph():
    return {
        "start_node_id": "__start__",
        "end_node_id": "__end__",
        "nodes": [
            {
                "id": "__start__",
                "kind": "start",
            },
            {
                "id": "action_false",
                "kind": "action",
                "step": {
                    "id": "false_action",
                    "type": "wait",
                    "wait_ms": 1,
                },
            },
            {
                "id": "condition_department",
                "kind": "condition",
                "expression": '{{department}} == "IT"',
            },
            {
                "id": "__end__",
                "kind": "end",
            },
            {
                "id": "action_true",
                "kind": "action",
                "step": {
                    "id": "true_action",
                    "type": "wait",
                    "wait_ms": 1,
                },
            },
        ],
        "edges": [
            {
                "id": "start-condition",
                "source": "__start__",
                "target": "condition_department",
                "branch": "default",
            },
            {
                "id": "condition-true",
                "source": "condition_department",
                "target": "action_true",
                "branch": "true",
            },
            {
                "id": "condition-false",
                "source": "condition_department",
                "target": "action_false",
                "branch": "false",
            },
            {
                "id": "true-end",
                "source": "action_true",
                "target": "__end__",
                "branch": "default",
            },
            {
                "id": "false-end",
                "source": "action_false",
                "target": "__end__",
                "branch": "default",
            },
        ],
    }


async def test_graph_condition_true_branch(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    order = []
    events = []

    async def perform(
        page,
        step,
        *args,
    ):
        order.append(step.id)

    monkeypatch.setattr(
        module,
        "perform",
        perform,
    )

    rpa = Engine(
        {
            "application": {},
            "timeout_seconds": 5,
            "steps": [],
            "graph": condition_graph(),
        },
        {
            "department": "IT",
        },
        tmp_path,
        lambda event, step_id=None, **details:
            events.append(
                (
                    event,
                    step_id,
                    details,
                )
            ),
        lambda: False,
    )

    assert await rpa.run() == {}

    assert order == [
        "true_action",
    ]

    condition_events = [
        event
        for event in events
        if event[0]
        == "CONDITION_EVALUATED"
    ]

    assert condition_events == [
        (
            "CONDITION_EVALUATED",
            "condition_department",
            {
                "result": True,
                "branch": "true",
            },
        )
    ]


async def test_graph_condition_false_branch(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    order = []
    events = []

    async def perform(
        page,
        step,
        *args,
    ):
        order.append(step.id)

    monkeypatch.setattr(
        module,
        "perform",
        perform,
    )

    rpa = Engine(
        {
            "application": {},
            "timeout_seconds": 5,
            "steps": [],
            "graph": condition_graph(),
        },
        {
            "department": "HR",
        },
        tmp_path,
        lambda event, step_id=None, **details:
            events.append(
                (
                    event,
                    step_id,
                    details,
                )
            ),
        lambda: False,
    )

    assert await rpa.run() == {}

    assert order == [
        "false_action",
    ]

    condition_events = [
        event
        for event in events
        if event[0]
        == "CONDITION_EVALUATED"
    ]

    assert condition_events == [
        (
            "CONDITION_EVALUATED",
            "condition_department",
            {
                "result": False,
                "branch": "false",
            },
        )
    ]
