import asyncio

from playwright.async_api import expect

from backend.app.core.security import check_url
from backend.app.rpa.selector_engine import choose
from backend.app.rpa.variable_engine import resolve


async def perform(page, step, variables, emit, capture):
    if step.type == "navigate":
        await page.goto(
            check_url(resolve(step.url, variables)),
            wait_until="domcontentloaded",
            timeout=step.timeout_ms,
        )
        return
    if step.type == "wait":
        await asyncio.sleep(step.wait_ms / 1000)
        return
    if step.type == "screenshot":
        await capture(step.id)
        return
    target = await choose(page, step.selectors, step.timeout_ms, emit, step.id)
    value = resolve(step.value, variables)
    match step.type:
        case "click":
            await target.click(timeout=step.timeout_ms)
        case "fill":
            # A missed secret flag must not permit literal password persistence.
            if await target.get_attribute("type") == "password" and "{{" not in step.value:
                raise ValueError("Password requer referência de variável")
            await target.fill(value, timeout=step.timeout_ms)
        case "select":
            await target.select_option(value, timeout=step.timeout_ms)
        case "extract_text":
            variables[step.output] = (await target.inner_text(timeout=step.timeout_ms))[:10000]
            return {step.output: variables[step.output]}
        case "assert_text":
            await expect(target).to_contain_text(value, timeout=step.timeout_ms)
        case "check":
            await target.set_checked(
                value.lower() not in {"false", "0", "no"}, timeout=step.timeout_ms
            )
        case "press":
            await target.press(value, timeout=step.timeout_ms)
        case "hover":
            await target.hover(timeout=step.timeout_ms)
