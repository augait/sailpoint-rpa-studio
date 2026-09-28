import re

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
)
from pydantic import Field, field_validator
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import roles
from backend.app.models.entities import (
    Application,
    Workflow,
    WorkflowVersion,
)
from backend.app.schemas.contracts import (
    ExecutionIn,
    StrictModel,
)
from backend.app.services.execution_service import (
    create_execution,
)


router = APIRouter(
    prefix="/api/v1/rpa",
    tags=["SailPoint RPA"],
)


class CreateAccountIn(StrictModel):
    application: str = Field(
        min_length=1,
        max_length=120,
    )

    correlationId: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )

    identity: dict[str, str] = Field(
        min_length=1,
        max_length=50,
    )

    @field_validator("identity")
    @classmethod
    def validate_identity(
        cls,
        values,
    ):
        key_pattern = re.compile(
            r"^[A-Za-z_][A-Za-z0-9_]{0,59}$"
        )

        for key, value in values.items():
            if not key_pattern.fullmatch(key):
                raise ValueError(
                    "Nome de atributo inválido"
                )

            if not value:
                raise ValueError(
                    "Atributo não pode ser vazio"
                )

            if len(value) > 10000:
                raise ValueError(
                    "Atributo muito grande"
                )

        return values


def published_workflow(
    db,
    application_id: str,
    operation: str,
):
    versions = db.scalars(
        select(
            WorkflowVersion
        )
        .where(
            WorkflowVersion.application_id
            == application_id,
            WorkflowVersion.operation
            == operation,
            WorkflowVersion.status
            == "PUBLISHED",
        )
        .order_by(
            WorkflowVersion.published_at.desc()
        )
    ).all()

    if not versions:
        raise HTTPException(
            409,
            (
                "Nenhum workflow publicado "
                f"para {operation}"
            ),
        )

    if len(versions) > 1:
        raise HTTPException(
            409,
            (
                "Mais de um workflow publicado "
                f"para {operation}; configuração ambígua"
            ),
        )

    version = versions[0]

    workflow = db.get(
        Workflow,
        version.workflow_id,
    )

    if not workflow:
        raise HTTPException(
            409,
            "Workflow publicado inconsistente",
        )

    return workflow, version


@router.post(
    "/accounts",
    status_code=202,
)
def create_account(
    body: CreateAccountIn,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
    ),
    user=Depends(
        roles(
            "ADMIN",
            "DEVELOPER",
            "OPERATOR",
        )
    ),
    db=Depends(get_db),
):
    if (
        idempotency_key
        and not re.fullmatch(
            r"[A-Za-z0-9_.:-]{1,100}",
            idempotency_key,
        )
    ):
        raise HTTPException(
            422,
            "Idempotency-Key inválida",
        )

    application = db.scalar(
        select(
            Application
        ).where(
            Application.name
            == body.application
        )
    )

    if not application:
        raise HTTPException(
            404,
            "Aplicação não encontrada",
        )

    workflow, version = (
        published_workflow(
            db,
            application.id,
            "CREATE_ACCOUNT",
        )
    )

    if not any(
        step.get(
            "enabled",
            True,
        )
        for step in version.steps
    ):
        raise HTTPException(
            409,
            "Workflow publicado sem etapas habilitadas",
        )

    execution_input = dict(
        body.identity
    )

    record = create_execution(
        db,
        workflow,
        version,
        ExecutionIn(
            input=execution_input,
            correlation_id=
                body.correlationId,
        ),
        user,
        (
            idempotency_key
            or body.correlationId
        ),
        (
            request.client.host
            if request.client
            else ""
        ),
    )

    return {
        "status": "accepted",
        "executionId":
            record.id,
        "correlationId":
            record.correlation_id,
        "workflowId":
            workflow.id,
        "workflowVersion":
            version.version,
    }
