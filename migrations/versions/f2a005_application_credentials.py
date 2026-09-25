"""Phase 2 application credentials

Revision ID: f2a005
Revises: f2a004
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a005"
down_revision = "f2a004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "application_credentials",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "data_encrypted",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "field_names",
            sa.JSON(),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
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
            "application_id",
            "name",
            name=(
                "uq_application_credentials_"
                "application_name"
            ),
        ),
    )

    op.create_index(
        "ix_application_credentials_application_id",
        "application_credentials",
        ["application_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_application_credentials_application_id",
        table_name="application_credentials",
    )

    op.drop_table(
        "application_credentials"
    )
