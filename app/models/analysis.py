from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID as UUIDType, uuid4

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalysisStatus(str, Enum):
	uploaded = "uploaded"
	queued = "queued"
	extracting = "extracting"
	interpreting = "interpreting"
	saving_results = "saving_results"
	completed = "completed"
	failed = "failed"


class Analysis(Base):
	__tablename__ = "analyses"

	id: Mapped[UUIDType] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		default=uuid4,
		index=True,
	)
	status: Mapped[str] = mapped_column(
		String(20),
		default=AnalysisStatus.uploaded.value,
		nullable=False,
		index=True,
	)
	file_path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
	document_paths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
	ocr_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	ai_interpretation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		index=True,
	)
	completed_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True),
		nullable=True,
		index=True,
	)
	failure_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
	failed_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True),
		nullable=True,
	)
