import os
import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

TEST_ROOT = Path(tempfile.mkdtemp(prefix="rpa-tests-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{TEST_ROOT}/test.db",
    JWT_SECRET="test-only-key-" + "x" * 40,
    ENCRYPTION_KEY=Fernet.generate_key().decode(),
    ARTIFACT_DIR=str(TEST_ROOT / "artifacts"),
    ALLOWED_ORIGINS='["http://127.0.0.1:18081"]',
)
from backend.app.core.database import Base, Session, engine  # noqa: E402
from backend.app.core.security import hasher, token  # noqa: E402
from backend.app.models.entities import User  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def users():
    with Session() as db:
        result = {}
        for role in ["ADMIN", "DEVELOPER", "OPERATOR", "VIEWER"]:
            user = User(
                username=role.lower(), password_hash=hasher.hash("Testing-only-123!"), role=role
            )
            db.add(user)
            db.flush()
            result[role] = {"Authorization": "Bearer " + token(user)}
        db.commit()
        return result


@pytest.fixture
def redis(monkeypatch):
    import fakeredis

    from backend.app.api import auth

    redis = fakeredis.FakeRedis()
    monkeypatch.setattr(auth, "connection", lambda: redis)
    return redis


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as client:
        yield client
