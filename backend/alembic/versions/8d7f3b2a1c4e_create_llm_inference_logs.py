"""create llm inference logs

Revision ID: 8d7f3b2a1c4e
Revises: 30938d936cac
Create Date: 2026-05-26 12:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8d7f3b2a1c4e"
down_revision: Union[str, Sequence[str], None] = "30938d936cac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "llm_inference_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_inference_logs_request_started_at"),
        "llm_inference_logs",
        ["request_started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_inference_logs_status"),
        "llm_inference_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_llm_inference_logs_conversation_id"),
        "llm_inference_logs",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_llm_inference_logs_conversation_id"), table_name="llm_inference_logs")
    op.drop_index(op.f("ix_llm_inference_logs_status"), table_name="llm_inference_logs")
    op.drop_index(op.f("ix_llm_inference_logs_request_started_at"), table_name="llm_inference_logs")
    op.drop_table("llm_inference_logs")
