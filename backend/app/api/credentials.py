from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_db
from backend.app.core.security import (
    current_user,
    roles,
    seal,
)
from backend.app.models.entities import (
    Application,
    ApplicationCredential,
    utcnow,
)
from backend.app.schemas.contracts import (
    CredentialIn,
)
from backend.app.services.audit_service import (
    audit,
)


router = APIRouter(
    prefix="/api/v1/applications",
    tags=["Credentials"],
)


def view(
    record: ApplicationCredential,
):
    # IMPORTANTE:
    # data_encrypted nunca é retornado.
    return {
        "id": record.id,
        "application_id":
            record.application_id,
        "name": record.name,
        "description":
            record.description,
        "fields":
            record.field_names,
        "created_at":
            record.created_at,
        "updated_at":
            record.updated_at,
    }


def application_or_404(
    db,
    application_id: str,
):
    application = db.get(
        Application,
        application_id,
    )

    if not application:
        raise HTTPException(
            404,
            "Aplicação não encontrada",
        )

    return application


def credential_or_404(
    db,
    application_id: str,
    credential_id: str,
):
    record = db.scalar(
        select(
            ApplicationCredential
        ).where(
            ApplicationCredential.id
            == credential_id,
            ApplicationCredential.application_id
            == application_id,
        )
    )

    if not record:
        raise HTTPException(
            404,
            "Credencial não encontrada",
        )

    return record


@router.get(
    "/{application_id}/credentials"
)
def list_credentials(
    application_id: str,
    user=Depends(current_user),
    db=Depends(get_db),
):
    application_or_404(
        db,
        application_id,
    )

    rows = db.scalars(
        select(
            ApplicationCredential
        )
        .where(
            ApplicationCredential.application_id
            == application_id
        )
        .order_by(
            ApplicationCredential.created_at.desc()
        )
    ).all()

    return [
        view(record)
        for record in rows
    ]


@router.post(
    "/{application_id}/credentials",
    status_code=201,
)
def create_credential(
    application_id: str,
    body: CredentialIn,
    request: Request,
    user=Depends(
        roles(
            "ADMIN",
            "DEVELOPER",
        )
    ),
    db=Depends(get_db),
):
    application_or_404(
        db,
        application_id,
    )

    record = ApplicationCredential(
        application_id=
            application_id,
        name=
            body.name,
        description=
            body.description,
        data_encrypted=
            seal(body.values),
        field_names=
            sorted(
                body.values.keys()
            ),
        created_by=
            user.id,
    )

    db.add(record)

    try:
        db.flush()

        audit(
            db,
            user.username,
            "CREDENTIAL_CREATED",
            record.id,
            (
                request.client.host
                if request.client
                else ""
            ),
            application_id=
                application_id,
            credential_name=
                record.name,
            fields=
                record.field_names,
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            409,
            (
                "Já existe uma credencial "
                "com este nome nesta aplicação"
            ),
        )

    db.refresh(record)

    return view(record)


@router.put(
    "/{application_id}/credentials/"
    "{credential_id}"
)
def update_credential(
    application_id: str,
    credential_id: str,
    body: CredentialIn,
    request: Request,
    user=Depends(
        roles(
            "ADMIN",
            "DEVELOPER",
        )
    ),
    db=Depends(get_db),
):
    application_or_404(
        db,
        application_id,
    )

    record = credential_or_404(
        db,
        application_id,
        credential_id,
    )

    record.name = body.name
    record.description = (
        body.description
    )

    record.data_encrypted = seal(
        body.values
    )

    record.field_names = sorted(
        body.values.keys()
    )

    record.updated_at = utcnow()

    try:
        audit(
            db,
            user.username,
            "CREDENTIAL_UPDATED",
            record.id,
            (
                request.client.host
                if request.client
                else ""
            ),
            application_id=
                application_id,
            credential_name=
                record.name,
            fields=
                record.field_names,
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            409,
            (
                "Já existe uma credencial "
                "com este nome nesta aplicação"
            ),
        )

    db.refresh(record)

    return view(record)


@router.delete(
    "/{application_id}/credentials/"
    "{credential_id}"
)
def delete_credential(
    application_id: str,
    credential_id: str,
    request: Request,
    user=Depends(
        roles(
            "ADMIN",
            "DEVELOPER",
        )
    ),
    db=Depends(get_db),
):
    application_or_404(
        db,
        application_id,
    )

    record = credential_or_404(
        db,
        application_id,
        credential_id,
    )

    credential_name = record.name

    audit(
        db,
        user.username,
        "CREDENTIAL_DELETED",
        record.id,
        (
            request.client.host
            if request.client
            else ""
        ),
        application_id=
            application_id,
        credential_name=
            credential_name,
    )

    db.delete(record)
    db.commit()

    return {
        "status": "deleted",
    }
