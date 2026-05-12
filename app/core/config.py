from functools import lru_cache

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=True,
		extra="ignore",
	)

	PROJECT_NAME: str = "Clinsights"
	API_V1_PREFIX: str = "/api/v1"
	DATABASE_URL: PostgresDsn
	REDIS_URL: str
	UPLOAD_DIR: str = "uploads"
	GEMINI_API_KEY: str | None = None
	GEMINI_MODEL: str = "gemini-2.5-flash"
	GEMINI_TIMEOUT_SECONDS: float = 60.0
	GEMINI_MAX_OUTPUT_TOKENS: int = 2048
	# When sending images to Gemini, compress/resize images larger than these
	GEMINI_MAX_UPLOAD_IMAGE_PIXELS: int = 1600
	GEMINI_MAX_UPLOAD_IMAGE_BYTES: int = 900000
	CELERY_TASK_TRACK_STARTED: bool = True
	CELERY_TASK_TIME_LIMIT: int = 3600
	CELERY_TASK_SOFT_TIME_LIMIT: int = 3300
	CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: bool = True
	CELERY_BROKER_CONNECTION_RETRY: bool = True
	CELERY_BROKER_CONNECTION_MAX_RETRIES: int = 10


@lru_cache
def get_settings() -> Settings:
	return Settings()  # type: ignore[call-arg]


settings = get_settings()
