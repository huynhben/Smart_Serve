"""FastAPI application exposing the food tracker over HTTP."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .ai import FoodRecognitionEngine
from .models import DailyLog, FoodEntry, FoodItem, UNSET
from .storage import FoodLogRepository, NutritionGoalRepository
from .tracker import FoodTracker


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


class GoalsPayload(BaseModel):
    """Schema representing nutrition goals."""

    calories: float | None = Field(default=None, gt=0)
    macronutrients: Dict[str, float | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_macros(self) -> "GoalsPayload":
        for nutrient, amount in self.macronutrients.items():
            if amount is not None and amount < 0:
                raise ValueError(f"Macro goal for {nutrient} must be non-negative.")
        return self


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
    data_dir = os.environ.get("FOOD_TRACKER_DATA_DIR")
    if data_dir:
        base_path = Path(data_dir).expanduser()
        repository = FoodLogRepository(storage_path=base_path / "log.json")
        goal_repository = NutritionGoalRepository(storage_path=base_path / "goals.json")
    else:
        repository = FoodLogRepository()
        goal_repository = NutritionGoalRepository()
    return FoodTracker(recogniser=recogniser, repository=repository, goal_repository=goal_repository)


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


def _serialise_goals(tracker: FoodTracker) -> Dict[str, object]:
    return tracker.nutrition_goals().as_dict()


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


@api_router.get("/goals")
def get_goals(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    return {"goals": _serialise_goals(tracker)}


@api_router.put("/goals")
def update_goals(payload: GoalsPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    fields_set = getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))
    calories_value = payload.calories if "calories" in fields_set else UNSET
    macronutrient_payload = payload.macronutrients if "macronutrients" in fields_set else None
    updated = tracker.update_goals(calories=calories_value, macronutrients=macronutrient_payload)
    return {"goals": updated.as_dict()}


@api_router.get("/stats")
def stats(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    return {
        "today": tracker.progress_for_day(),
        "weekly": tracker.weekly_overview(),
        "lifetime": tracker.lifetime_stats(),
        "goals": _serialise_goals(tracker),
    }


class EditEntryPayload(BaseModel):
    """Schema for editing an entry."""
    quantity: float = Field(gt=0)

@api_router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int, tracker: FoodTracker = Depends(get_tracker)) -> None:
    """Delete a food entry by its ID."""
    try:
        tracker.remove_entry(entry_id)
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Entry with ID {entry_id} not found")

@api_router.patch("/entries/{entry_id}", status_code=200)
def update_entry(entry_id: int, payload: EditEntryPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Update the quantity of a food entry."""
    try:
        entry = tracker.edit_entry(entry_id, payload.quantity)
        return _serialise_entry(entry)
    except IndexError:
        raise HTTPException(status_code=404, detail=f"Entry with ID {entry_id} not found")

app.include_router(api_router)


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("food_tracker.api:app", host="0.0.0.0", port=8000, reload=True)
