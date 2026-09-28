from types import SimpleNamespace

from backend.app.api import rpa as rpa_api
from backend.app.core.database import Session
from backend.app.core.security import unseal
from backend.app.models.entities import Execution
from backend.app.services import (
    outbox_service,
)


def create_published_workflow(
    client,
    headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "name":
                "SailPoint Legacy Test",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    workflow = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name":
                "ISC CREATE_ACCOUNT",
            "application_id":
                application.json()["id"],
            "operation":
                "CREATE_ACCOUNT",
            "steps": [
                {
                    "id":
                        "wait_create",
                    "type":
                        "wait",
                    "wait_ms":
                        5,
                }
            ],
        },
    )

    assert workflow.status_code == 201

    published = client.post(
        (
            "/api/v1/workflows/"
            f"{workflow.json()['id']}"
            "/publish"
        ),
        headers=headers,
    )

    assert published.status_code == 200
    assert (
        published.json()["status"]
        == "PUBLISHED"
    )

    return (
        application.json(),
        workflow.json(),
    )


def test_create_account_requires_published_workflow(
    client,
    users,
    integration_headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name":
                "No published workflow",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    response = client.post(
        "/api/v1/rpa/accounts",
        headers=integration_headers,
        json={
            "application":
                "No published workflow",
            "correlationId":
                "SP-NO-PUBLISHED",
            "identity": {
                "username":
                    "john.doe",
            },
        },
    )

    assert response.status_code == 409


def test_create_account_queues_published_workflow(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    jobs = []

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id: None,
            enqueue=lambda *args, **kwargs:
                jobs.append(
                    (args, kwargs)
                ),
        ),
    )

    _, workflow = (
        create_published_workflow(
            client,
            users["ADMIN"],
        )
    )

    headers = {
        **integration_headers,
        "Idempotency-Key":
            "SP-CREATE-1001",
    }

    payload = {
        "application":
            "SailPoint Legacy Test",
        "correlationId":
            "SP-CREATE-1001",
        "identity": {
            "username":
                "john.doe",
            "firstname":
                "John",
            "lastname":
                "Doe",
            "email":
                "john.doe@test.local",
            "department":
                "IT",
        },
    }

    response = client.post(
        "/api/v1/rpa/accounts",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 202

    result = response.json()

    assert result["status"] == "accepted"

    assert (
        result["correlationId"]
        == "SP-CREATE-1001"
    )

    assert (
        result["workflowId"]
        == workflow["id"]
    )

    assert (
        result["workflowVersion"]
        == 1
    )

    assert len(jobs) == 1

    repeated = client.post(
        "/api/v1/rpa/accounts",
        headers=headers,
        json=payload,
    )

    assert repeated.status_code == 202

    assert (
        repeated.json()["executionId"]
        == result["executionId"]
    )

    assert len(jobs) == 1


def create_published_update_workflow(
    client,
    headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "name":
                "SailPoint Update Test",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    workflow = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name":
                "ISC UPDATE_ACCOUNT",
            "application_id":
                application.json()["id"],
            "operation":
                "UPDATE_ACCOUNT",
            "steps": [
                {
                    "id":
                        "wait_update",
                    "type":
                        "wait",
                    "wait_ms":
                        5,
                }
            ],
        },
    )

    assert workflow.status_code == 201

    published = client.post(
        (
            "/api/v1/workflows/"
            f"{workflow.json()['id']}"
            "/publish"
        ),
        headers=headers,
    )

    assert published.status_code == 200

    return (
        application.json(),
        workflow.json(),
    )


def test_update_account_requires_published_workflow(
    client,
    users,
    integration_headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name":
                "No update workflow",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    response = client.put(
        "/api/v1/rpa/accounts/john.doe",
        headers=integration_headers,
        json={
            "application":
                "No update workflow",
            "correlationId":
                "SP-UPDATE-NONE",
            "attributes": {
                "firstname":
                    "John",
            },
        },
    )

    assert response.status_code == 409


def test_update_account_queues_published_workflow(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    jobs = []

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id:
                None,
            enqueue=lambda *args, **kwargs:
                jobs.append(
                    (args, kwargs)
                ),
        ),
    )

    _, workflow = (
        create_published_update_workflow(
            client,
            users["ADMIN"],
        )
    )

    headers = {
        **integration_headers,
        "Idempotency-Key":
            "SP-UPDATE-1001",
    }

    payload = {
        "application":
            "SailPoint Update Test",
        "correlationId":
            "SP-UPDATE-1001",
        "attributes": {
            "firstname":
                "Jane",
            "lastname":
                "Updated",
            "email":
                "jane.updated@test.local",
            "department":
                "FINANCE",

            # Deve ser ignorado em favor
            # do username da URL.
            "username":
                "wrong.user",
        },
    }

    response = client.put(
        "/api/v1/rpa/accounts/john.doe",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 202

    result = response.json()

    assert (
        result["status"]
        == "accepted"
    )

    assert (
        result["accountId"]
        == "john.doe"
    )

    assert (
        result["workflowId"]
        == workflow["id"]
    )

    assert (
        result["workflowVersion"]
        == 1
    )

    with Session() as db:
        execution = db.get(
            Execution,
            result["executionId"],
        )

        assert execution is not None

        execution_input = unseal(
            execution.input_encrypted
        )

        assert (
            execution_input["username"]
            == "john.doe"
        )

        assert (
            execution_input["firstname"]
            == "Jane"
        )

        assert (
            execution_input["lastname"]
            == "Updated"
        )

        assert (
            execution_input["department"]
            == "FINANCE"
        )

        assert (
            execution_input["username"]
            != "wrong.user"
        )

    assert len(jobs) == 1

    repeated = client.put(
        "/api/v1/rpa/accounts/john.doe",
        headers=headers,
        json=payload,
    )

    assert repeated.status_code == 202

    assert (
        repeated.json()["executionId"]
        == result["executionId"]
    )

    assert len(jobs) == 1


def test_integration_can_read_execution_status(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    jobs = []

    monkeypatch.setattr(
        outbox_service,
        "queue",
        lambda: SimpleNamespace(
            fetch_job=lambda job_id:
                None,
            enqueue=lambda *args, **kwargs:
                jobs.append(
                    (args, kwargs)
                ),
        ),
    )

    create_published_workflow(
        client,
        users["ADMIN"],
    )

    response = client.post(
        "/api/v1/rpa/accounts",
        headers={
            **integration_headers,
            "Idempotency-Key":
                "SP-STATUS-1001",
        },
        json={
            "application":
                "SailPoint Legacy Test",
            "correlationId":
                "SP-STATUS-1001",
            "identity": {
                "username":
                    "status.user",
                "firstname":
                    "Status",
                "lastname":
                    "User",
                "email":
                    "status.user@test.local",
                "department":
                    "IT",
            },
        },
    )

    assert response.status_code == 202

    execution_id = (
        response.json()["executionId"]
    )

    status = client.get(
        (
            "/api/v1/rpa/executions/"
            + execution_id
        ),
        headers=integration_headers,
    )

    assert status.status_code == 200

    result = status.json()

    assert (
        result["executionId"]
        == execution_id
    )

    assert (
        result["correlationId"]
        == "SP-STATUS-1001"
    )

    assert result["status"] == "QUEUED"

    other = client.post(
        "/api/v1/integration-clients",
        headers=users["ADMIN"],
        json={
            "name":
                "status-reader-other",
        },
    )

    assert other.status_code == 201

    other_headers = {
        "Authorization":
            f"Bearer {other.json()['token']}",
    }

    other_status = client.get(
        (
            "/api/v1/rpa/executions/"
            + execution_id
        ),
        headers=other_headers,
    )

    # Uma integração não pode enxergar
    # execuções pertencentes a outra.
    assert other_status.status_code == 404

    # JWT humano não é credencial
    # válida para endpoints RPA.
    human = client.get(
        (
            "/api/v1/rpa/executions/"
            + execution_id
        ),
        headers=users["ADMIN"],
    )

    assert human.status_code == 401


def test_integration_test_connection(
    client,
    users,
    integration_headers,
):
    response = client.get(
        "/api/v1/rpa/test-connection",
        headers=integration_headers,
    )

    assert response.status_code == 200

    assert response.json() == {
        "status":
            "ok",
        "service":
            "sailpoint-rpa-studio",
        "authenticated":
            True,
    }

    human = client.get(
        "/api/v1/rpa/test-connection",
        headers=users["ADMIN"],
    )

    assert human.status_code == 401


def create_published_aggregation_workflow(
    client,
    headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "name":
                "SailPoint Aggregation Test",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    workflow = client.post(
        "/api/v1/workflows",
        headers=headers,
        json={
            "name":
                "ISC ACCOUNT_AGGREGATION",
            "application_id":
                application.json()["id"],
            "operation":
                "ACCOUNT_AGGREGATION",
            "steps": [
                {
                    "id":
                        "wait_aggregation",
                    "type":
                        "wait",
                    "wait_ms":
                        5,
                }
            ],
        },
    )

    assert workflow.status_code == 201

    published = client.post(
        (
            "/api/v1/workflows/"
            f"{workflow.json()['id']}"
            "/publish"
        ),
        headers=headers,
    )

    assert published.status_code == 200

    return application.json()


def test_account_aggregation_returns_accounts(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    create_published_aggregation_workflow(
        client,
        users["ADMIN"],
    )

    monkeypatch.setattr(
        rpa_api,
        "create_execution",
        lambda *args, **kwargs:
            SimpleNamespace(
                id="aggregation-test",
            ),
    )

    accounts = [
        {
            "username":
                "test.user01",
            "firstname":
                "Test01",
            "lastname":
                "User",
            "email":
                "test.user01@test.local",
            "department":
                "IT",
        },
        {
            "username":
                "test.user02",
            "firstname":
                "Test02",
            "lastname":
                "User",
            "email":
                "test.user02@test.local",
            "department":
                "HR",
        },
    ]

    monkeypatch.setattr(
        rpa_api,
        "wait_for_execution",
        lambda *args, **kwargs:
            SimpleNamespace(
                status="SUCCESS",
                output={
                    "accounts":
                        accounts,
                },
            ),
    )

    response = client.get(
        (
            "/api/v1/rpa/accounts"
            "?application="
            "SailPoint%20Aggregation%20Test"
        ),
        headers=integration_headers,
    )

    assert response.status_code == 200
    assert response.json() == accounts


def test_account_aggregation_requires_workflow(
    client,
    users,
    integration_headers,
):
    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name":
                "No aggregation workflow",
            "url":
                "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    response = client.get(
        (
            "/api/v1/rpa/accounts"
            "?application="
            "No%20aggregation%20workflow"
        ),
        headers=integration_headers,
    )

    assert response.status_code == 409



def test_create_account_sync_returns_created_account(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    create_published_workflow(
        client,
        users["ADMIN"],
    )

    captured = {}

    def fake_create_execution(
        db,
        workflow,
        version,
        request,
        user,
        key,
        ip,
    ):
        captured["input"] = request.input
        captured["correlation_id"] = (
            request.correlation_id
        )

        return SimpleNamespace(
            id="sync-create-test",
        )

    monkeypatch.setattr(
        rpa_api,
        "create_execution",
        fake_create_execution,
    )

    monkeypatch.setattr(
        rpa_api,
        "wait_for_execution",
        lambda *args, **kwargs:
            SimpleNamespace(
                status="SUCCESS",
                output={
                    "accountId":
                        "john.doe",
                },
            ),
    )

    response = client.post(
        "/api/v1/rpa/accounts/sync",
        headers=integration_headers,
        json={
            "application":
                "SailPoint Legacy Test",
            "identity": {
                "username":
                    "john.doe",
                "firstname":
                    "John",
                "lastname":
                    "Doe",
                "email":
                    "john.doe@test.local",
                "department":
                    "IT",
            },
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result == {
        "username":
            "john.doe",
        "firstname":
            "John",
        "lastname":
            "Doe",
        "email":
            "john.doe@test.local",
        "department":
            "IT",
        "accountId":
            "john.doe",
    }

    assert captured["input"]["username"] == (
        "john.doe"
    )

    # O ISC não é obrigado a fornecer
    # correlationId.
    assert (
        captured["correlation_id"]
        is None
    )


def test_create_account_sync_propagates_failure(
    client,
    users,
    integration_headers,
    monkeypatch,
):
    create_published_workflow(
        client,
        users["ADMIN"],
    )

    monkeypatch.setattr(
        rpa_api,
        "create_execution",
        lambda *args, **kwargs:
            SimpleNamespace(
                id="sync-create-failed",
            ),
    )

    monkeypatch.setattr(
        rpa_api,
        "wait_for_execution",
        lambda *args, **kwargs:
            SimpleNamespace(
                status="FAILED",
                output={},
            ),
    )

    response = client.post(
        "/api/v1/rpa/accounts/sync",
        headers=integration_headers,
        json={
            "application":
                "SailPoint Legacy Test",
            "identity": {
                "username":
                    "failed.user",
            },
        },
    )

    assert response.status_code == 502

    assert (
        "Create Account falhou"
        in response.json()["detail"]
    )
