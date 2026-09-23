import pytest

from backend.app.rpa.selector_engine import choose
from backend.app.schemas.contracts import Selector


class Target:
    def __init__(self, count):
        self.matches = count

    async def count(self):
        return self.matches

    async def is_visible(self):
        return True


class Page:
    def locator(self, value):
        return Target({"#missing": 0, "#duplicate": 2, "#ok": 1}[value])


async def test_fallback_is_logged():
    events = []
    target = await choose(
        Page(),
        [Selector(value="#missing"), Selector(value="#ok")],
        300,
        lambda *a, **kw: events.append((a, kw)),
        "a",
    )
    assert await target.count() == 1
    assert events[-1][0][0] == "SELECTOR_FALLBACK"
    assert events[-1][1]["selector_index"] == 1


async def test_ambiguous_selector_never_chooses_first():
    with pytest.raises(TimeoutError):
        await choose(Page(), [Selector(value="#duplicate")], 200, lambda *a, **kw: None, "a")
