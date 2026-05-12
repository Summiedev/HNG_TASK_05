from __future__ import annotations

from celery import Celery
import os
import logging
import ssl

logger = logging.getLogger(__name__)

# Try to import settings, but don't fail import if environment is not configured yet.
try:
    from app.core.config import settings
except Exception:  # pragma: no cover - environment-specific
    settings = None

# Create Celery app without requiring settings at module import time.
celery_app = Celery("celery_app")

if settings:
    # Configure broker/backend and common task settings when settings are available.
    broker_url = getattr(settings, "REDIS_URL", None)
    if broker_url:
        celery_app.conf.broker_url = broker_url
        celery_app.conf.result_backend = broker_url

        # If a secure redis scheme is used (rediss://) provide minimal SSL options
        # so Celery/Redis client won't raise on missing ssl params. For quick local
        # testing we default to CERT_NONE; in production set a stricter policy.
        if str(broker_url).startswith("rediss://"):
            celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
            celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

    celery_app.conf.update(
        task_track_started=getattr(settings, "CELERY_TASK_TRACK_STARTED", True),
        task_time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT", 3600),
        task_soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", 3300),
    )
else:
    logger.debug("`app.core.config.Settings` not available; celery_app created without settings")

# Register local task modules so Celery can discover task definitions.
try:
    import app.services.tasks  # noqa: F401
except Exception:
    # Import errors during task module import should not prevent importing celery_app.
    logger.debug("Failed to import app.services.tasks during celery_app initialization", exc_info=True)

