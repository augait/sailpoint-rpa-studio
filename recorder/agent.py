"""Local interactive RPA recorder.

Run on the user's desktop, not on a remote worker.
"""

import asyncio
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
ORIGIN = "http://127.0.0.1:8877"

state = {
    "browser": None,
    "playwright": None,
    "steps": [],
    "started": 0.0,
    "recording": False,
    "source_url": None,
}

lock = asyncio.Lock()


def selector_identity(action: dict) -> str:
    selectors = action.get("selectors") or []

    priorities = {
        "testid": 0,
        "css": 1,
        "label": 2,
        "role": 3,
        "placeholder": 4,
        "text": 5,
        "xpath": 6,
    }

    ordered = sorted(
        selectors,
        key=lambda item: priorities.get(
            item.get("kind", ""),
            99,
        ),
    )

    for selector in ordered:
        value = selector.get("value")

        if value:
            return (
                f"{selector.get('kind', '')}:"
                f"{value}:"
                f"{selector.get('name', '')}"
            )

    return ""


def friendly_name(action: dict) -> str:
    action_type = action.get(
        "type",
        "action",
    )

    selectors = (
        action.get("selectors")
        or []
    )

    label = None

    #
    # Primeiro tenta transformar um ID CSS
    # em nome curto e previsível.
    #
    for selector in selectors:
        value = selector.get(
            "value",
            "",
        )

        if (
            selector.get("kind")
            == "css"
            and value.startswith("#")
        ):
            label = (
                value[1:]
                .replace("-", " ")
                .replace("_", " ")
            )

            break

    #
    # Depois tenta label/text/placeholder.
    #
    if not label:
        for selector in selectors:
            if selector.get(
                "kind"
            ) in {
                "label",
                "text",
                "placeholder",
            }:
                value = selector.get(
                    "value"
                )

                if value:
                    label = value
                    break

    if not label:
        for selector in selectors:
            if (
                selector.get("kind")
                == "role"
                and selector.get("name")
            ):
                label = selector["name"]
                break

    names = {
        "navigate": "Open URL",
        "click": "Click",
        "fill": "Fill",
        "wait": "Wait",
        "select": "Select",
        "screenshot": "Screenshot",
        "extract_text": "Extract text",
        "assert_text": "Validate text",
        "check": "Check",
        "press": "Press",
        "hover": "Hover",
    }

    base = names.get(
        action_type,
        action_type
        .replace("_", " ")
        .title(),
    )

    if action_type == "navigate":
        return base

    if action_type == "press":
        return (
            f"{base} "
            f"{action.get('value', '')}"
        ).strip()

    if label:
        pretty = (
            str(label)
            .strip()
            .replace("-", " ")
            .replace("_", " ")
        )

        pretty = (
            pretty[:1].upper()
            + pretty[1:]
        )

        return (
            f"{base} "
            f"{pretty[:60]}"
        )

    return base


def is_duplicate_fill(
    action: dict,
) -> bool:
    identity = selector_identity(
        action,
    )

    if not identity:
        return False

    for previous in reversed(
        state["steps"],
    ):
        if previous["type"] in {
            "navigate",
            "click",
            "select",
            "check",
            "press",
        }:
            break

        if (
            previous["type"]
            == "fill"
            and selector_identity(
                previous
            )
            == identity
        ):
            return True

    return False


def append(action: dict):
    if not state["recording"]:
        return

    if len(state["steps"]) >= 200:
        return

    action_type = action.get(
        "type"
    )

    if not action_type:
        return

    if (
        action_type == "press"
        and action.get("value")
        == "Tab"
    ):
        return

    if (
        action_type == "click"
        and not action.get(
            "selectors"
        )
    ):
        return

    if (
        action_type == "fill"
        and is_duplicate_fill(
            action
        )
    ):
        return

    record = {
        "id": uuid4().hex,
        "name": friendly_name(
            action
        ),
        **action,
        "recorded_at": round(
            time.monotonic()
            - state["started"],
            2,
        ),
    }

    state["steps"].append(
        record
    )


async def stop_browser():
    state["recording"] = False

    if state["browser"]:
        await state[
            "browser"
        ].close()

    if state["playwright"]:
        await state[
            "playwright"
        ].stop()

    state["browser"] = None
    state["playwright"] = None


@asynccontextmanager
async def lifespan(app):
    yield
    await stop_browser()


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def protect(
    request: Request,
    call_next,
):
    if (
        request.headers.get(
            "host"
        )
        != "127.0.0.1:8877"
    ):
        return JSONResponse(
            {
                "detail":
                    "Invalid host"
            },
            status_code=403,
        )

    if (
        request.method == "POST"
        and request.headers.get(
            "origin"
        )
        != ORIGIN
    ):
        return JSONResponse(
            {
                "detail":
                    "Invalid origin"
            },
            status_code=403,
        )

    result = await call_next(
        request
    )

    result.headers[
        "Cache-Control"
    ] = "no-store"

    result.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'"
    )

    result.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    return result


class Start(BaseModel):
    url: str = Field(
        max_length=2000
    )


@app.get("/")
def home():
    return FileResponse(
        ROOT / "index.html"
    )


@app.get("/panel.js")
def script():
    return FileResponse(
        ROOT / "panel.js",
        media_type=(
            "text/javascript"
        ),
    )


@app.get("/style.css")
def style():
    return FileResponse(
        ROOT / "style.css",
        media_type="text/css",
    )


@app.post("/start")
async def start(
    body: Start,
):
    parsed = urlsplit(
        body.url
    )

    if (
        parsed.scheme
        not in {
            "http",
            "https",
        }
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise HTTPException(
            422,
            (
                "Use uma URL "
                "HTTP(S), sem "
                "credenciais"
            ),
        )

    async with lock:
        if state["recording"]:
            raise HTTPException(
                409,
                "Gravação já iniciada",
            )

        await stop_browser()

        state["steps"] = []
        state["started"] = (
            time.monotonic()
        )
        state["recording"] = True
        state["source_url"] = (
            body.url
        )

        try:
            pw = (
                await async_playwright()
                .start()
            )

            state[
                "playwright"
            ] = pw

            browser = (
                await pw.chromium
                .launch(
                    headless=False,
                )
            )

            state[
                "browser"
            ] = browser

            context = (
                await browser
                .new_context(
                    service_workers=(
                        "block"
                    ),
                )
            )

            await (
                context
                .expose_binding(
                    "studioRecord",
                    lambda source,
                    action:
                        append(action),
                )
            )

            await (
                context
                .add_init_script(
                    path=str(
                        ROOT
                        / "capture.js"
                    ),
                )
            )

            page = (
                await context
                .new_page()
            )

            append(
                {
                    "type":
                        "navigate",
                    "url":
                        "{{application.url}}",
                }
            )

            await page.goto(
                body.url,
                wait_until=(
                    "domcontentloaded"
                ),
                timeout=30000,
            )

        except Exception as exc:
            await stop_browser()

            #
            # Agora o terminal também
            # mostra o erro real.
            #
            print(
                "[RECORDER ERROR]",
                repr(exc),
                flush=True,
            )

            raise HTTPException(
                400,
                (
                    "Não foi possível "
                    "abrir o navegador: "
                    f"{type(exc).__name__}"
                ),
            )

    return {
        "recording": True,
        "source_url": body.url,
    }


@app.post("/stop")
async def stop():
    async with lock:
        await stop_browser()

    return {
        "count":
            len(state["steps"]),
    }


@app.post("/reset")
async def reset():
    async with lock:
        if state["recording"]:
            raise HTTPException(
                409,
                (
                    "Pare a gravação "
                    "antes de limpar."
                ),
            )

        state["steps"] = []
        state["started"] = 0.0
        state["source_url"] = None

    return {
        "cleared": True,
    }


@app.get("/events")
def events():
    return {
        "recording":
            state["recording"],

        "steps":
            state["steps"],

        "source_url":
            state["source_url"],
    }


@app.get("/export")
def export():
    steps = []

    for step in state[
        "steps"
    ]:
        clean = {
            key: value
            for key, value
            in step.items()
            if key
            != "recorded_at"
        }

        steps.append(
            clean
        )

    return JSONResponse(
        {
            "steps": steps,
        },
        headers={
            "Content-Disposition":
                (
                    "attachment; "
                    'filename="recording.json"'
                )
        },
    )


if __name__ == "__main__":
    webbrowser.open(
        ORIGIN
    )

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8877,
    )