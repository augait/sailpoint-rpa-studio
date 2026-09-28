import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

import jwt
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.entities import (
    IntegrationClient,
    User,
    utcnow,
)

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
SENSITIVE = re.compile(r"password|passwd|secret|token|authorization|cookie|credential", re.I)


def seal(value: dict) -> str:
    return Fernet(settings().encryption_key.encode()).encrypt(json.dumps(value).encode()).decode()


def unseal(value: str) -> dict:
    return json.loads(Fernet(settings().encryption_key.encode()).decrypt(value.encode()))


def mask(value, secrets: tuple[str, ...] = ()):
    if isinstance(value, dict):
        return {k: "***" if SENSITIVE.search(k) else mask(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [mask(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "***")
    return value


def secret_values(value: dict) -> tuple[str, ...]:
    # All input values are treated as sensitive when constructing diagnostic text.
    def flatten(item):
        if isinstance(item, dict):
            for child in item.values():
                yield from flatten(child)
        elif isinstance(item, list):
            for child in item:
                yield from flatten(child)
        elif isinstance(item, str) and item:
            yield item

    return tuple(flatten(value))


def token(user: User) -> str:
    now = utcnow()
    return jwt.encode(
        {
            "sub": user.id,
            "iat": now,
            "exp": now + timedelta(minutes=settings().jwt_minutes),
            "iss": "rpa-studio",
            "aud": "rpa-studio-api",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def integration_secret_hash(
    client_id: str,
    secret: str,
) -> str:
    return hmac.new(
        settings().jwt_secret.encode(),
        (
            f"integration:"
            f"{client_id}:"
            f"{secret}"
        ).encode(),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True)
class IntegrationActor:
    # Execution.created_by continua apontando
    # para o usuário ADMIN que criou o client.
    id: str
    username: str
    client_id: str


def integration_actor(
    auth: HTTPAuthorizationCredentials
    | None = Depends(bearer),
    db=Depends(get_db),
) -> IntegrationActor:
    try:
        if auth is None:
            raise ValueError()

        value = auth.credentials

        prefix, client_id, secret = (
            value.split("_", 2)
        )

        if (
            prefix != "sprpa"
            or not client_id
            or not secret
        ):
            raise ValueError()

        record = db.scalar(
            select(
                IntegrationClient
            ).where(
                IntegrationClient.id
                == client_id,
                IntegrationClient.active.is_(
                    True
                ),
            )
        )

        if not record:
            raise ValueError()

        expected = (
            integration_secret_hash(
                record.id,
                secret,
            )
        )

        if not hmac.compare_digest(
            expected,
            record.secret_hash,
        ):
            raise ValueError()

        return IntegrationActor(
            id=record.created_by,
            username=(
                f"integration:"
                f"{record.name}"
            ),
            client_id=record.id,
        )

    except ValueError:
        raise HTTPException(
            401,
            "Credencial de integração inválida",
            headers={
                "WWW-Authenticate":
                    "Bearer",
            },
        )


def current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)
) -> User:
    try:
        if auth is None:
            raise ValueError()
        payload = jwt.decode(
            auth.credentials,
            settings().jwt_secret,
            algorithms=["HS256"],
            issuer="rpa-studio",
            audience="rpa-studio-api",
            options={"require": ["exp", "iat", "sub"]},
        )
        user = db.scalar(select(User).where(User.id == payload["sub"], User.active.is_(True)))
        if not user:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Autenticação necessária", headers={"WWW-Authenticate": "Bearer"})


def roles(*allowed: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "Permissão insuficiente")
        return user

    return check


def origin(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("URL deve ser HTTP(S), sem credenciais embutidas")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname.lower()
    return f"{parsed.scheme}://{host}:{port}"


def check_url(url: str) -> str:
    if origin(url) not in {origin(item) for item in settings().allowed_origins}:
        raise ValueError("Destino não permitido em ALLOWED_ORIGINS")
    return url
