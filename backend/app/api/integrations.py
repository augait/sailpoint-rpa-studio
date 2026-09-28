import secrets

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_db
from backend.app.core.security import (
    integration_secret_hash,
    roles,
)
from backend.app.models.entities import (
    IntegrationClient,
    uid,
    utcnow,
)
from backend.app.schemas.contracts import (
    StrictModel,
)
from backend.app.services.audit_service import (
    audit,
)


router = APIRouter(
    prefix="/api/v1/integration-clients",
    tags=["Integration Clients"],
)


class IntegrationClientIn(StrictModel):
    name: str = Field(
        pattern=(
            r"^[A-Za-z]"
            r"[A-Za-z0-9_.-]{2,79}$"
        ),
    )


def public(
    record: IntegrationClient,
):
    return {
        "id": record.id,
        "name": record.name,
        "active": record.active,
        "tokenHint":
            f"sprpa_{record.id}_***",
        "created_at":
            record.created_at,
    }


@router.get("")
def list_clients(
    user=Depends(
        roles("ADMIN"),
    ),
    db=Depends(get_db),
):
    return [
        public(record)
        for record in db.scalars(
            select(
                IntegrationClient
            )
            .order_by(
                IntegrationClient.created_at.desc()
            )
        ).all()
    ]


@router.post(
    "",
    status_code=201,
)
def create_client(
    body: IntegrationClientIn,
    request: Request,
    user=Depends(
        roles("ADMIN"),
    ),
    db=Depends(get_db),
):
    client_id = uid()

    secret = (
        secrets.token_urlsafe(32)
    )

    record = IntegrationClient(
        id=client_id,
        name=body.name,
        secret_hash=
            integration_secret_hash(
                client_id,
                secret,
            ),
        active=True,
        created_by=user.id,
        created_at=utcnow(),
    )

    db.add(record)

    audit(
        db,
        user.username,
        "INTEGRATION_CLIENT_CREATED",
        record.id,
        (
            request.client.host
            if request.client
            else ""
        ),
    )

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            409,
            "Nome de integração já existe",
        ) from exc

    db.refresh(record)

    result = public(record)

    # ÚNICA vez em que o segredo é devolvido.
    result["token"] = (
        f"sprpa_{client_id}_{secret}"
    )

    return result


@router.post(
    "/{client_id}/revoke",
)
def revoke_client(
    client_id: str,
    request: Request,
    user=Depends(
        roles("ADMIN"),
    ),
    db=Depends(get_db),
):
    record = db.get(
        IntegrationClient,
        client_id,
    )

    if not record:
        raise HTTPException(
            404,
            "Cliente de integração não encontrado",
        )

    record.active = False

    audit(
        db,
        user.username,
        "INTEGRATION_CLIENT_REVOKED",
        record.id,
        (
            request.client.host
            if request.client
            else ""
        ),
    )

    db.commit()

    return public(record)
