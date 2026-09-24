"""Phase 2 workflow versions

Revision ID: f2a001
Revises: 562ce4dd5bf6
"""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision = "f2a001"
down_revision = "562ce4dd5bf6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflows",
        sa.Column(
            "current_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_id",
            "version",
            name="uq_workflow_versions_workflow_version",
        ),
    )

    op.create_index(
        "ix_workflow_versions_workflow_id",
        "workflow_versions",
        ["workflow_id"],
        unique=False,
    )

    op.create_index(
        "ix_workflow_versions_status",
        "workflow_versions",
        ["status"],
        unique=False,
    )

    op.add_column(
        "executions",
        sa.Column(
            "workflow_version_id",
            sa.String(length=36),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_executions_workflow_version_id",
        "executions",
        "workflow_versions",
        ["workflow_version_id"],
        ["id"],
    )

    op.create_index(
        "ix_executions_workflow_version_id",
        "executions",
        ["workflow_version_id"],
        unique=False,
    )

    # Converte os workflows já existentes em versões v1 DRAFT.
    bind = op.get_bind()

    workflows = sa.table(
        "workflows",
        sa.column("id", sa.String()),
        sa.column("application_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("operation", sa.String()),
        sa.column("steps", sa.JSON()),
        sa.column("timeout_seconds", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    versions = sa.table(
        "workflow_versions",
        sa.column("id", sa.String()),
        sa.column("workflow_id", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("application_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("operation", sa.String()),
        sa.column("steps", sa.JSON()),
        sa.column("timeout_seconds", sa.Integer()),
        sa.column("created_by", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("published_at", sa.DateTime(timezone=True)),
    )

    existing = bind.execute(
        sa.select(
            workflows.c.id,
            workflows.c.application_id,
            workflows.c.name,
            workflows.c.operation,
            workflows.c.steps,
            workflows.c.timeout_seconds,
            workflows.c.created_at,
        )
    ).mappings()

    for workflow in existing:
        bind.execute(
            versions.insert().values(
                id=str(uuid4()),
                workflow_id=workflow["id"],
                version=1,
                status="DRAFT",
                application_id=workflow["application_id"],
                name=workflow["name"],
                operation=workflow["operation"],
                steps=workflow["steps"],
                timeout_seconds=workflow["timeout_seconds"],
                created_by=None,
                created_at=workflow["created_at"],
                published_at=None,
            )
        )

    op.alter_column(
        "workflows",
        "current_version",
        server_default=None,
    )


def downgrade():
    op.drop_index(
        "ix_executions_workflow_version_id",
        table_name="executions",
    )

    op.drop_constraint(
        "fk_executions_workflow_version_id",
        "executions",
        type_="foreignkey",
    )

    op.drop_column(
        "executions",
        "workflow_version_id",
    )

    op.drop_index(
        "ix_workflow_versions_status",
        table_name="workflow_versions",
    )

    op.drop_index(
        "ix_workflow_versions_workflow_id",
        table_name="workflow_versions",
    )

    op.drop_table("workflow_versions")

    op.drop_column(
        "workflows",
        "current_version",
    )
