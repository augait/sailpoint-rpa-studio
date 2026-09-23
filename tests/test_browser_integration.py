"""Real Chromium + demo HTTP server + RQ serializer/queue + SQLite persistence.
Run explicitly with RUN_BROWSER_TESTS=1. Redis transport uses fakeredis here.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright
from rq import Queue, SimpleWorker
from rq.serializers import JSONSerializer

from backend.app.core.config import settings
from backend.app.services import execution_service
from scripts.demo_workflow import template

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_BROWSER_TESTS") != "1", reason="Explicit browser suite"
)


@pytest.fixture
def legacy_server(tmp_path):
    env = {
        **os.environ,
        "DEMO_PASSWORD": "Fictitious-demo-only!",
        "DEMO_DB": str(tmp_path / "legacy.db"),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "demo.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "18081",
            "--no-access-log",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            try:
                if (
                    httpx.get("http://127.0.0.1:18081", timeout=0.2, trust_env=False).status_code
                    == 200
                ):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("Legacy server unavailable")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_real_create_account_and_failure_evidence(client, users, redis, monkeypatch, legacy_server):
    q = Queue("rpa", connection=redis, serializer=JSONSerializer)
    monkeypatch.setattr(execution_service, "queue", lambda: q)
    headers = users["ADMIN"]
    app = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"name": "Demo", "url": "http://127.0.0.1:18081"},
    ).json()
    workflow = client.post(
        "/api/v1/workflows", headers=headers, json={**template(), "application_id": app["id"]}
    ).json()
    inputs = {
        "admin_username": "demo-admin",
        "admin_password": "Fictitious-demo-only!",
        "username": "john.doe",
        "firstname": "John",
        "lastname": "Doe",
        "email": "john.doe@test.local",
        "department": "IT",
    }
    queued = client.post(
        f"/api/v1/workflows/{workflow['id']}/execute", headers=headers, json={"input": inputs}
    ).json()
    SimpleWorker([q], connection=redis, serializer=JSONSerializer).work(burst=True)
    result = client.get("/api/v1/executions/" + queued["id"], headers=headers).json()
    logs = client.get(f"/api/v1/executions/{queued['id']}/logs", headers=headers).json()
    assert result["status"] == "SUCCESS", (result, logs)
    assert result["output"]["accountId"] == "john.doe"
    assert inputs["admin_password"] not in json.dumps(logs)
    assert len([event for event in logs if event["event"] == "STEP_FINISHED"]) == 14
    bad = {
        "application_id": app["id"],
        "name": "Missing element",
        "steps": [
            {"id": "open", "type": "navigate", "url": "{{application.url}}"},
            {
                "id": "missing",
                "type": "click",
                "selectors": [{"kind": "css", "value": "#not-here"}],
                "timeout_ms": 300,
            },
        ],
    }
    workflow = client.post("/api/v1/workflows", json=bad, headers=headers).json()
    queued = client.post(
        f"/api/v1/workflows/{workflow['id']}/execute", json={"input": {}}, headers=headers
    ).json()
    SimpleWorker([q], connection=redis, serializer=JSONSerializer).work(burst=True)
    result = client.get("/api/v1/executions/" + queued["id"], headers=headers).json()
    assert result["status"] == "TIMEOUT"
    path = settings().artifact_dir / queued["id"] / "missing.png"
    assert path.is_file() and path.stat().st_size > 1000
    assert client.get(f"/api/v1/executions/{queued['id']}/artifacts/missing.png").status_code == 401
    assert (
        client.get(
            f"/api/v1/executions/{queued['id']}/artifacts/missing.png", headers=headers
        ).status_code
        == 200
    )


def test_recorder_captures_dom_without_password(legacy_server):
    actions = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.expose_binding("studioRecord", lambda source, action: actions.append(action))
        context.add_init_script(path=str(Path("recorder/capture.js")))
        page = context.new_page()
        page.goto("http://127.0.0.1:18081")
        page.locator("#login-username").fill("demo-admin")
        page.locator("#login-password").fill("Fictitious-demo-only!")
        page.locator("#login").click()
        page.locator("#users").wait_for()
        browser.close()
    assert any(a["type"] == "click" for a in actions)
    assert any(a.get("secret") and a["value"] == "{{admin_password}}" for a in actions)
    assert "Fictitious-demo-only!" not in json.dumps(actions)


def test_studio_ui_create_edit_execute(client, users, redis, monkeypatch, legacy_server, tmp_path):
    q = Queue("rpa", connection=redis, serializer=JSONSerializer)
    monkeypatch.setattr(execution_service, "queue", lambda: q)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))

        def bridge(route):
            request = route.request
            response = client.request(
                request.method,
                request.url.replace("https://studio.test", ""),
                content=request.post_data_buffer,
                headers={
                    k: v for k, v in request.headers.items() if k not in ["host", "content-length"]
                },
            )
            route.fulfill(
                status=response.status_code,
                body=response.content,
                headers={
                    k: v
                    for k, v in response.headers.items()
                    if k not in ["content-length", "content-encoding"]
                },
            )

        page.route("https://studio.test/**", bridge)
        page.goto("https://studio.test/")
        page.locator("[name=username]").fill("admin")
        page.locator("[name=password]").fill("Testing-only-123!")
        page.get_by_role("button", name="Entrar no Studio").click()
        page.get_by_role("heading", name="Visão geral").wait_for()
        page.locator("[data-view=applications]").click()
        page.get_by_role("button", name="+ Nova aplicação").click()
        page.locator("#app-form [name=name]").fill("Legacy UI Test")
        page.locator("#app-form [name=url]").fill("http://127.0.0.1:18081")
        page.get_by_role("button", name="Cadastrar aplicação").click()
        page.get_by_role("heading", name="Legacy UI Test").wait_for()
        page.locator("[data-view=workflows]").click()
        page.get_by_role("button", name="+ Novo workflow").click()
        page.locator("#wf-name").fill("UI smoke workflow")
        page.locator("[data-action=add-step][data-id=navigate]").click()
        page.get_by_role("button", name="Aplicar etapa").click()
        page.get_by_role("button", name="Salvar workflow", exact=True).click()
        page.get_by_role("button", name="Executar teste", exact=True).click()
        page.get_by_role("button", name="Enviar para execução").click()
        page.get_by_role("heading", name="UI smoke workflow").wait_for()
        # Playwright sync client owns this thread's event loop; execute the worker
        # entrypoint on a separate thread, as a separate process would in deployment.
        from concurrent.futures import ThreadPoolExecutor

        from worker.tasks import execute

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(execute, q.job_ids[0]).result(timeout=30)
        page.locator(".badge.SUCCESS").wait_for(timeout=10000)
        page.locator("[data-view=dashboard]").click()
        page.get_by_role("heading", name="Visão geral").wait_for()
        output = Path(os.getenv("UI_SCREENSHOT_DIR", str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / "studio-dashboard.png"), full_page=True)
        page.locator("[data-view=workflows]").click()
        page.get_by_role("button", name="Abrir designer").click()
        page.get_by_role("heading", name="Workflow designer").wait_for()
        page.screenshot(path=str(output / "studio-designer.png"), full_page=True)
        browser.close()
    assert errors == []
