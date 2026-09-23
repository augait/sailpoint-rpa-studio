from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.core.queue import connection
from backend.app.core.security import current_user, hasher, token
from backend.app.models.entities import User
from backend.app.schemas.contracts import LoginIn
from backend.app.services.audit_service import audit

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login")
def login(body: LoginIn, request: Request, db=Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    try:
        redis = connection()
        key = "login:" + ip
        count = redis.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n",
            1,
            key,
        )
    except Exception:
        raise HTTPException(503, "Autenticação temporariamente indisponível")
    if count > 10:
        raise HTTPException(429, "Muitas tentativas; aguarde um minuto")
    user = db.scalar(select(User).where(User.username == body.username))
    valid = False
    try:
        if user:
            valid = hasher.verify(user.password_hash, body.password)
        else:
            # Perform an equivalent hash to reduce username timing disclosure.
            hasher.hash(body.password)
    except (VerificationError, InvalidHashError):
        pass
    if not valid or not user.active:
        raise HTTPException(401, "Usuário ou senha inválidos")
    audit(db, user.username, "LOGIN", user.id, ip)
    db.commit()
    return {
        "access_token": token(user),
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


@router.get("/me")
def me(user=Depends(current_user)):
    return {"username": user.username, "role": user.role}
