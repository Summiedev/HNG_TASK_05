"""align analysis id to uuid

Revision ID: c9d4e1a7b2f8
Revises: b7a9f2d1e4c3
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c9d4e1a7b2f8"
down_revision: Union[str, None] = "b7a9f2d1e4c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.alter_column(
		"analyses",
		"id",
		existing_type=sa.String(length=36),
		type_=postgresql.UUID(as_uuid=True),
		existing_nullable=False,
		postgresql_using="id::uuid",
	)


def downgrade() -> None:
	op.alter_column(
		"analyses",
		"id",
		existing_type=postgresql.UUID(as_uuid=True),
		type_=sa.String(length=36),
		existing_nullable=False,
		postgresql_using="id::text",
	)