"""Phase 2 integration clients

Revision ID: f2a006
Revises: f2a005
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a006"
down_revision = "f2a005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integration_clients",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "secret_hash",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name",
            name="uq_integration_clients_name",
        ),
    )


def downgrade():
    op.drop_table(
        "integration_clients"
    )
