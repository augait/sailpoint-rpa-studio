from datetime import timedelta

from sqlalchemy import select

from backend.app.core.database import Session
from backend.app.core.queue import queue
from backend.app.models.entities import Execution, OutboxEvent, utcnow


EXECUTION_ENQUEUE = "EXECUTION_ENQUEUE"


def mark_failed(event_id: str, error: str) -> None:
    with Session() as db:
        event = db.get(OutboxEvent, event_id)

        if not event or event.status == "SENT":
            return

        event.status = "FAILED"
        event.attempts += 1
        event.last_error = error[:1000]

        # Backoff simples para o reconciliador.
        delay = min(300, max(5, event.attempts * 10))
        event.available_at = utcnow() + timedelta(seconds=delay)

        db.commit()


def dispatch_event(event_id: str) -> bool:
    try:
        with Session() as db:
            event = db.scalar(
                select(OutboxEvent)
                .where(OutboxEvent.id == event_id)
                .with_for_update()
            )

            if not event:
                return False

            if event.status == "SENT":
                return True

            if event.event_type != EXECUTION_ENQUEUE:
                raise ValueError(
                    f"Tipo de evento não suportado: {event.event_type}"
                )

            execution = db.get(
                Execution,
                event.aggregate_id,
            )

            if not execution:
                raise LookupError("EXECUTION_NOT_FOUND")

            #
            # Se a execução já saiu de QUEUED, não devemos
            # enfileirá-la novamente.
            #
            if execution.status != "QUEUED":
                event.status = "SENT"
                event.processed_at = utcnow()
                event.last_error = None

                db.commit()
                return True

            q = queue()

            #
            # Proteção importante:
            #
            # Redis pode ter recebido o job, mas o processo pode ter
            # caído antes de marcarmos o Outbox como SENT.
            #
            # Nesse caso, não devemos gerar outro job.
            #
            existing_job = q.fetch_job(execution.id)

            if existing_job is None:
                job_timeout = int(
                    event.payload.get(
                        "job_timeout",
                        execution.snapshot.get(
                            "timeout_seconds",
                            600,
                        )
                        + 90,
                    )
                )

                q.enqueue(
                    "worker.tasks.execute",
                    execution.id,
                    job_id=execution.id,
                    job_timeout=job_timeout,
                    result_ttl=3600,
                    failure_ttl=86400,
                    on_failure="worker.tasks.job_failed",
                )

            event.status = "SENT"
            event.attempts += 1
            event.processed_at = utcnow()
            event.last_error = None

            db.commit()

            return True

    except Exception as exc:
        #
        # Usa outra sessão porque a transação anterior pode ter
        # sido invalidada pelo erro.
        #
        try:
            mark_failed(
                event_id,
                type(exc).__name__,
            )
        except Exception:
            pass

        return False


def dispatch_pending(limit: int = 50) -> dict:
    now = utcnow()

    with Session() as db:
        event_ids = db.scalars(
            select(OutboxEvent.id)
            .where(
                OutboxEvent.status.in_(
                    ["PENDING", "FAILED"]
                ),
                OutboxEvent.available_at <= now,
            )
            .order_by(
                OutboxEvent.available_at,
                OutboxEvent.created_at,
            )
            .limit(max(1, min(limit, 500)))
        ).all()

    sent = 0
    failed = 0

    for event_id in event_ids:
        if dispatch_event(event_id):
            sent += 1
        else:
            failed += 1

    return {
        "selected": len(event_ids),
        "sent": sent,
        "failed": failed,
    }
