from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiError(RuntimeError):
	pass


class GeminiTransientError(GeminiError):
	pass


class GeminiExtractionResult(BaseModel):
	ocr_result: dict[str, Any] = Field(default_factory=dict)
	ai_interpretation: dict[str, Any] = Field(default_factory=dict)



def _mime_type_for(path: Path) -> str:
	suffix = path.suffix.lower()
	if suffix == ".pdf":
		return "application/pdf"
	if suffix in {".jpg", ".jpeg"}:
		return "image/jpeg"
	return "image/png"


def _prepare_file_bytes(path: Path) -> tuple[str, bytes]:
	"""Return (mime_type, bytes) for a file path.
	Images larger than configured thresholds will be resized/compressed to
	reduce payload size before base64 encoding. PDFs are returned unchanged.
	"""
	from app.core.config import settings

	if path.suffix.lower() == ".pdf":
		return "application/pdf", path.read_bytes()

	img = Image.open(path)
	img_format = "JPEG"
	max_pixels = settings.GEMINI_MAX_UPLOAD_IMAGE_PIXELS
	# Resize if either dimension exceeds max_pixels
	width, height = img.size
	if max(width, height) > max_pixels:
		ratio = max_pixels / float(max(width, height))
		new_size = (int(width * ratio), int(height * ratio))
		img = img.resize(new_size, Image.LANCZOS)

	out = io.BytesIO()
	# Save as JPEG to reduce size; allow transparency conversion
	if img.mode in ("RGBA", "LA"):
		background = Image.new("RGB", img.size, (255, 255, 255))
		background.paste(img, mask=img.split()[-1])
		img = background

	quality = 85
	img.save(out, format=img_format, quality=quality, optimize=True)
	data = out.getvalue()
	# If still too large, lower quality progressively
	max_bytes = settings.GEMINI_MAX_UPLOAD_IMAGE_BYTES
	while len(data) > max_bytes and quality > 30:
		quality -= 10
		out = io.BytesIO()
		img.save(out, format=img_format, quality=quality, optimize=True)
		data = out.getvalue()

	return "image/jpeg", data



def _extract_text(payload: dict[str, Any]) -> str:
	for candidate in payload.get("candidates", []):
		content = candidate.get("content", {})
		parts = content.get("parts", [])
		texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
		text = "".join(texts).strip()
		if text:
			return text
	raise GeminiError("Gemini returned no textual payload")



def _normalize_json_text(text: str) -> str:
	clean = text.strip()
	if clean.startswith("```"):
		clean = clean.strip("`")
		clean = clean.removeprefix("json").strip()
	start = clean.find("{")
	end = clean.rfind("}")
	if start != -1 and end != -1 and end > start:
		return clean[start : end + 1]
	return clean



def _parse_result(text: str) -> GeminiExtractionResult:
	candidate = _normalize_json_text(text)
	try:
		return GeminiExtractionResult.model_validate_json(candidate)
	except ValidationError as exc:
		raise GeminiError("Gemini response was not valid structured JSON") from exc
	except json.JSONDecodeError as exc:
		raise GeminiError("Gemini response could not be decoded as JSON") from exc


async def extract_report(file_paths: list[Path]) -> GeminiExtractionResult:
	if not file_paths:
		raise GeminiError("At least one document is required")
	if not settings.GEMINI_API_KEY:
		raise GeminiError("GEMINI_API_KEY is not configured")

	for path in file_paths:
		if not path.exists():
			raise FileNotFoundError(path)

	prompt = (
		"You are a medical OCR and lab interpretation engine. "
		"Read the attached lab report documents together and return only valid JSON with this exact structure: "
		"{\"ocr_result\": {\"raw_text\": string, \"extracted_fields\": object}, "
		"\"ai_interpretation\": {\"summary\": string, \"risk_level\": string, \"key_findings\": array, \"next_steps\": array}}. "
		"Do not wrap the JSON in markdown and do not add extra keys."
	)

	parts: list[dict[str, Any]] = [{"text": prompt}]
	for path in file_paths:
		mime, data_bytes = _prepare_file_bytes(path)
		parts.append(
			{
				"inline_data": {
					"mime_type": mime,
					"data": base64.b64encode(data_bytes).decode("utf-8"),
				},
			}
		)

	payload = {
		"contents": [
			{
				"role": "user",
				"parts": parts,
			}
		],
		"generationConfig": {
			"temperature": 0,
			"topP": 0.95,
			"maxOutputTokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
			"responseMimeType": "application/json",
		},
	}

	endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
	async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
		response = await client.post(endpoint, params={"key": settings.GEMINI_API_KEY}, json=payload)
		if response.status_code in {429, 500, 502, 503, 504}:
			raise GeminiTransientError(f"Gemini returned retryable status {response.status_code}")
		try:
			response.raise_for_status()
		except httpx.HTTPStatusError as exc:
			text = None
			try:
				text = response.text
			except Exception:
				text = None
			raise GeminiError(f"Gemini request failed with status {response.status_code}: {text}") from exc

	body = response.json()
	text = _extract_text(body)
	return _parse_result(text)
