import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse

import requests
from PIL import Image


@dataclass
class GeminiResult:
    score: float          # 0–1 suspicion score
    verdict: str          # GENUINE / SUSPICIOUS / LIKELY_FORGED
    reasoning: str        # plain-English explanation
    confidence: int       # 0–100
    available: bool       # False if API key missing or call failed
    warnings: list[str] = field(default_factory=list)


DEFAULT_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GEMINI_MODEL_CHECK_TTL_SECONDS = 3600

logger = logging.getLogger(__name__)

_MODEL_CHECK_STATE = {
    "checked_at": 0.0,
    "model": "",
    "base": "",
    "warning": "",
}


def _build_gemini_endpoint() -> str:
    explicit = os.getenv("GEMINI_API_URL", "").strip()
    if explicit:
        return explicit

    api_base = os.getenv("GEMINI_API_BASE", DEFAULT_GEMINI_API_BASE).strip().rstrip("/")
    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()

    if model.startswith("models/"):
        model = model[len("models/"):]
    if model.endswith(":generateContent"):
        model = model[: -len(":generateContent")]

    return f"{api_base}/models/{model}:generateContent"


def _normalize_model_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned.startswith("models/"):
        cleaned = cleaned[len("models/"):]
    return cleaned


def _get_gemini_api_base() -> Optional[str]:
    explicit_base = os.getenv("GEMINI_API_BASE", "").strip()
    if explicit_base:
        return explicit_base.rstrip("/")

    explicit_url = os.getenv("GEMINI_API_URL", "").strip()
    if explicit_url:
        parsed = urlparse(explicit_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        path = parsed.path or ""
        marker = "/v1beta"
        idx = path.find(marker)
        if idx != -1:
            base_path = path[: idx + len(marker)]
        else:
            marker = "/models/"
            idx = path.find(marker)
            base_path = path[:idx] if idx != -1 else ""
        return f"{parsed.scheme}://{parsed.netloc}{base_path}".rstrip("/")

    return DEFAULT_GEMINI_API_BASE


def _model_check_enabled() -> bool:
    flag = os.getenv("GEMINI_MODEL_CHECK", "0").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def _maybe_warn_on_model_availability(api_key: str) -> list[str]:
    if not _model_check_enabled():
        return []

    ttl = int(os.getenv("GEMINI_MODEL_CHECK_TTL_SECONDS", str(DEFAULT_GEMINI_MODEL_CHECK_TTL_SECONDS)))
    now = time.time()
    api_base = _get_gemini_api_base()
    model = _normalize_model_name(os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL))
    if (
        _MODEL_CHECK_STATE["checked_at"]
        and now - _MODEL_CHECK_STATE["checked_at"] < ttl
        and _MODEL_CHECK_STATE["model"] == model
        and _MODEL_CHECK_STATE["base"] == api_base
    ):
        cached = _MODEL_CHECK_STATE.get("warning") or ""
        return [cached] if cached else []

    warning = ""
    if not api_base:
        warning = "Gemini model check skipped: invalid GEMINI_API_BASE or GEMINI_API_URL."
        logger.warning(warning)
        _MODEL_CHECK_STATE["checked_at"] = now
        _MODEL_CHECK_STATE["model"] = model
        _MODEL_CHECK_STATE["base"] = api_base or ""
        _MODEL_CHECK_STATE["warning"] = warning
        return [warning]

    try:
        response = requests.get(
            f"{api_base}/models",
            headers={"x-goog-api-key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        models = data.get("models", [])
        names = [
            _normalize_model_name(m.get("name", ""))
            for m in models
            if isinstance(m, dict)
        ]
        if names and model not in names:
            sample = ", ".join(names[:10])
            suffix = "..." if len(names) > 10 else ""
            warning = (
                f"Gemini model '{model}' not present in {api_base}/models. "
                f"Set GEMINI_MODEL to one of: {sample}{suffix}"
            )
            logger.warning(warning)
        elif not names:
            warning = (
                f"Gemini model check returned no models from {api_base}/models; "
                f"cannot verify '{model}'."
            )
            logger.warning(warning)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status in {401, 403}:
            logger.warning(
                "Gemini model check skipped: HTTP %s from %s/models (permission denied).",
                status,
                api_base,
            )
            warning = ""
        else:
            warning = f"Gemini model check failed: HTTP {status} from {api_base}/models."
            logger.warning(warning)
    except Exception as exc:
        warning = f"Gemini model check failed: {str(exc)[:200]}"
        logger.warning(warning)
    finally:
        _MODEL_CHECK_STATE["checked_at"] = now
        _MODEL_CHECK_STATE["model"] = model
        _MODEL_CHECK_STATE["base"] = api_base
        _MODEL_CHECK_STATE["warning"] = warning

    return [warning] if warning else []

FORENSIC_PROMPT = """You are a forensic document examiner specializing in ID document authentication.

Analyze this ID document image carefully and respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON.

{
  "verdict": "GENUINE" or "SUSPICIOUS" or "LIKELY_FORGED",
  "suspicion_score": <number 0.0 to 1.0>,
  "confidence": <integer 0 to 100>,
  "reasoning": "<2-3 sentence plain English explanation of your finding>",
  "flags": ["<specific observation 1>", "<specific observation 2>"]
}

Examine these aspects:
- Document type and overall structure
- Font consistency and typography
- Photo integration (does the photo look naturally embedded?)
- Text alignment and field positioning
- Any visible signs of digital editing or compositing
- Color and lighting consistency
- Security feature indicators (holograms, watermarks if visible)

Be specific. If the image looks like a genuine document, say so clearly.
If something looks tampered, describe exactly what looks wrong."""


def _pil_to_base64_jpeg(img: Image.Image) -> str:
    """Convert PIL image to base64 JPEG string for Gemini API."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def run_gemini_analysis(img: Image.Image) -> GeminiResult:
    """
    Send the ID image to Gemini Vision for semantic forensic analysis.

    This acts as a 6th forensic signal that understands document structure,
    font consistency, and visual anomalies that classical CV cannot detect.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        return GeminiResult(
            score=0.0,
            verdict="UNKNOWN",
            reasoning="Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
            confidence=0,
            available=False,
        )

    warnings: list[str] = []
    try:
        image_b64 = _pil_to_base64_jpeg(img)
        endpoint = _build_gemini_endpoint()
        warnings = _maybe_warn_on_model_availability(api_key)

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": FORENSIC_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,   # low temp for consistent forensic output
                "maxOutputTokens": 512,
            },
        }

        response = requests.post(
            endpoint,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        raw_text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        # Strip accidental markdown fences
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        parsed = json.loads(clean)

        return GeminiResult(
            score=float(parsed.get("suspicion_score", 0.5)),
            verdict=parsed.get("verdict", "SUSPICIOUS"),
            reasoning=parsed.get("reasoning", ""),
            confidence=int(parsed.get("confidence", 50)),
            available=True,
            warnings=warnings,
        )

    except requests.HTTPError as exc:
        status = None
        detail = ""
        if exc.response is not None:
            status = exc.response.status_code
            try:
                detail = exc.response.json().get("error", {}).get("message", "")
            except ValueError:
                detail = exc.response.text or ""
        status_text = str(status) if status is not None else "unknown"
        detail = detail.replace("\n", " ").strip()[:200]
        message = f"Gemini analysis unavailable: HTTP {status_text}."
        if detail:
            message = f"{message} {detail}"
        return GeminiResult(
            score=0.0,
            verdict="UNKNOWN",
            reasoning=message,
            confidence=0,
            available=False,
            warnings=warnings,
        )
    except Exception as exc:
        return GeminiResult(
            score=0.0,
            verdict="UNKNOWN",
            reasoning=f"Gemini analysis unavailable: {str(exc)[:200]}",
            confidence=0,
            available=False,
            warnings=warnings,
        )
