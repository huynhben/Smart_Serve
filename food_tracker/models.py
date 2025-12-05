"""Domain models for the food tracking application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Dict, Iterable, List


@dataclass
class FoodItem:
    """Represents a known food item in the reference database."""

    name: str
    serving_size: str
    calories: float
    macronutrients: Dict[str, float] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        """Return True when *text* is an explicit alias for the item."""

        text_lower = text.lower().strip()
        aliases = [self.name.lower(), *[alias.lower() for alias in self.aliases]]
        return text_lower in aliases


@dataclass
class FoodEntry:
    """A log entry for the consumption of a food item."""

    food: FoodItem
    quantity: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def calories(self) -> float:
        return self.food.calories * self.quantity

    @property
    def macronutrients(self) -> Dict[str, float]:
        return {
            nutrient: amount * self.quantity
            for nutrient, amount in self.food.macronutrients.items()
        }


@dataclass
class DailyLog:
    """A collection of food entries for a specific day."""

    day: date
    entries: List[FoodEntry] = field(default_factory=list)

    def add_entry(self, entry: FoodEntry) -> None:
        self.entries.append(entry)

    def total_calories(self) -> float:
        return sum(entry.calories for entry in self.entries)

    def total_macros(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for entry in self.entries:
            for nutrient, amount in entry.macronutrients.items():
                totals[nutrient] = totals.get(nutrient, 0.0) + amount
        return totals

    def to_dict(self) -> Dict[str, object]:
        return {
            "day": self.day.isoformat(),
            "entries": [
                {
                    "food": entry.food.name,
                    "quantity": entry.quantity,
                    "timestamp": entry.timestamp.isoformat(),
                    "calories": entry.calories,
                    "macronutrients": entry.macronutrients,
                }
                for entry in self.entries
            ],
            "total_calories": self.total_calories(),
            "total_macronutrients": self.total_macros(),
        }


def group_entries_by_day(entries: Iterable[FoodEntry]) -> Dict[date, DailyLog]:
    grouped: Dict[date, DailyLog] = {}
    for entry in entries:
        entry_day = entry.timestamp.date()
        if entry_day not in grouped:
            grouped[entry_day] = DailyLog(day=entry_day)
        grouped[entry_day].add_entry(entry)
    return grouped
