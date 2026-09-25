import asyncio
import socket
from datetime import timezone

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from rq import get_current_job
from sqlalchemy import select, update

from backend.app.core.config import settings
from backend.app.core.database import Session
from backend.app.core.security import unseal
from backend.app.models.entities import (
    ApplicationCredential,
    Execution,
    ExecutionLog,
    utcnow,
)
from backend.app.rpa.engine import Engine, ExecutionCancelled
from backend.app.services.audit_service import audit

TERMINAL = {"SUCCESS", "FAILED", "CANCELLED", "TIMEOUT"}


def load_application_credentials(
    application_id: str,
) -> dict[str, dict[str, str]]:
    with Session() as db:
        records = db.scalars(
            select(
                ApplicationCredential
            )
            .where(
                ApplicationCredential.application_id
                == application_id
            )
            .order_by(
                ApplicationCredential.name
            )
        ).all()

        result = {}

        for record in records:
            values = unseal(
                record.data_encrypted
            )

            if (
                not isinstance(values, dict)
                or not all(
                    isinstance(key, str)
                    and isinstance(value, str)
                    for key, value
                    in values.items()
                )
            ):
                raise ValueError(
                    "CREDENTIAL_PAYLOAD_INVALID"
                )

            result[record.name] = values

        return result


def finish(execution_id: str, status: str, output=None, error=None):
    with Session() as db:
        record = db.get(Execution, execution_id)
        if record is None or record.status in TERMINAL:
            return
        now = utcnow()
        record.status, record.finished_at = status, now
        record.error, record.output = error, output or {}
        record.input_encrypted = (
            ""  # Erase input after processing; snapshots retain only references.
        )
        if record.started_at:
            record.duration = (now - record.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        db.add(ExecutionLog(execution_id=record.id, event="EXECUTION_" + status, details={}))
        audit(db, record.worker or "worker", "EXECUTION_" + status, record.id)
        db.commit()


def execute(execution_id: str):
    job = get_current_job()
    with Session() as db:
        claimed = db.execute(
            update(Execution)
            .where(Execution.id == execution_id, Execution.status == "QUEUED")
            .values(
                status="RUNNING",
                started_at=utcnow(),
                worker=job.worker_name if job else socket.gethostname(),
            )
        )
        db.commit()
        if not claimed.rowcount:
            return
        record = db.get(Execution, execution_id)
        snapshot = record.snapshot
        encrypted = record.input_encrypted

    def emit(event, step_id=None, **details):
        with Session() as db:
            db.add(
                ExecutionLog(
                    execution_id=execution_id, event=event, step_id=step_id, details=details
                )
            )
            db.commit()

    def cancelled():
        with Session() as db:
            return db.get(Execution, execution_id).cancel_requested

    emit("EXECUTION_STARTED")
    try:
        inputs = unseal(encrypted)

        credentials = (
            load_application_credentials(
                snapshot["application"]["id"]
            )
        )

        engine = Engine(
            snapshot,
            inputs,
            settings().artifact_dir
            / execution_id,
            emit,
            cancelled,
            credentials=credentials,
        )

        output = asyncio.run(
            engine.run()
        )
    except ExecutionCancelled:
        finish(execution_id, "CANCELLED")
    except (TimeoutError, PlaywrightTimeoutError):
        finish(execution_id, "TIMEOUT", error="TIMEOUT")
    except Exception as exc:
        finish(execution_id, "FAILED", error=type(exc).__name__)
    else:
        finish(execution_id, "SUCCESS", output=output)


def job_failed(job, connection, exc_type, exc_value, traceback):
    # RQ invokes this on hard timeouts and process failures, too.
    status = "TIMEOUT" if "Timeout" in exc_type.__name__ else "FAILED"
    finish(job.id, status, error=exc_type.__name__)
