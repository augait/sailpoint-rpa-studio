from types import SimpleNamespace

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
