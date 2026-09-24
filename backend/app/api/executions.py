import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import current_user, roles
from backend.app.models.entities import (
    Execution,
    ExecutionLog,
    Workflow,
    WorkflowVersion,
)
from backend.app.schemas.contracts import ExecutionIn
from backend.app.services.audit_service import audit
from backend.app.services.execution_service import create_execution


router = APIRouter(prefix="/api/v1", tags=["Executions"])


def public(record: Execution):
    return {
        key: getattr(record, key)
        for key in (
            "id",
            "workflow_id",
            "workflow_version_id",
            "correlation_id",
            "status",
            "output",
            "error",
            "worker",
            "cancel_requested",
            "created_at",
            "started_at",
            "finished_at",
            "duration",
            "snapshot",
        )
    }


@router.post(
    "/workflows/{workflow_id}/execute",
    status_code=202,
)
def execute(
    workflow_id: str,
    body: ExecutionIn,
    request: Request,
    idempotency_key: str | None = Header(default=None),
    user=Depends(
        roles(
            "ADMIN",
            "DEVELOPER",
            "OPERATOR",
        )
    ),
    db=Depends(get_db),
):
    if idempotency_key and not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,100}",
        idempotency_key,
    ):
        raise HTTPException(
            422,
            "Idempotency-Key inválida",
        )

    workflow = db.get(
        Workflow,
        workflow_id,
    )

    if not workflow:
        raise HTTPException(
            404,
            "Workflow não encontrado",
        )

    version = db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.version == workflow.current_version,
        )
    )

    if not version:
        raise HTTPException(
            409,
            "Workflow sem versão atual válida",
        )

    if not any(
        step.get("enabled", True)
        for step in version.steps
    ):
        raise HTTPException(
            422,
            "Adicione uma etapa habilitada",
        )

    record = create_execution(
        db,
        workflow,
        version,
        body,
        user,
        idempotency_key,
        request.client.host,
    )

    return public(record)


@router.get("/executions")
def list_executions(
    limit: int = 50,
    offset: int = 0,
    user=Depends(current_user),
    db=Depends(get_db),
):
    records = db.scalars(
        select(Execution)
        .order_by(Execution.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .offset(max(0, offset))
    ).all()

    return [
        public(record)
        for record in records
    ]


@router.get("/executions/{execution_id}")
def detail(
    execution_id: str,
    user=Depends(current_user),
    db=Depends(get_db),
):
    record = db.get(
        Execution,
        execution_id,
    )

    if not record:
        raise HTTPException(
            404,
            "Execução não encontrada",
        )

    return public(record)


@router.get("/executions/{execution_id}/logs")
def logs(
    execution_id: str,
    after: int = 0,
    user=Depends(current_user),
    db=Depends(get_db),
):
    return db.scalars(
        select(ExecutionLog)
        .where(
            ExecutionLog.execution_id == execution_id,
            ExecutionLog.id > after,
        )
        .order_by(ExecutionLog.id)
        .limit(500)
    ).all()


@router.post(
    "/executions/{execution_id}/cancel",
    status_code=202,
)
def cancel(
    execution_id: str,
    request: Request,
    user=Depends(
        roles(
            "ADMIN",
            "OPERATOR",
            "DEVELOPER",
        )
    ),
    db=Depends(get_db),
):
    record = db.scalar(
        select(Execution)
        .where(
            Execution.id == execution_id
        )
        .with_for_update()
    )

    if not record:
        raise HTTPException(
            404,
            "Execução não encontrada",
        )

    if record.status not in {
        "QUEUED",
        "RUNNING",
    }:
        raise HTTPException(
            409,
            "Execução já terminou",
        )

    record.cancel_requested = True

    if record.status == "QUEUED":
        from backend.app.models.entities import utcnow

        record.status = "CANCELLED"
        record.finished_at = utcnow()
        record.input_encrypted = ""

    audit(
        db,
        user.username,
        "EXECUTION_CANCEL_REQUESTED",
        record.id,
        request.client.host,
    )

    db.commit()

    return public(record)


@router.get(
    "/executions/{execution_id}/artifacts/{filename}"
)
def artifact(
    execution_id: str,
    filename: str,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if (
        not db.get(
            Execution,
            execution_id,
        )
        or not re.fullmatch(
            r"[A-Za-z0-9_-]+\.png",
            filename,
        )
    ):
        raise HTTPException(404)

    path = (
        settings().artifact_dir
        / execution_id
        / filename
    )

    if not path.is_file():
        raise HTTPException(404)

    return FileResponse(
        path,
        media_type="image/png",
    )
