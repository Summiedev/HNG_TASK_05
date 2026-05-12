from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, select, update

from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)

StateType = Literal[
	"uploaded", "queued", "extracting", "interpreting",
	"saving_results", "completed", "failed"
]

VALID_TRANSITIONS = {
	"uploaded": {"queued"},
	"queued": {"extracting", "failed"},
	"extracting": {"interpreting", "failed"},
	"interpreting": {"saving_results", "failed"},
	"saving_results": {"completed", "failed"},
	"completed": set(),
	"failed": set(),
}


async def transition_to(analysis_id: str, target_state: StateType, reason: str | None = None) -> bool:
	async with AsyncSessionLocal() as session:
		try:
			lookup = await session.execute(
				select(Analysis.status).where(Analysis.id == analysis_id)
			)
			current_state = lookup.scalar_one_or_none()

			if current_state is None:
				logger.warning("Analysis %s not found for transition to %s", analysis_id, target_state)
				return False

			if target_state not in VALID_TRANSITIONS.get(current_state, set()):
				logger.error(
					"Invalid transition for analysis %s: %s -> %s",
					analysis_id, current_state, target_state
				)
				return False

			update_values = {"status": target_state}
			if target_state == "failed":
				update_values["failed_at"] = datetime.now(timezone.utc)
				if reason:
					update_values["failure_reason"] = reason
			elif target_state == "completed":
				update_values["completed_at"] = datetime.now(timezone.utc)

			stmt = (
				update(Analysis)
				.where(and_(
					Analysis.id == analysis_id,
					Analysis.status == current_state
				))
				.values(**update_values)
			)
			result = await session.execute(stmt)
			await session.commit()

			if result.rowcount == 0:
				logger.warning(
					"Concurrent transition detected for analysis %s: %s -> %s",
					analysis_id, current_state, target_state
				)
				return False

			logger.info("Transitioned analysis %s: %s -> %s", analysis_id, current_state, target_state)
			return True

		except Exception as exc:
			logger.exception("Failed to transition analysis %s to %s", analysis_id, target_state)
			return False
