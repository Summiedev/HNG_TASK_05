"""multi document analysis

Revision ID: b7a9f2d1e4c3
Revises: 90aeb7c687d7
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7a9f2d1e4c3"
down_revision: Union[str, None] = "90aeb7c687d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.add_column(
		"analyses",
		sa.Column("document_paths", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
	)

	op.alter_column("analyses", "document_paths", server_default=None)


def downgrade() -> None:
	op.drop_column("analyses", "document_paths")