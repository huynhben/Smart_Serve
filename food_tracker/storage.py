"""Persistence helpers for the food tracker."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import FoodEntry, FoodItem, NutritionGoals


class FoodLogRepository:
    """Persist food entries to a JSON file on disk."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path.home() / ".food_tracker" / "log.json"
        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_entries(self, entries: Iterable[FoodEntry]) -> None:
        payload: List[dict] = []
        for entry in entries:
            payload.append(
                {
                    "food": entry.food.name,
                    "serving_size": entry.food.serving_size,
                    "calories": entry.food.calories,
                    "macronutrients": entry.food.macronutrients,
                    "aliases": entry.food.aliases,
                    "quantity": entry.quantity,
                    "timestamp": entry.timestamp.isoformat(),
                }
            )
        with self._storage_path.open("w", encoding="utf8") as handle:
            json.dump(payload, handle, indent=2)

    def load_entries(self) -> List[FoodEntry]:
        if not self._storage_path.exists():
            return []
        with self._storage_path.open("r", encoding="utf8") as handle:
            data = json.load(handle)
        entries: List[FoodEntry] = []
        for record in data:
            food = FoodItem(
                name=record["food"],
                serving_size=record.get("serving_size", "1 serving"),
                calories=float(record.get("calories", 0)),
                macronutrients=record.get("macronutrients", {}),
                aliases=record.get("aliases", []),
            )
            timestamp = datetime.fromisoformat(record["timestamp"])
            entries.append(
                FoodEntry(food=food, quantity=float(record.get("quantity", 1.0)), timestamp=timestamp)
            )
        return entries


class NutritionGoalRepository:
    """Persist user nutrition goals separately from log entries."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path.home() / ".food_tracker" / "goals.json"
        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_goals(self, goals: NutritionGoals) -> None:
        payload = goals.as_dict()
        with self._storage_path.open("w", encoding="utf8") as handle:
            json.dump(payload, handle, indent=2)

    def load_goals(self) -> NutritionGoals:
        if not self._storage_path.exists():
            return NutritionGoals()
        with self._storage_path.open("r", encoding="utf8") as handle:
            data = json.load(handle)
        return NutritionGoals.from_dict(data)
