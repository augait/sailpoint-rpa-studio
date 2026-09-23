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
