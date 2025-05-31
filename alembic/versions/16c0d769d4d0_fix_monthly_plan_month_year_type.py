"""fix_monthly_plan_month_year_type

Revision ID: 16c0d769d4d0
Revises: 717e4a251af5
Create Date: 2025-05-31 12:20:28.629948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16c0d769d4d0'
down_revision: Union[str, None] = '717e4a251af5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Изменяем тип поля month_year с VARCHAR на DATE с явным преобразованием
    op.execute("""
        ALTER TABLE monthly_plans 
        ALTER COLUMN month_year TYPE DATE 
        USING month_year::date
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Возвращаем тип обратно к VARCHAR
    op.alter_column('monthly_plans', 'month_year',
                   existing_type=sa.Date(),
                   type_=sa.String(),
                   existing_nullable=False)
