from contextlib import asynccontextmanager

import pytest

from backend.app.rpa import engine as module
from backend.app.rpa.engine import (
    Engine,
    ExecutionCancelled,
    LoopIterationLimit,
)


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



def loop_graph(
    expression="{{counter}} < 3",
    max_iterations=5,
):
    return {
        "start_node_id": "__start__",
        "end_node_id": "__end__",
        "nodes": [
            {
                "id": "__start__",
                "kind": "start",
            },
            {
                "id": "loop_counter",
                "kind": "loop",
                "expression": expression,
                "max_iterations": max_iterations,
            },
            {
                "id": "loop_action",
                "kind": "action",
                "step": {
                    "id": "body_action",
                    "type": "wait",
                    "wait_ms": 1,
                },
            },
            {
                "id": "__end__",
                "kind": "end",
            },
        ],
        "edges": [
            {
                "id": "start-loop",
                "source": "__start__",
                "target": "loop_counter",
                "branch": "default",
            },
            {
                "id": "loop-body",
                "source": "loop_counter",
                "target": "loop_action",
                "branch": "body",
            },
            {
                "id": "loop-exit",
                "source": "loop_counter",
                "target": "__end__",
                "branch": "exit",
            },
            {
                "id": "body-loop",
                "source": "loop_action",
                "target": "loop_counter",
                "branch": "default",
            },
        ],
    }


async def test_graph_loop_executes_until_condition_false(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    order = []
    events = []

    async def perform(
        page,
        step,
        variables,
        *args,
    ):
        order.append(step.id)
        variables["counter"] += 1

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
            "graph": loop_graph(),
        },
        {
            "counter": 0,
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
        "body_action",
        "body_action",
        "body_action",
    ]

    loop_events = [
        event
        for event in events
        if event[0] == "LOOP_EVALUATED"
    ]

    assert [
        (
            event[2]["result"],
            event[2]["branch"],
            event[2]["iteration"],
        )
        for event in loop_events
    ] == [
        (True, "body", 1),
        (True, "body", 2),
        (True, "body", 3),
        (False, "exit", 3),
    ]


async def test_graph_loop_can_exit_without_body(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    order = []

    async def perform(
        page,
        step,
        variables,
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
            "graph": loop_graph(),
        },
        {
            "counter": 3,
        },
        tmp_path,
        lambda *args, **kwargs: None,
        lambda: False,
    )

    assert await rpa.run() == {}
    assert order == []


async def test_graph_loop_enforces_iteration_limit(
    fake_browser,
    tmp_path,
    monkeypatch,
):
    order = []
    events = []

    async def perform(
        page,
        step,
        variables,
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
            "graph": loop_graph(
                expression="{{continue_loop}} == true",
                max_iterations=2,
            ),
        },
        {
            "continue_loop": True,
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

    with pytest.raises(
        LoopIterationLimit
    ):
        await rpa.run()

    assert order == [
        "body_action",
        "body_action",
    ]

    limit_events = [
        event
        for event in events
        if event[0] == "LOOP_LIMIT_REACHED"
    ]

    assert len(limit_events) == 1

    assert limit_events[0][1] == "loop_counter"

    assert limit_events[0][2] == {
        "iteration": 2,
        "max_iterations": 2,
    }


def test_credentials_are_available_and_masked(
    tmp_path,
):
    password = "engine-test-secret"

    rpa = Engine(
        snapshot([]),
        {},
        tmp_path,
        lambda *a, **kw: None,
        lambda: False,
        credentials={
            "legacy_login": {
                "username": "engine_user",
                "password": password,
            }
        },
    )

    assert (
        rpa.variables[
            "credential"
        ][
            "legacy_login"
        ][
            "username"
        ]
        == "engine_user"
    )

    assert (
        rpa.variables[
            "credential"
        ][
            "legacy_login"
        ][
            "password"
        ]
        == password
    )

    assert password in rpa.secrets
    assert password in rpa.output_secrets
