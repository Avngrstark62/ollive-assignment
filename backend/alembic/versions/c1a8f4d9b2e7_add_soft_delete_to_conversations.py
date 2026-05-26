"""add soft delete to conversations

Revision ID: c1a8f4d9b2e7
Revises: 8d7f3b2a1c4e
Create Date: 2026-05-26 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a8f4d9b2e7"
down_revision: Union[str, Sequence[str], None] = "8d7f3b2a1c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("conversations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_conversations_deleted_at"), "conversations", ["deleted_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_conversations_deleted_at"), table_name="conversations")
    op.drop_column("conversations", "deleted_at")
