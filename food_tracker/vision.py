"""Vision helper for extracting foods and macros from images."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Dict, List

from .models import FoodItem

try:
    from openai import OpenAI
    from openai import OpenAIError
except Exception:  # pragma: no cover - dependency may be missing until installed
    OpenAI = None  # type: ignore
    OpenAIError = Exception  # type: ignore


class VisionAIUnavailable(RuntimeError):
    """Raised when image recognition cannot be performed."""


@dataclass
class VisionPrediction:
    """Container for a food prediction returned by the vision model."""

    item: FoodItem
    confidence: float


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if OpenAI is None:
        raise VisionAIUnavailable(
            "The openai package is not installed. Add it to requirements and install dependencies."
        )
    if not api_key:
        raise VisionAIUnavailable("Set OPENAI_API_KEY to enable image-based scanning.")
    return OpenAI(api_key=api_key)


def _macros_from_record(record: Dict[str, object]) -> Dict[str, float]:
    macronutrients = record.get("macronutrients") or {}
    cleaned: Dict[str, float] = {}
    if isinstance(macronutrients, dict):
        for key, value in macronutrients.items():
            try:
                cleaned[key] = float(value)  # type: ignore[arg-type]
            except Exception:
                continue
    return cleaned


def analyse_food_image(image_bytes: bytes, top_k: int = 3, model: str | None = None) -> List[VisionPrediction]:
    """Send an image to an OpenAI vision model and return food predictions."""

    client = _build_client()
    model_name = model or os.environ.get("FOOD_TRACKER_VISION_MODEL", "gpt-4o-mini")
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "You are a nutritionist. Look at the image and identify distinct food items. "
        "For each item, return an estimated serving_size (human readable), calories per serving, "
        "and grams for macronutrients (protein, carbs, fat) if visible. "
        "Respond strictly as JSON with an 'items' array; each item should have "
        "name, serving_size, calories, macronutrients, and confidence between 0 and 1."
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{prompt} Return at most {top_k} items."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                    ],
                }
            ],
        )
    except OpenAIError as exc:  # pragma: no cover - network/credentials errors
        raise VisionAIUnavailable(str(exc)) from exc

    content = response.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VisionAIUnavailable("Vision model returned invalid JSON.") from exc

    raw_items = data.get("items") or []
    if not isinstance(raw_items, list):
        raise VisionAIUnavailable("Vision model response missing items array.")

    predictions: List[VisionPrediction] = []
    for record in raw_items[:top_k]:
        if not isinstance(record, dict):
            continue
        name = str(record.get("name") or "").strip()
        if not name:
            continue
        serving_size = str(record.get("serving_size") or "1 serving")
        try:
            calories = float(record.get("calories", 0.0))
        except Exception:
            calories = 0.0
        confidence_raw = record.get("confidence", 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence_raw)))
        except Exception:
            confidence = 0.5

        item = FoodItem(
            name=name,
            serving_size=serving_size,
            calories=calories,
            macronutrients=_macros_from_record(record),
            aliases=record.get("aliases", []) if isinstance(record.get("aliases"), list) else [],
        )
        predictions.append(VisionPrediction(item=item, confidence=confidence))

    return predictions
