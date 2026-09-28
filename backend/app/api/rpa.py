import re
import time

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
)
from pydantic import Field, field_validator
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.security import (
    integration_actor,
)
from backend.app.models.entities import (
    Application,
    Execution,
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

    correlationId: str | None = Field(
        default=None,
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



class UpdateAccountIn(StrictModel):
    application: str = Field(
        min_length=1,
        max_length=120,
    )

    correlationId: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )

    attributes: dict[str, str] = Field(
        min_length=1,
        max_length=50,
    )

    @field_validator("attributes")
    @classmethod
    def validate_attributes(
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


def wait_for_execution(
    db,
    execution_id: str,
    timeout_seconds: float = 50,
):
    deadline = (
        time.monotonic()
        + timeout_seconds
    )

    terminal = {
        "SUCCESS",
        "FAILED",
        "TIMEOUT",
        "CANCELLED",
    }

    while time.monotonic() < deadline:
        record = db.get(
            Execution,
            execution_id,
        )

        if not record:
            return None

        db.refresh(record)

        if record.status in terminal:
            return record

        time.sleep(0.25)

    return None


@router.get(
    "/accounts",
)
def aggregate_accounts(
    request: Request,
    application: str = Query(
        min_length=1,
        max_length=120,
    ),
    user=Depends(
        integration_actor
    ),
    db=Depends(get_db),
):
    target = db.scalar(
        select(Application).where(
            Application.name
            == application
        )
    )

    if not target:
        raise HTTPException(
            404,
            "Aplicação não encontrada",
        )

    workflow, version = (
        published_workflow(
            db,
            target.id,
            "ACCOUNT_AGGREGATION",
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

    execution = create_execution(
        db,
        workflow,
        version,
        ExecutionIn(
            input={},
        ),
        user,
        None,
        (
            request.client.host
            if request.client
            else ""
        ),
    )

    result = wait_for_execution(
        db,
        execution.id,
    )

    if result is None:
        raise HTTPException(
            504,
            "Timeout aguardando Account Aggregation",
        )

    if result.status != "SUCCESS":
        raise HTTPException(
            502,
            (
                "Account Aggregation falhou: "
                f"{result.status}"
            ),
        )

    accounts = (
        result.output or {}
    ).get(
        "accounts"
    )

    if (
        not isinstance(accounts, list)
        or not all(
            isinstance(item, dict)
            for item in accounts
        )
    ):
        raise HTTPException(
            502,
            "Workflow de agregação retornou formato inválido",
        )

    return accounts


@router.get(
    "/entitlements",
)
def aggregate_entitlements(
    request: Request,
    application: str = Query(
        min_length=1,
        max_length=120,
    ),
    user=Depends(
        integration_actor
    ),
    db=Depends(get_db),
):
    target = db.scalar(
        select(Application).where(
            Application.name
            == application
        )
    )

    if not target:
        raise HTTPException(
            404,
            "Aplicação não encontrada",
        )

    workflow, version = (
        published_workflow(
            db,
            target.id,
            "GROUP_AGGREGATION",
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

    execution = create_execution(
        db,
        workflow,
        version,
        ExecutionIn(
            input={},
        ),
        user,
        None,
        (
            request.client.host
            if request.client
            else ""
        ),
    )

    result = wait_for_execution(
        db,
        execution.id,
    )

    if result is None:
        raise HTTPException(
            504,
            "Timeout aguardando Group Aggregation",
        )

    if result.status != "SUCCESS":
        raise HTTPException(
            502,
            (
                "Group Aggregation falhou: "
                f"{result.status}"
            ),
        )

    entitlements = (
        result.output or {}
    ).get(
        "entitlements"
    )

    if (
        not isinstance(
            entitlements,
            list,
        )
        or not all(
            isinstance(item, dict)
            for item in entitlements
        )
    ):
        raise HTTPException(
            502,
            "Workflow de grupos retornou formato inválido",
        )

    return entitlements


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
        integration_actor
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



@router.post(
    "/accounts/sync",
)
def create_account_sync(
    body: CreateAccountIn,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
    ),
    user=Depends(
        integration_actor
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

    result = wait_for_execution(
        db,
        record.id,
    )

    if result is None:
        raise HTTPException(
            504,
            "Timeout aguardando Create Account",
        )

    if result.status != "SUCCESS":
        raise HTTPException(
            502,
            (
                "Create Account falhou: "
                f"{result.status}"
            ),
        )

    output = (
        result.output
        or {}
    )

    if not isinstance(
        output,
        dict,
    ):
        raise HTTPException(
            502,
            "Workflow de criação retornou formato inválido",
        )

    # Mantemos o adapter genérico.
    #
    # Os atributos enviados pelo ISC são devolvidos,
    # mas valores retornados pelo target/workflow têm
    # precedência caso o sistema normalize algum campo.
    account = {
        **body.identity,
        **output,
    }

    return account


@router.put(
    "/accounts/{username}",
    status_code=202,
)
def update_account(
    username: str,
    body: UpdateAccountIn,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
    ),
    user=Depends(
        integration_actor
    ),
    db=Depends(get_db),
):
    if (
        not username
        or len(username) > 200
    ):
        raise HTTPException(
            422,
            "Identificador de conta inválido",
        )

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
            "UPDATE_ACCOUNT",
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

    execution_input = {
        **body.attributes,

        # O identificador da URL é autoritativo.
        # Um atributo username no body não pode
        # substituir a conta alvo.
        "username":
            username,
    }

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
        "status":
            "accepted",
        "executionId":
            record.id,
        "correlationId":
            record.correlation_id,
        "accountId":
            username,
        "workflowId":
            workflow.id,
        "workflowVersion":
            version.version,
    }



@router.get(
    "/executions/{execution_id}",
)
def execution_status(
    execution_id: str,
    user=Depends(
        integration_actor
    ),
    db=Depends(get_db),
):
    record = db.get(
        Execution,
        execution_id,
    )

    if (
        not record
        or record.integration_client_id
        != user.client_id
    ):
        # Não revela se uma execução
        # pertencente a outro principal existe.
        raise HTTPException(
            404,
            "Execução não encontrada",
        )

    return {
        "executionId":
            record.id,
        "correlationId":
            record.correlation_id,
        "status":
            record.status,
        "output":
            record.output or {},
        "error":
            record.error,
        "startedAt":
            record.started_at,
        "finishedAt":
            record.finished_at,
        "duration":
            record.duration,
    }


@router.get(
    "/test-connection",
)
def test_connection(
    user=Depends(
        integration_actor
    ),
):
    return {
        "status":
            "ok",
        "service":
            "sailpoint-rpa-studio",
        "authenticated":
            True,
    }
