"""Phase 2 execution integration client ownership

Revision ID: f2a007
Revises: f2a006
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a007"
down_revision = "f2a006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "executions",
        sa.Column(
            "integration_client_id",
            sa.String(length=36),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_executions_integration_client_id",
        "executions",
        "integration_clients",
        ["integration_client_id"],
        ["id"],
    )

    op.create_index(
        "ix_executions_integration_client_id",
        "executions",
        ["integration_client_id"],
    )


def downgrade():
    op.drop_index(
        "ix_executions_integration_client_id",
        table_name="executions",
    )

    op.drop_constraint(
        "fk_executions_integration_client_id",
        "executions",
        type_="foreignkey",
    )

    op.drop_column(
        "executions",
        "integration_client_id",
    )
