"""Add granular processing states and failure tracking

Revision ID: d7e2c8b9a3f0
Revises: c9d4e1a7b2f8
Create Date: 2026-05-12 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e2c8b9a3f0"
down_revision: Union[str, None] = "c9d4e1a7b2f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.add_column("analyses", sa.Column("failure_reason", sa.String(length=1024), nullable=True))
	op.add_column("analyses", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
	op.drop_column("analyses", "failed_at")
	op.drop_column("analyses", "failure_reason")
