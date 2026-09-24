import hashlib
import hmac
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.security import seal
from backend.app.models.entities import (
    Application,
    Execution,
    OutboxEvent,
    Workflow,
    WorkflowVersion,
    uid,
)
from backend.app.services.audit_service import audit
from backend.app.services.outbox_service import (
    EXECUTION_ENQUEUE,
    dispatch_event,
)


def create_execution(
    db,
    workflow: Workflow,
    version: WorkflowVersion,
    request,
    user,
    key: str | None,
    ip: str,
):
    canonical = json.dumps(
        {
            "workflow": workflow.id,
            "workflow_version": version.id,
            "input": request.input,
        },
        sort_keys=True,
    ).encode()

    digest = hmac.new(
        settings().jwt_secret.encode(),
        canonical,
        hashlib.sha256,
    ).hexdigest()

    def existing():
        record = db.scalar(
            select(Execution).where(
                Execution.idempotency_key == key
            )
        )

        if record and (
            record.request_hash != digest
            or record.created_by != user.id
        ):
            raise HTTPException(
                409,
                "Idempotency-Key já usada para outro pedido",
            )

        return record

    if key and (record := existing()):
        return record

    application = db.get(
        Application,
        version.application_id,
    )

    if not application:
        raise HTTPException(
            409,
            "Aplicação da versão do workflow não encontrada",
        )

    snapshot = {
        "name": version.name,
        "revision": workflow.revision,
        "version": version.version,
        "version_status": version.status,
        "steps": version.steps,
        "timeout_seconds": version.timeout_seconds,
        "application": {
            k: getattr(application, k)
            for k in (
                "id",
                "name",
                "url",
                "browser",
                "headless",
                "timeout_ms",
            )
        },
    }

    record = Execution(
        id=uid(),
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        created_by=user.id,
        correlation_id=request.correlation_id or uid(),
        idempotency_key=key,
        request_hash=digest,
        snapshot=snapshot,
        input_encrypted=seal(request.input),
        status="QUEUED",
    )

    outbox = OutboxEvent(
        id=uid(),
        event_type=EXECUTION_ENQUEUE,
        aggregate_type="EXECUTION",
        aggregate_id=record.id,
        dedupe_key=f"execution:{record.id}:enqueue",
        payload={
            "execution_id": record.id,
            "job_timeout": version.timeout_seconds + 90,
        },
        status="PENDING",
    )

    #
    # Ponto central do Transactional Outbox:
    #
    # Execution e OutboxEvent entram na MESMA transação.
    #
    db.add(record)
    db.add(outbox)

    audit(
        db,
        user.username,
        "EXECUTION_QUEUED",
        record.id,
        ip,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        version=version.version,
        version_status=version.status,
        outbox_event_id=outbox.id,
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        if key and (record := existing()):
            return record

        raise

    #
    # Depois do COMMIT fazemos uma tentativa imediata.
    #
    # Se Redis estiver indisponível, dispatch_event() marca
    # o Outbox como FAILED, mas a Execution continua QUEUED.
    #
    dispatch_event(outbox.id)

    return record
