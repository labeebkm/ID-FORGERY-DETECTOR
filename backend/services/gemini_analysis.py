import base64
import json
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import requests
from PIL import Image


@dataclass
class GeminiResult:
    score: float          # 0–1 suspicion score
    verdict: str          # GENUINE / SUSPICIOUS / LIKELY_FORGED
    reasoning: str        # plain-English explanation
    confidence: int       # 0–100
    available: bool       # False if API key missing or call failed


GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

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

    try:
        image_b64 = _pil_to_base64_jpeg(img)

        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                    {"text": FORENSIC_PROMPT},
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,   # low temp for consistent forensic output
                "maxOutputTokens": 512,
            },
        }

        response = requests.post(
            f"{GEMINI_API_URL}?key={api_key}",
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
        )

    except Exception as exc:
        return GeminiResult(
            score=0.0,
            verdict="UNKNOWN",
            reasoning=f"Gemini analysis unavailable: {str(exc)[:120]}",
            confidence=0,
            available=False,
        )
