from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from celery import Task
from kombu.exceptions import OperationalError

from celery_app import celery_app
from app.services.gemini import GeminiTransientError

logger = logging.getLogger(__name__)


class AnalysisTask(Task):
	autoretry_for = (OperationalError, httpx.RequestError, httpx.TimeoutException, GeminiTransientError)
	retry_kwargs = {"max_retries": 3}
	retry_backoff = True
	retry_backoff_max = 600
	retry_jitter = True


@celery_app.task(
	base=AnalysisTask,
	bind=True,
	name="app.services.tasks.process_analysis",
	queue="analysis",
	routing_key="analysis.process",
)
def process_analysis(self: Task, analysis_id: str) -> dict[str, Any]:
	from app.services.processor import process_analysis_async
	loop = asyncio.new_event_loop()
	try:
		loop.run_until_complete(process_analysis_async(analysis_id))
	finally:
		loop.close()
	return {"status": "success", "analysis_id": analysis_id}
