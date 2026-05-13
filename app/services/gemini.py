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
		lines = clean.splitlines()
		if lines and lines[0].startswith("```"):
			lines = lines[1:]
		if lines and lines[-1].strip().startswith("```"):
			lines = lines[:-1]
		clean = "\n".join(lines).strip()
		if clean.lower().startswith("json"):
			clean = clean[4:].strip()

	start = clean.find("{")
	if start == -1:
		return clean

	depth = 0
	in_string = False
	escaped = False
	for index in range(start, len(clean)):
		character = clean[index]
		if in_string:
			if escaped:
				escaped = False
			elif character == "\\":
				escaped = True
			elif character == '"':
				in_string = False
			continue

		if character == '"':
			in_string = True
		elif character == "{":
			depth += 1
		elif character == "}":
			depth -= 1
			if depth == 0:
				return clean[start : index + 1]

	return clean[start:]


def _gemini_response_schema() -> dict[str, Any]:
	return {
		"type": "object",
		"propertyOrdering": ["ocr_result", "ai_interpretation"],
		"properties": {
			"ocr_result": {
				"type": "object",
				"propertyOrdering": ["raw_text", "extracted_fields"],
				"properties": {
					"raw_text": {"type": "string"},
					"extracted_fields": {"type": "object"},
				},
				"required": ["raw_text", "extracted_fields"],
				"additionalProperties": True,
			},
			"ai_interpretation": {
				"type": "object",
				"properties": {
					"summary": {"type": "string"},
					"risk_level": {"type": "string"},
					"key_findings": {"type": "array", "items": {"type": "string"}},
					"next_steps": {"type": "array", "items": {"type": "string"}},
				},
				"required": ["summary", "risk_level", "key_findings", "next_steps"],
				"additionalProperties": True,
			},
		},
		"required": ["ocr_result", "ai_interpretation"],
		"additionalProperties": False,
	}



def _parse_result(text: str) -> GeminiExtractionResult:
	candidate = _normalize_json_text(text)
	try:
		return GeminiExtractionResult.model_validate_json(candidate)
	except ValidationError as exc:
		try:
			return GeminiExtractionResult.model_validate(json.loads(candidate))
		except (json.JSONDecodeError, ValidationError) as inner_exc:
			raise GeminiError("Gemini response was not valid structured JSON") from inner_exc
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
			"responseJsonSchema": _gemini_response_schema(),
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
