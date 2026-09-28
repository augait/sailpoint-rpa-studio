from backend.app.core.database import Session
from backend.app.models.entities import (
    IntegrationClient,
)


def test_integration_token_is_returned_once(
    client,
    users,
):
    response = client.post(
        "/api/v1/integration-clients",
        headers=users["ADMIN"],
        json={
            "name":
                "isc-service",
        },
    )

    assert response.status_code == 201

    created = response.json()

    assert created["token"].startswith(
        "sprpa_"
    )

    token = created["token"]

    listing = client.get(
        "/api/v1/integration-clients",
        headers=users["ADMIN"],
    )

    assert listing.status_code == 200

    assert token not in listing.text
    assert "secret_hash" not in listing.text

    with Session() as db:
        record = db.get(
            IntegrationClient,
            created["id"],
        )

        assert record is not None
        assert token not in record.secret_hash


def test_rpa_rejects_studio_jwt(
    client,
    users,
):
    response = client.post(
        "/api/v1/rpa/accounts",
        headers=users["OPERATOR"],
        json={
            "application":
                "Does not matter",
            "correlationId":
                "SP-JWT-REJECT",
            "identity": {
                "username":
                    "john.doe",
            },
        },
    )

    assert response.status_code == 401


def test_revoked_integration_token_is_rejected(
    client,
    users,
):
    created = client.post(
        "/api/v1/integration-clients",
        headers=users["ADMIN"],
        json={
            "name":
                "isc-revoked",
        },
    )

    assert created.status_code == 201

    data = created.json()

    headers = {
        "Authorization":
            "Bearer " + data["token"]
    }

    revoked = client.post(
        (
            "/api/v1/integration-clients/"
            f"{data['id']}/revoke"
        ),
        headers=users["ADMIN"],
    )

    assert revoked.status_code == 200
    assert revoked.json()["active"] is False

    response = client.post(
        "/api/v1/rpa/accounts",
        headers=headers,
        json={
            "application":
                "Does not matter",
            "correlationId":
                "SP-REVOKED",
            "identity": {
                "username":
                    "john.doe",
            },
        },
    )

    assert response.status_code == 401
