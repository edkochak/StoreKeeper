"""Add monthly_plans table

Revision ID: 717e4a251af5
Revises:
Create Date: 2025-05-31 11:40:12.191631

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "717e4a251af5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "monthly_plans",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("store_id", sa.Integer, sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("month_year", sa.String, nullable=False),
        sa.Column("plan_amount", sa.Float, nullable=False),
        sa.UniqueConstraint("store_id", "month_year", name="uq_store_month_plan"),
    )

    op.create_index(
        "ix_monthly_plans_store_month", "monthly_plans", ["store_id", "month_year"]
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index("ix_monthly_plans_store_month", "monthly_plans")

    op.drop_table("monthly_plans")
