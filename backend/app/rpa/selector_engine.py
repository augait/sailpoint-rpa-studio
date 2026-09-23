import asyncio
import time

from playwright.async_api import Locator, Page

from backend.app.schemas.contracts import Selector


def locator(page: Page, selector: Selector) -> Locator:
    match selector.kind:
        case "testid":
            return page.get_by_test_id(selector.value)
        case "role":
            return page.get_by_role(selector.value, name=selector.name, exact=True)
        case "label":
            return page.get_by_label(selector.value, exact=True)
        case "placeholder":
            return page.get_by_placeholder(selector.value, exact=True)
        case "text":
            return page.get_by_text(selector.value, exact=True)
        case "xpath":
            return page.locator("xpath=" + selector.value)
        case _:
            return page.locator(selector.value)


async def choose(
    page: Page, selectors: list[Selector], timeout_ms: int, emit, step_id: str
) -> Locator:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for index, selector in enumerate(selectors):
            target = locator(page, selector)
            # Never silently pick the first of several matching elements.
            if await target.count() == 1 and await target.is_visible():
                emit("SELECTOR_SELECTED", step_id, selector_index=index, kind=selector.kind)
                if index:
                    emit("SELECTOR_FALLBACK", step_id, selector_index=index, kind=selector.kind)
                return target
        await asyncio.sleep(0.1)
    raise TimeoutError("Nenhum seletor único e visível encontrado")
