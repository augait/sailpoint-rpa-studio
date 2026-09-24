"""Phase 2 transactional outbox

Revision ID: f2a002
Revises: f2a001
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a002"
down_revision = "f2a001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_type", sa.String(length=40), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("dedupe_key", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )

    op.create_index(
        "ix_outbox_events_event_type",
        "outbox_events",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_outbox_events_aggregate_id",
        "outbox_events",
        ["aggregate_id"],
        unique=False,
    )

    op.create_index(
        "ix_outbox_events_status",
        "outbox_events",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_outbox_events_available_at",
        "outbox_events",
        ["available_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_outbox_events_available_at",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_events_status",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_events_aggregate_id",
        table_name="outbox_events",
    )

    op.drop_index(
        "ix_outbox_events_event_type",
        table_name="outbox_events",
    )

    op.drop_table("outbox_events")
