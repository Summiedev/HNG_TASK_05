from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis, AnalysisStatus
from app.services.gemini import GeminiError, extract_report
from app.services.state import transition_to

logger = logging.getLogger(__name__)


async def process_analysis_async(analysis_id: str) -> None:
	try:
		if not await transition_to(analysis_id, "queued"):
			return

		async with AsyncSessionLocal() as session:
			lookup = await session.execute(
				select(Analysis.file_path, Analysis.document_paths).where(Analysis.id == analysis_id)
			)
			row = lookup.first()
			if row is None:
				logger.warning("Analysis %s not found after queued transition", analysis_id)
				return

		file_path, document_paths_raw = row
		document_paths = [Path(path) for path in (document_paths_raw or [])] or [Path(file_path)]

		if not await transition_to(analysis_id, "extracting"):
			return

		report = await extract_report(document_paths)

		if not await transition_to(analysis_id, "interpreting"):
			return

		if not await transition_to(analysis_id, "saving_results"):
			return

		async with AsyncSessionLocal() as save_session:
			async with save_session.begin():
				await save_session.execute(
					update(Analysis)
					.where(Analysis.id == analysis_id)
					.values(
						ocr_result=report.ocr_result,
						ai_interpretation=report.ai_interpretation,
					)
				)

		if not await transition_to(analysis_id, "completed"):
			return

		logger.info("Analysis %s completed successfully", analysis_id)

	except GeminiError as exc:
		logger.exception("Gemini failed for analysis %s: %s", analysis_id, exc)
		await transition_to(analysis_id, "failed", str(exc))
	except SQLAlchemyError:
		logger.exception("Database error processing analysis %s", analysis_id)
		await transition_to(analysis_id, "failed", "Database error during processing")
	except Exception as exc:
		logger.exception("Unexpected error processing analysis %s", analysis_id)
		await transition_to(analysis_id, "failed", str(exc))


