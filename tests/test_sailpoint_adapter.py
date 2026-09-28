from types import SimpleNamespace

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
        headers=users["OPERATOR"],
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
        **users["OPERATOR"],
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
