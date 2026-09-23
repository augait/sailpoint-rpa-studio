import asyncio
import time
from pathlib import Path
from urllib.parse import urlsplit

from backend.app.core.security import SENSITIVE, mask, secret_values
from backend.app.rpa.actions.basic import perform
from backend.app.rpa.browser_manager import browser_session
from backend.app.rpa.variable_engine import resolve
from backend.app.schemas.contracts import Step


class ExecutionCancelled(Exception):
    pass


class Engine:
    def __init__(self, snapshot: dict, inputs: dict, artifact_dir: Path, emit, cancelled):
        self.snapshot = snapshot
        self.variables = {**inputs, "application": snapshot["application"]}
        self.artifact_dir = artifact_dir
        self.emit = emit
        self.cancelled = cancelled
        self.secrets = list(secret_values(inputs))
        self.output_secrets = list(
            secret_values({k: v for k, v in inputs.items() if SENSITIVE.search(k)})
        )
        self.output: dict = {}
        self.step_id: str | None = None

    async def capture(self, page, step_id: str) -> None:
        filename = f"{step_id}.png"
        # Mask form controls and text nodes containing input data. Restore afterwards.
        marks = await page.evaluate(
            """(values) => {
          const marked=[];
          for(const el of document.querySelectorAll('body *')) {
            if(['INPUT','TEXTAREA','SELECT'].includes(el.tagName) ||
               [...el.childNodes].some(n=>n.nodeType===3 && values.some(v=>v && n.textContent.includes(v)))) {
              if(!el.hasAttribute('data-rpa-private')) {el.setAttribute('data-rpa-private','');marked.push(el);}
            }
          }
          window.__rpaMarked=marked;return marked.length;
        }""",
            self.secrets,
        )
        try:
            await page.screenshot(
                path=str(self.artifact_dir / filename),
                full_page=True,
                mask=[page.locator("[data-rpa-private]")],
                timeout=5000,
            )
            self.emit("SCREENSHOT", step_id, artifact=filename, masked_elements=marks)
        finally:
            await page.evaluate(
                "() => (window.__rpaMarked||[]).forEach(e=>e.removeAttribute('data-rpa-private'))"
            )

    async def run(self) -> dict:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        async with browser_session(self.snapshot["application"]) as (_, page):
            try:
                async with asyncio.timeout(self.snapshot["timeout_seconds"]):
                    for raw in self.snapshot["steps"]:
                        step = Step.model_validate(raw)
                        self.step_id = step.id
                        if self.cancelled():
                            raise ExecutionCancelled()
                        if not step.enabled:
                            self.emit("STEP_SKIPPED", step.id)
                            continue
                        if step.secret:
                            self.secrets.append(resolve(step.value, self.variables))
                            self.output_secrets.append(resolve(step.value, self.variables))
                        started = time.monotonic()
                        self.emit("STEP_STARTED", step.id, action=step.type)
                        result = await perform(
                            page,
                            step,
                            self.variables,
                            self.emit,
                            lambda sid: self.capture(page, sid),
                        )
                        if result:
                            self.output.update(mask(result, tuple(self.output_secrets)))
                        self.emit(
                            "STEP_FINISHED", step.id, duration=round(time.monotonic() - started, 3)
                        )
                    if self.cancelled():
                        raise ExecutionCancelled()
                return self.output
            except ExecutionCancelled:
                raise
            except Exception as exc:
                # Never save exception messages: Playwright includes entered values in call logs.
                parsed = urlsplit(page.url)
                self.emit(
                    "STEP_FAILED",
                    self.step_id,
                    exception=type(exc).__name__,
                    url=mask(
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}", tuple(self.secrets)
                    ),
                )
                try:
                    await self.capture(page, self.step_id or "error")
                    # Diagnostic structure only; omit text, attributes and complete DOM snapshots.
                    structure = await page.locator("body").evaluate(
                        "el => [...el.querySelectorAll('*')].slice(0,100).map(e=>e.tagName).join(' > ')"
                    )
                    self.emit("PAGE_STRUCTURE", self.step_id, tags=structure)
                except Exception as capture_error:
                    self.emit(
                        "EVIDENCE_UNAVAILABLE", self.step_id, exception=type(capture_error).__name__
                    )
                raise
