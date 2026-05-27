"""add input and output preview to inference logs

Revision ID: f2c9a7e4d1b0
Revises: 8d7f3b2a1c4e
Create Date: 2026-05-27 08:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2c9a7e4d1b0"
down_revision: Union[str, Sequence[str], None] = "c1a8f4d9b2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("llm_inference_logs", sa.Column("input_preview", sa.Text(), nullable=True))
    op.add_column("llm_inference_logs", sa.Column("output_preview", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("llm_inference_logs", "output_preview")
    op.drop_column("llm_inference_logs", "input_preview")
