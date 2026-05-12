from __future__ import annotations

import logging
import os
import sys
from typing import Any

from celery import Celery
from celery.signals import task_failure, task_prerun, task_success

logger = logging.getLogger(__name__)

BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND: str = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)
TIMEZONE: str = "UTC"
ENABLE_UTC: bool = True
RESULT_EXPIRES: int = 3600
WORKER_PREFETCH_MULTIPLIER: int = 1
WORKER_MAX_TASKS_PER_CHILD: int = 1000


class AnalysisWorkflow:
    STATES = ("uploaded", "queued", "extracting", "interpreting", "saving_results", "completed", "failed")
    QUEUE_NAME = "analysis"
    ROUTING_KEY = "analysis.process"
    TASK_NAME = "app.services.tasks.process_analysis"


celery_app = Celery(
    "clinsights",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=TIMEZONE,
    enable_utc=ENABLE_UTC,
    result_expires=RESULT_EXPIRES,
    worker_prefetch_multiplier=WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=WORKER_MAX_TASKS_PER_CHILD,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_disable_rate_limits=False,
    task_compression="gzip",
    result_compression="gzip",
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
)

celery_app.conf.task_routes = {
    AnalysisWorkflow.TASK_NAME: {"queue": AnalysisWorkflow.QUEUE_NAME, "routing_key": AnalysisWorkflow.ROUTING_KEY}
}

celery_app.conf.queues = {
    AnalysisWorkflow.QUEUE_NAME: {"exchange": AnalysisWorkflow.QUEUE_NAME, "routing_key": AnalysisWorkflow.ROUTING_KEY}
}


@task_prerun.connect
def task_prerun_handler(sender: Any = None, task_id: str | None = None, task: Any = None, **kwargs: Any) -> None:
    try:
        if task and task.name == AnalysisWorkflow.TASK_NAME:
            analysis_id = kwargs.get("args", [])[0] if kwargs.get("args") else None
            if analysis_id:
                logger.info(f"Task {task_id} starting analysis {analysis_id}")
    except Exception as e:
        logger.error(f"Error in task_prerun_handler: {e}", exc_info=True)


@task_success.connect
def task_success_handler(sender: Any = None, result: Any = None, **kwargs: Any) -> None:
    try:
        if sender and sender.name == AnalysisWorkflow.TASK_NAME:
            logger.info(f"Task {sender.request.id} completed successfully")
    except Exception as e:
        logger.error(f"Error in task_success_handler: {e}", exc_info=True)


@task_failure.connect
def task_failure_handler(sender: Any = None, task_id: str | None = None, exception: Exception | None = None, **kwargs: Any) -> None:
    try:
        if sender and sender.name == AnalysisWorkflow.TASK_NAME:
            logger.error(
                f"Task {task_id} failed with exception: {exception}",
                exc_info=kwargs.get("traceback"),
                extra={"task_name": sender.name, "exception_type": type(exception).__name__},
            )
    except Exception as e:
        logger.error(f"Error in task_failure_handler: {e}", exc_info=True)


def get_celery_app() -> Celery:
    return celery_app


__all__ = ["celery_app", "AnalysisWorkflow", "get_celery_app"]
