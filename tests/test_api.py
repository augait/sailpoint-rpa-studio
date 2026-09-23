from types import SimpleNamespace

from backend.app.core.database import Session
from backend.app.core.security import unseal
from backend.app.models.entities import Execution
from backend.app.services import execution_service


def create_workflow(client, headers):
    response = client.post(
        "/api/v1/applications",
        headers=headers,
        json={"name": "Legacy", "url": "http://127.0.0.1:18081"},
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name": "Example",
            "application_id": response.json()["id"],
            "steps": [{"id": "wait", "type": "wait", "wait_ms": 5}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_login_and_rate_limit(client, users, redis):
    r = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "Testing-only-123!"}
    )
    assert r.status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}
        ).json()["role"]
        == "ADMIN"
    )
    for _ in range(9):
        client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
        ).status_code
        == 429
    )


def test_auth_rbac_and_security_headers(client, users):
    assert client.get("/api/v1/applications").status_code == 401
    response = client.post(
        "/api/v1/applications",
        headers=users["VIEWER"],
        json={"name": "a", "url": "http://127.0.0.1:18081"},
    )
    assert response.status_code == 403
    assert client.get("/api/v1/audit", headers=users["OPERATOR"]).status_code == 403
    assert client.get("/").headers["x-frame-options"] == "DENY"


def test_workflow_concurrency_guard(client, users):
    workflow = create_workflow(client, users["ADMIN"])
    body = {k: workflow[k] for k in ["name", "application_id", "steps", "revision"]}
    url = "/api/v1/workflows/" + workflow["id"]
    assert client.put(url, json=body, headers=users["ADMIN"]).status_code == 200
    assert client.put(url, json=body, headers=users["ADMIN"]).status_code == 409


def test_snapshot_queue_and_idempotency(client, users, monkeypatch):
    jobs = []
    monkeypatch.setattr(
        execution_service,
        "queue",
        lambda: SimpleNamespace(enqueue=lambda *a, **kw: jobs.append((a, kw))),
    )
    workflow = create_workflow(client, users["ADMIN"])
    url = f"/api/v1/workflows/{workflow['id']}/execute"
    headers = {**users["OPERATOR"], "Idempotency-Key": "SP-123"}
    response = client.post(url, headers=headers, json={"input": {"password": "private"}})
    assert response.status_code == 202, response.text
    execution = response.json()
    assert "private" not in response.text
    assert execution["status"] == "QUEUED" and len(jobs) == 1
    assert (
        client.post(url, headers=headers, json={"input": {"password": "private"}}).json()["id"]
        == execution["id"]
    )
    assert len(jobs) == 1
    assert (
        client.post(url, headers=headers, json={"input": {"password": "different"}}).status_code
        == 409
    )
    with Session() as db:
        record = db.get(Execution, execution["id"])
        assert unseal(record.input_encrypted)["password"] == "private"
        assert record.snapshot["revision"] == 1
    assert (
        client.post(
            f"/api/v1/executions/{execution['id']}/cancel", headers=users["OPERATOR"]
        ).json()["status"]
        == "CANCELLED"
    )


def test_queue_failure_not_success(client, users, monkeypatch):
    def fail(*a, **kw):
        raise ConnectionError()

    monkeypatch.setattr(execution_service, "queue", lambda: SimpleNamespace(enqueue=fail))
    wf = create_workflow(client, users["ADMIN"])
    response = client.post(
        f"/api/v1/workflows/{wf['id']}/execute", headers=users["ADMIN"], json={"input": {}}
    )
    assert response.status_code == 503
    assert client.get("/api/v1/executions", headers=users["ADMIN"]).json()[0]["status"] == "FAILED"


def test_validation_does_not_echo_secrets(client, users):
    wf = create_workflow(client, users["ADMIN"])
    body = {
        "name": "Bad",
        "application_id": wf["application_id"],
        "steps": [
            {
                "id": "a",
                "type": "fill",
                "selectors": [{"value": "#password"}],
                "value": "never-echo-this",
            }
        ],
    }
    response = client.post("/api/v1/workflows", json=body, headers=users["ADMIN"])
    assert response.status_code == 422
    assert "never-echo-this" not in response.text
