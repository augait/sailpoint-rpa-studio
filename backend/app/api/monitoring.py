from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from rq import Worker
from sqlalchemy import func, select, text

from backend.app.core.database import get_db
from backend.app.core.queue import connection, queue
from backend.app.core.security import current_user, roles
from backend.app.models.entities import Application, AuditEvent, Execution, Workflow, utcnow

router = APIRouter(tags=["Monitoring"])


@router.get("/health")
def health(db=Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        connection().ping()
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "degraded"}, status_code=503)


@router.get("/health/workers")
def workers(user=Depends(current_user)):
    try:
        rows = Worker.all(connection=connection())
        return [
            {
                "name": w.name,
                "state": w.get_state(),
                "hostname": w.hostname,
                "last_heartbeat": w.last_heartbeat,
                "current_job": w.get_current_job_id(),
                "successful_jobs": w.successful_job_count,
                "failed_jobs": w.failed_job_count,
            }
            for w in rows
        ]
    except Exception:
        return JSONResponse({"detail": "Redis indisponível"}, status_code=503)


@router.get("/api/v1/dashboard")
def dashboard(user=Depends(current_user), db=Depends(get_db)):
    counts = dict(
        db.execute(select(Execution.status, func.count()).group_by(Execution.status)).all()
    )
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        pending, online = queue().count, len(Worker.all(connection=connection()))
    except Exception:
        pending, online = None, None
    return {
        "applications": db.scalar(select(func.count()).select_from(Application)),
        "workflows": db.scalar(select(func.count()).select_from(Workflow)),
        "executions_today": db.scalar(
            select(func.count()).select_from(Execution).where(Execution.created_at >= today)
        ),
        "counts": counts,
        "queue": pending,
        "workers_online": online,
        "average_seconds": db.scalar(select(func.avg(Execution.duration))),
    }


@router.get("/api/v1/audit")
def audit_events(user=Depends(roles("ADMIN")), db=Depends(get_db)):
    return db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(200)).all()


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(user=Depends(roles("ADMIN")), db=Depends(get_db)):
    values = dashboard(user, db)
    return (
        "\n".join(f'rpa_executions{{status="{s}"}} {n}' for s, n in values["counts"].items()) + "\n"
    )
