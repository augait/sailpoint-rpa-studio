"""Phase 2 execution log node ids

Revision ID: f2a004
Revises: f2a003
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a004"
down_revision = "f2a003"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "execution_logs",
        "step_id",
        existing_type=sa.String(length=60),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade():
    bind = op.get_bind()

    too_long = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM execution_logs
            WHERE LENGTH(step_id) > 60
            """
        )
    ).scalar_one()

    if too_long:
        raise RuntimeError(
            "Não é possível voltar step_id para 60 caracteres: "
            "existem logs com IDs maiores"
        )

    op.alter_column(
        "execution_logs",
        "step_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=60),
        existing_nullable=True,
    )
