from types import SimpleNamespace

from backend.app.core.database import Session
from backend.app.core.security import unseal
from backend.app.models.entities import Execution, OutboxEvent
from backend.app.services import execution_service, outbox_service


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
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id: None,
            enqueue=lambda *a, **kw: jobs.append((a, kw)),
        ),
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
        assert record.workflow_version_id is not None
        assert record.snapshot["revision"] == 1
        assert record.snapshot["version"] == 1
        assert record.snapshot["version_status"] == "DRAFT"

        graph = record.snapshot["graph"]

        assert graph is not None
        assert graph["start_node_id"] == "__start__"
        assert graph["end_node_id"] == "__end__"
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 2
        assert graph["nodes"][1]["kind"] == "action"
        assert graph["nodes"][1]["step"]["id"] == "wait"

        event = db.scalar(
            __import__("sqlalchemy").select(OutboxEvent).where(
                OutboxEvent.aggregate_id == record.id
            )
        )

        assert event is not None
        assert event.event_type == "EXECUTION_ENQUEUE"
        assert event.status == "SENT"
        assert event.dedupe_key == f"execution:{record.id}:enqueue"

    assert (
        client.post(
            f"/api/v1/executions/{execution['id']}/cancel", headers=users["OPERATOR"]
        ).json()["status"]
        == "CANCELLED"
    )


def test_queue_failure_keeps_execution_durable(
    client,
    users,
    monkeypatch,
):
    class FailedQueue:
        def fetch_job(self, job_id):
            return None

        def enqueue(self, *args, **kwargs):
            raise ConnectionError("redis offline")

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: FailedQueue(),
    )

    wf = create_workflow(
        client,
        users["ADMIN"],
    )

    response = client.post(
        f"/api/v1/workflows/{wf['id']}/execute",
        headers=users["ADMIN"],
        json={"input": {}},
    )

    #
    # A API aceitou o pedido porque ele está duravelmente
    # persistido no PostgreSQL.
    #
    assert response.status_code == 202, response.text

    execution_id = response.json()["id"]

    with Session() as db:
        record = db.get(
            Execution,
            execution_id,
        )

        assert record is not None
        assert record.status == "QUEUED"
        assert record.input_encrypted

        event = db.scalar(
            __import__("sqlalchemy").select(
                OutboxEvent
            ).where(
                OutboxEvent.aggregate_id == execution_id
            )
        )

        assert event is not None
        assert event.status == "FAILED"
        assert event.attempts == 1
        assert event.last_error == "ConnectionError"


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


def test_workflow_version_lifecycle(client, users):
    workflow = create_workflow(
        client,
        users["ADMIN"],
    )

    workflow_id = workflow["id"]

    versions = client.get(
        f"/api/v1/workflows/{workflow_id}/versions",
        headers=users["ADMIN"],
    )

    assert versions.status_code == 200

    data = versions.json()

    assert len(data) == 1
    assert data[0]["version"] == 1
    assert data[0]["status"] == "DRAFT"
    assert data[0]["graph"] is not None
    assert data[0]["graph"]["start_node_id"] == "__start__"
    assert data[0]["graph"]["end_node_id"] == "__end__"
    assert len(data[0]["graph"]["nodes"]) == 3
    assert len(data[0]["graph"]["edges"]) == 2

    #
    # Editar um draft não cria versão nova.
    #
    body = {
        "name": "Example edited",
        "application_id": workflow["application_id"],
        "operation": workflow["operation"],
        "timeout_seconds": workflow["timeout_seconds"],
        "steps": workflow["steps"],
        "revision": workflow["revision"],
    }

    # Alterar os steps precisa regenerar o graph.
    body["steps"] = [
        *body["steps"],
        {
            "id": "wait2",
            "type": "wait",
            "wait_ms": 10,
        },
    ]

    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        headers=users["ADMIN"],
        json=body,
    )

    assert response.status_code == 200, response.text

    edited = response.json()

    versions = client.get(
        f"/api/v1/workflows/{workflow_id}/versions",
        headers=users["ADMIN"],
    ).json()

    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["status"] == "DRAFT"
    assert versions[0]["name"] == "Example edited"
    assert versions[0]["graph"] is not None

    action_nodes = [
        node
        for node in versions[0]["graph"]["nodes"]
        if node["kind"] == "action"
    ]

    assert len(action_nodes) == 2
    assert [
        node["step"]["id"]
        for node in action_nodes
    ] == ["wait", "wait2"]

    assert len(
        versions[0]["graph"]["nodes"]
    ) == 4

    assert len(
        versions[0]["graph"]["edges"]
    ) == 3

    #
    # Publicar v1.
    #
    response = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        headers=users["ADMIN"],
    )

    assert response.status_code == 200, response.text

    published = response.json()

    assert published["version"] == 1
    assert published["status"] == "PUBLISHED"
    assert published["published_at"] is not None

    #
    # Editar depois do publish deve criar v2 DRAFT.
    #
    body["name"] = "Example version 2"
    body["revision"] = edited["revision"]

    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        headers=users["ADMIN"],
        json=body,
    )

    assert response.status_code == 200, response.text

    version_two_workflow = response.json()

    assert version_two_workflow["current_version"] == 2

    versions = client.get(
        f"/api/v1/workflows/{workflow_id}/versions",
        headers=users["ADMIN"],
    ).json()

    assert len(versions) == 2

    assert versions[0]["version"] == 2
    assert versions[0]["status"] == "DRAFT"

    assert versions[1]["version"] == 1
    assert versions[1]["status"] == "PUBLISHED"

    #
    # Publicar v2 arquiva automaticamente v1.
    #
    response = client.post(
        f"/api/v1/workflows/{workflow_id}/publish",
        headers=users["ADMIN"],
    )

    assert response.status_code == 200, response.text

    versions = client.get(
        f"/api/v1/workflows/{workflow_id}/versions",
        headers=users["ADMIN"],
    ).json()

    assert versions[0]["version"] == 2
    assert versions[0]["status"] == "PUBLISHED"

    assert versions[1]["version"] == 1
    assert versions[1]["status"] == "ARCHIVED"


def test_outbox_reconciler_retries_failed_event(
    client,
    users,
    monkeypatch,
):
    class FailedQueue:
        def fetch_job(self, job_id):
            return None

        def enqueue(self, *args, **kwargs):
            raise ConnectionError("redis offline")

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: FailedQueue(),
    )

    wf = create_workflow(
        client,
        users["ADMIN"],
    )

    response = client.post(
        f"/api/v1/workflows/{wf['id']}/execute",
        headers=users["ADMIN"],
        json={"input": {}},
    )

    assert response.status_code == 202

    execution_id = response.json()["id"]

    with Session() as db:
        event = db.scalar(
            __import__("sqlalchemy").select(OutboxEvent).where(
                OutboxEvent.aggregate_id == execution_id
            )
        )

        assert event.status == "FAILED"

        # Libera imediatamente para o teste do reconciliador.
        event.available_at = event.created_at
        db.commit()

    jobs = []

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id: None,
            enqueue=lambda *args, **kwargs: jobs.append(
                (args, kwargs)
            ),
        ),
    )

    result = outbox_service.dispatch_pending(limit=10)

    assert result["selected"] == 1
    assert result["sent"] == 1
    assert result["failed"] == 0
    assert len(jobs) == 1

    with Session() as db:
        event = db.scalar(
            __import__("sqlalchemy").select(OutboxEvent).where(
                OutboxEvent.aggregate_id == execution_id
            )
        )

        assert event.status == "SENT"
        assert event.attempts == 2
        assert event.last_error is None
        assert event.processed_at is not None


def native_condition_graph():
    return {
        "start_node_id": "__start__",
        "end_node_id": "__end__",
        "nodes": [
            {
                "id": "__start__",
                "kind": "start",
            },
            {
                "id": "condition_department",
                "kind": "condition",
                "expression": '{{department}} == "IT"',
            },
            {
                "id": "action_it",
                "kind": "action",
                "step": {
                    "id": "it_path",
                    "type": "wait",
                    "wait_ms": 5,
                },
            },
            {
                "id": "action_other",
                "kind": "action",
                "step": {
                    "id": "other_path",
                    "type": "wait",
                    "wait_ms": 5,
                },
            },
            {
                "id": "__end__",
                "kind": "end",
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
                "target": "action_it",
                "branch": "true",
            },
            {
                "id": "condition-false",
                "source": "condition_department",
                "target": "action_other",
                "branch": "false",
            },
            {
                "id": "it-end",
                "source": "action_it",
                "target": "__end__",
                "branch": "default",
            },
            {
                "id": "other-end",
                "source": "action_other",
                "target": "__end__",
                "branch": "default",
            },
        ],
    }


def test_native_graph_persists_into_execution_snapshot(
    client,
    users,
    monkeypatch,
):
    jobs = []

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id: None,
            enqueue=lambda *args, **kwargs:
                jobs.append((args, kwargs)),
        ),
    )

    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name": "Native graph app",
            "url": "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    graph = native_condition_graph()

    response = client.post(
        "/api/v1/workflows",
        headers=users["ADMIN"],
        json={
            "name": "Native condition workflow",
            "application_id": application.json()["id"],

            #
            # Deliberadamente conflitante.
            # Quando graph existe, steps NÃO deve ser
            # uma segunda fonte de verdade.
            #
            "steps": [
                {
                    "id": "legacy_should_not_win",
                    "type": "wait",
                    "wait_ms": 5,
                }
            ],
            "graph": graph,
        },
    )

    assert response.status_code == 201, response.text

    workflow = response.json()

    assert sorted(
        step["id"]
        for step in workflow["steps"]
    ) == [
        "it_path",
        "other_path",
    ]

    versions = client.get(
        f"/api/v1/workflows/{workflow['id']}/versions",
        headers=users["ADMIN"],
    )

    assert versions.status_code == 200

    version = versions.json()[0]

    assert version["graph"] is not None

    condition_nodes = [
        node
        for node in version["graph"]["nodes"]
        if node["kind"] == "condition"
    ]

    assert len(condition_nodes) == 1

    assert (
        condition_nodes[0]["expression"]
        == '{{department}} == "IT"'
    )

    condition_edges = [
        edge
        for edge in version["graph"]["edges"]
        if edge["source"] == "condition_department"
    ]

    assert {
        edge["branch"]
        for edge in condition_edges
    } == {
        "true",
        "false",
    }

    execute = client.post(
        f"/api/v1/workflows/{workflow['id']}/execute",
        headers=users["ADMIN"],
        json={
            "input": {
                "department": "IT",
            }
        },
    )

    assert execute.status_code == 202, execute.text
    assert len(jobs) == 1

    with Session() as db:
        execution = db.get(
            Execution,
            execute.json()["id"],
        )

        snapshot_graph = execution.snapshot["graph"]

        assert snapshot_graph is not None

        snapshot_conditions = [
            node
            for node in snapshot_graph["nodes"]
            if node["kind"] == "condition"
        ]

        assert len(snapshot_conditions) == 1

        assert (
            snapshot_conditions[0]["expression"]
            == '{{department}} == "IT"'
        )

        assert {
            edge["branch"]
            for edge in snapshot_graph["edges"]
            if edge["source"] == "condition_department"
        } == {
            "true",
            "false",
        }
