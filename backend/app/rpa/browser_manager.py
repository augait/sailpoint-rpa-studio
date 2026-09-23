from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

from backend.app.core.security import check_url


@asynccontextmanager
async def browser_session(application: dict):
    async with async_playwright() as playwright:
        name = application["browser"]
        browser_type = playwright.firefox if name == "firefox" else playwright.chromium
        options = {"headless": application["headless"]}
        if name in {"chrome", "msedge"}:
            options["channel"] = name
        browser = await browser_type.launch(**options)
        try:
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                service_workers="block",
                accept_downloads=False,
            )

            async def gate(route):
                try:
                    check_url(route.request.url)
                except ValueError:
                    await route.abort("blockedbyclient")
                else:
                    await route.continue_()

            await context.route("**/*", gate)
            page = await context.new_page()
            page.set_default_timeout(application["timeout_ms"])
            yield context, page
        finally:
            await browser.close()
