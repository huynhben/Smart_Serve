"""FastAPI application exposing the food tracker over HTTP."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, FastAPI, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai import FoodRecognitionEngine
from .models import DailyLog, FoodEntry, FoodItem
from .tracker import FoodTracker
from . import vision


class FoodPayload(BaseModel):
    """Schema representing a food item exchanged with the API."""

    name: str
    serving_size: str
    calories: float = Field(..., ge=0)
    macronutrients: Dict[str, float] = Field(default_factory=dict)
    aliases: List[str] = Field(default_factory=list)


class EntryPayload(BaseModel):
    """Schema describing a request to log a food entry."""

    food: FoodPayload
    quantity: float = Field(1.0, gt=0)
    timestamp: datetime | None = None


class CustomFoodPayload(FoodPayload):
    """Schema for registering a custom food in the recogniser."""

    pass


app = FastAPI(title="Food Tracker", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_tracker() -> FoodTracker:
    """Initialise the tracker with the default recognition engine."""

    recogniser = FoodRecognitionEngine()
    return FoodTracker(recogniser=recogniser)


@app.on_event("startup")
def _startup() -> None:
    app.state.tracker = _build_tracker()


def get_tracker() -> FoodTracker:
    tracker: FoodTracker | None = getattr(app.state, "tracker", None)
    if tracker is None:
        tracker = _build_tracker()
        app.state.tracker = tracker
    return tracker


api_router = APIRouter(prefix="/api")


def _serialise_food(item: FoodItem) -> Dict[str, object]:
    return {
        "name": item.name,
        "serving_size": item.serving_size,
        "calories": item.calories,
        "macronutrients": item.macronutrients,
        "aliases": item.aliases,
    }


def _serialise_entry(entry: FoodEntry) -> Dict[str, object]:
    return {
        "food": _serialise_food(entry.food),
        "quantity": entry.quantity,
        "timestamp": entry.timestamp.isoformat(),
        "calories": entry.calories,
        "macronutrients": entry.macronutrients,
    }


def _serialise_daily_log(log: DailyLog) -> Dict[str, object]:
    return {
        "day": log.day.isoformat(),
        "entries": [_serialise_entry(entry) for entry in log.entries],
        "total_calories": log.total_calories(),
        "total_macronutrients": log.total_macros(),
    }


@api_router.get("/foods/search")
def search_foods(query: str = Query("", min_length=0), tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    if not query.strip():
        return {"items": []}
    results = tracker.scan_description(query)
    items = [
        {
            "food": _serialise_food(result.item),
            "confidence": result.confidence,
        }
        for result in results
    ]
    return {"items": items}


@api_router.get("/foods/library")
def library(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    items = [_serialise_food(item) for item in tracker.recogniser.known_items()]
    return {"items": items}


@api_router.post("/foods", status_code=201)
def register_food(payload: CustomFoodPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    item = tracker.register_custom_food(
        name=payload.name,
        serving_size=payload.serving_size,
        calories=payload.calories,
        macronutrients=payload.macronutrients,
        aliases=payload.aliases,
    )
    return _serialise_food(item)


@api_router.get("/entries")
def list_entries(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    entries = [_serialise_entry(entry) for entry in tracker.entries()]
    return {"items": entries}


@api_router.post("/entries", status_code=201)
def create_entry(payload: EntryPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    food = FoodItem(
        name=payload.food.name,
        serving_size=payload.food.serving_size,
        calories=payload.food.calories,
        macronutrients=payload.food.macronutrients,
        aliases=payload.food.aliases,
    )
    entry = tracker.log_food(food, quantity=payload.quantity, timestamp=payload.timestamp)
    return _serialise_entry(entry)


@api_router.get("/summary")
def summary(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    logs = [_serialise_daily_log(log) for log in tracker.daily_summary()]
    return {"days": logs}


@api_router.post("/scan-image")
async def scan_image(file: UploadFile = File(...)) -> Dict[str, object]:
    """Accept an uploaded image and return candidate food matches."""
    data = await file.read()
    results = vision.match_image_to_foods(data, top_k=5)
    items = []
    for r in results:
        # r['food'] is the raw dict from foods.json
        try:
            food_obj = FoodItem(
                name=r['food'].get('name'),
                serving_size=r['food'].get('serving_size'),
                calories=r['food'].get('calories'),
                macronutrients=r['food'].get('macronutrients', {}),
                aliases=r['food'].get('aliases', []),
            )
        except Exception:
            # fallback: pass through the dict
            food_obj = None

        if food_obj is not None:
            items.append({"food": _serialise_food(food_obj), "confidence": r.get("confidence", 0.0)})
        else:
            items.append({"food": r['food'], "confidence": r.get("confidence", 0.0)})

    return {"items": items}


class EditEntryPayload(BaseModel):
    """Schema for editing an entry."""
    quantity: float = Field(gt=0)

@api_router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int, tracker: FoodTracker = Depends(get_tracker)) -> None:
    """Delete a food entry by its ID."""
    tracker.remove_entry(entry_id)

@api_router.patch("/entries/{entry_id}", status_code=200)
def update_entry(entry_id: int, payload: EditEntryPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Update the quantity of a food entry."""
    entry = tracker.edit_entry(entry_id, payload.quantity)
    return _serialise_entry(entry)

app.include_router(api_router)


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("food_tracker.api:app", host="0.0.0.0", port=8000, reload=True)
