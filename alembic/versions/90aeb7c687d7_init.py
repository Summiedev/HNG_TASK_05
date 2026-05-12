"""init

Revision ID: 90aeb7c687d7
Revises: 
Create Date: 2026-04-28 17:24:32.638374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '90aeb7c687d7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("document_paths", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("ocr_result", sa.JSON, nullable=True),
        sa.Column("ai_interpretation", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_analyses_id", "id"),
    )


def downgrade() -> None:
    op.drop_table("analyses")
