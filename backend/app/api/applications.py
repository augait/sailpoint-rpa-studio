from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.core.database import get_db
from backend.app.core.security import check_url, current_user, roles
from backend.app.models.entities import Application
from backend.app.schemas.contracts import ApplicationIn
from backend.app.services.audit_service import audit

router = APIRouter(prefix="/api/v1/applications", tags=["Applications"])


@router.get("")
def list_applications(user=Depends(current_user), db=Depends(get_db)):
    return db.scalars(select(Application).order_by(Application.created_at.desc()).limit(500)).all()


@router.post("", status_code=201)
def create(
    body: ApplicationIn,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    try:
        check_url(body.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    record = Application(**body.model_dump())
    db.add(record)
    try:
        db.flush()
        audit(db, user.username, "APPLICATION_CREATED", record.id, request.client.host)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe uma aplicação com este nome")
    return record
