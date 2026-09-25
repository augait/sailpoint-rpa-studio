from backend.app.core.database import Session
from backend.app.models.entities import (
    ApplicationCredential,
)
from worker.tasks import (
    load_application_credentials,
)


def test_credential_api_and_worker_resolution(
    client,
    users,
):
    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name": "Credential test app",
            "url": "http://127.0.0.1:18081",
        },
    )

    assert application.status_code == 201

    application_id = application.json()["id"]

    secret = "Dummy-Credential-Secret!"

    response = client.post(
        (
            f"/api/v1/applications/"
            f"{application_id}/credentials"
        ),
        headers=users["ADMIN"],
        json={
            "name": "legacy_login",
            "description": "Test",
            "values": {
                "username": "dummy_user",
                "password": secret,
            },
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["fields"] == [
        "password",
        "username",
    ]

    assert "values" not in payload
    assert "data_encrypted" not in payload

    listing = client.get(
        (
            f"/api/v1/applications/"
            f"{application_id}/credentials"
        ),
        headers=users["ADMIN"],
    )

    assert listing.status_code == 200
    assert secret not in listing.text
    assert "dummy_user" not in listing.text

    with Session() as db:
        record = db.get(
            ApplicationCredential,
            payload["id"],
        )

        assert record is not None
        assert secret not in record.data_encrypted
        assert "dummy_user" not in record.data_encrypted

    credentials = (
        load_application_credentials(
            application_id
        )
    )

    assert credentials == {
        "legacy_login": {
            "username": "dummy_user",
            "password": secret,
        }
    }


def test_credential_name_must_be_variable_safe(
    client,
    users,
):
    application = client.post(
        "/api/v1/applications",
        headers=users["ADMIN"],
        json={
            "name": "Credential validation app",
            "url": "http://127.0.0.1:18081",
        },
    )

    application_id = application.json()["id"]

    response = client.post(
        (
            f"/api/v1/applications/"
            f"{application_id}/credentials"
        ),
        headers=users["ADMIN"],
        json={
            "name": "legacy-login",
            "values": {
                "password": "dummy",
            },
        },
    )

    assert response.status_code == 422
