import hashlib
import hmac
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.queue import queue
from backend.app.core.security import seal
from backend.app.models.entities import Application, Execution, Workflow, uid, utcnow
from backend.app.services.audit_service import audit


def create_execution(db, workflow: Workflow, request, user, key: str | None, ip: str):
    canonical = json.dumps(
        {"workflow": workflow.id, "input": request.input}, sort_keys=True
    ).encode()
    digest = hmac.new(settings().jwt_secret.encode(), canonical, hashlib.sha256).hexdigest()

    def existing():
        record = db.scalar(select(Execution).where(Execution.idempotency_key == key))
        if record and (record.request_hash != digest or record.created_by != user.id):
            raise HTTPException(409, "Idempotency-Key já usada para outro pedido")
        return record

    if key and (record := existing()):
        return record
    application = db.get(Application, workflow.application_id)
    snapshot = {
        "name": workflow.name,
        "revision": workflow.revision,
        "steps": workflow.steps,
        "timeout_seconds": workflow.timeout_seconds,
        "application": {
            k: getattr(application, k)
            for k in ("id", "name", "url", "browser", "headless", "timeout_ms")
        },
    }
    record = Execution(
        id=uid(),
        workflow_id=workflow.id,
        created_by=user.id,
        correlation_id=request.correlation_id or uid(),
        idempotency_key=key,
        request_hash=digest,
        snapshot=snapshot,
        input_encrypted=seal(request.input),
        status="QUEUED",
    )
    db.add(record)
    audit(db, user.username, "EXECUTION_QUEUED", record.id, ip)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if key and (record := existing()):
            return record
        raise
    try:
        queue().enqueue(
            "worker.tasks.execute",
            record.id,
            job_id=record.id,
            job_timeout=workflow.timeout_seconds + 90,
            result_ttl=3600,
            failure_ttl=86400,
            on_failure="worker.tasks.job_failed",
        )
    except Exception:
        record.status = "FAILED"
        record.error = "QUEUE_UNAVAILABLE"
        record.finished_at = utcnow()
        record.input_encrypted = ""
        audit(db, user.username, "EXECUTION_FAILED", record.id, ip, reason="QUEUE_UNAVAILABLE")
        db.commit()
        raise HTTPException(503, {"message": "Fila indisponível", "execution_id": record.id})
    return record
