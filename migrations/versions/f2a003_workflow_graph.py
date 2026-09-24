"""Phase 2 workflow graph

Revision ID: f2a003
Revises: f2a002
"""

import sqlalchemy as sa
from alembic import op


revision = "f2a003"
down_revision = "f2a002"
branch_labels = None
depends_on = None


def linear_graph(steps):
    steps = steps or []

    nodes = [
        {
            "id": "__start__",
            "kind": "start",
            "step": None,
            "expression": "",
            "max_iterations": None,
        }
    ]

    for step in steps:
        nodes.append(
            {
                "id": f"node_{step['id']}",
                "kind": "action",
                "step": step,
                "expression": "",
                "max_iterations": None,
            }
        )

    nodes.append(
        {
            "id": "__end__",
            "kind": "end",
            "step": None,
            "expression": "",
            "max_iterations": None,
        }
    )

    node_ids = [
        node["id"]
        for node in nodes
    ]

    edges = []

    for source, target in zip(
        node_ids,
        node_ids[1:],
    ):
        edges.append(
            {
                "id": f"edge_{source}__{target}",
                "source": source,
                "target": target,
                "branch": "default",
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "start_node_id": "__start__",
        "end_node_id": "__end__",
    }


def upgrade():
    op.add_column(
        "workflow_versions",
        sa.Column(
            "graph",
            sa.JSON(),
            nullable=True,
        ),
    )

    bind = op.get_bind()

    versions = sa.table(
        "workflow_versions",
        sa.column("id", sa.String()),
        sa.column("steps", sa.JSON()),
        sa.column("graph", sa.JSON()),
    )

    rows = bind.execute(
        sa.select(
            versions.c.id,
            versions.c.steps,
        )
    ).mappings()

    for row in rows:
        bind.execute(
            versions.update()
            .where(
                versions.c.id == row["id"]
            )
            .values(
                graph=linear_graph(
                    row["steps"]
                )
            )
        )


def downgrade():
    op.drop_column(
        "workflow_versions",
        "graph",
    )
