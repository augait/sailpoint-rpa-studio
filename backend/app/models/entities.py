from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def uid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="VIEWER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(String(3), default="DEV")
    browser: Mapped[str] = mapped_column(String(20), default="chromium")
    headless: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=30000)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    operation: Mapped[str] = mapped_column(String(40), default="CUSTOM")
    steps: Mapped[list] = mapped_column(JSON, default=list)

    # revision continua sendo o optimistic locking do editor.
    revision: Mapped[int] = mapped_column(Integer, default=1)

    # version e revision são conceitos diferentes.
    # current_version identifica a versão funcional atual do workflow.
    current_version: Mapped[int] = mapped_column(Integer, default=1)

    timeout_seconds: Mapped[int] = mapped_column(Integer, default=600)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    __table_args__ = (
        UniqueConstraint(
            "workflow_id",
            "version",
            name="uq_workflow_versions_workflow_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id"),
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer)

    # DRAFT -> pode ser editada
    # PUBLISHED -> imutável
    # ARCHIVED -> versão antiga mantida para histórico
    status: Mapped[str] = mapped_column(
        String(20),
        default="DRAFT",
        index=True,
    )

    # Snapshot funcional do workflow.
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id")
    )
    name: Mapped[str] = mapped_column(String(120))
    operation: Mapped[str] = mapped_column(String(40))
    steps: Mapped[list] = mapped_column(JSON, default=list)

    # Contrato de grafo da Fase 2.
    # Temporariamente nullable durante a migração dos workflows sequenciais.
    graph: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    timeout_seconds: Mapped[int] = mapped_column(Integer, default=600)

    # Workflows criados antes da Fase 2 não possuem autor histórico conhecido.
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=uid,
    )

    event_type: Mapped[str] = mapped_column(
        String(60),
        index=True,
    )

    aggregate_type: Mapped[str] = mapped_column(
        String(40),
        default="EXECUTION",
    )

    aggregate_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    # Impede que a mesma mensagem lógica seja criada duas vezes.
    dedupe_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    # PENDING -> aguardando envio
    # SENT    -> entregue ao broker
    # FAILED  -> falhou e aguarda reconciliação/retry
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)

    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id"),
        index=True,
    )

    # NULL para execuções históricas anteriores à Fase 2.
    # Novas execuções serão vinculadas à versão exata executada.
    workflow_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_versions.id"),
        nullable=True,
        index=True,
    )

    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), unique=True
    )
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        index=True,
    )
    snapshot: Mapped[dict] = mapped_column(JSON)
    input_encrypted: Mapped[str] = mapped_column(Text)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    worker: Mapped[str | None] = mapped_column(String(200))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    duration: Mapped[float | None] = mapped_column(Float)


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.id"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
    step_id: Mapped[str | None] = mapped_column(String(100))
    event: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    event: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    ip: Mapped[str] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
    details: Mapped[dict] = mapped_column(JSON, default=dict)
