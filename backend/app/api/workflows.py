from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update

from backend.app.core.database import get_db
from backend.app.core.security import current_user, roles
from backend.app.models.entities import Application, Workflow, utcnow
from backend.app.schemas.contracts import WorkflowIn
from backend.app.services.audit_service import audit

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


@router.get("")
def list_workflows(user=Depends(current_user), db=Depends(get_db)):
    return db.scalars(select(Workflow).order_by(Workflow.updated_at.desc()).limit(500)).all()


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, user=Depends(current_user), db=Depends(get_db)):
    record = db.get(Workflow, workflow_id)
    if not record:
        raise HTTPException(404, "Workflow não encontrado")
    return record


@router.post("", status_code=201)
def create(
    body: WorkflowIn,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    if not db.get(Application, body.application_id):
        raise HTTPException(404, "Aplicação não encontrada")
    record = Workflow(**body.model_dump(exclude={"revision"}))
    db.add(record)
    db.flush()
    audit(db, user.username, "WORKFLOW_CREATED", record.id, request.client.host)
    db.commit()
    return record


@router.put("/{workflow_id}")
def save(
    workflow_id: str,
    body: WorkflowIn,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    if body.revision is None:
        raise HTTPException(422, "Informe revision para evitar sobrescrever outra edição")
    if not db.get(Application, body.application_id):
        raise HTTPException(404, "Aplicação não encontrada")
    changed = db.execute(
        update(Workflow)
        .where(Workflow.id == workflow_id, Workflow.revision == body.revision)
        .values(
            **body.model_dump(exclude={"revision"}), revision=body.revision + 1, updated_at=utcnow()
        )
    )
    if not changed.rowcount:
        db.rollback()
        raise HTTPException(409, "Workflow alterado por outro usuário ou inexistente; recarregue")
    audit(
        db,
        user.username,
        "WORKFLOW_UPDATED",
        workflow_id,
        request.client.host,
        revision=body.revision + 1,
    )
    db.commit()
    return db.get(Workflow, workflow_id)
