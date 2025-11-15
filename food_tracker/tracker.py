"""High level API for the food tracking app."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

from .ai import FoodRecognitionEngine, RecognisedFood
from .models import DailyLog, FoodEntry, FoodItem, NutritionGoals, group_entries_by_day
from .storage import FoodLogRepository, NutritionGoalRepository


@dataclass
class FoodTracker:
    """Coordinates food recognition, logging, and reporting."""

    recogniser: FoodRecognitionEngine
    repository: FoodLogRepository = field(default_factory=FoodLogRepository)
    goal_repository: NutritionGoalRepository = field(default_factory=NutritionGoalRepository)
    _entries: List[FoodEntry] = field(default_factory=list)
    _goals: NutritionGoals = field(default_factory=NutritionGoals)

    def __post_init__(self) -> None:
        if not self._entries:
            self._entries.extend(self.repository.load_entries())
        self._goals = self.goal_repository.load_goals()

    # --- Recognition -----------------------------------------------------
    def scan_description(self, description: str, top_k: int = 3) -> List[RecognisedFood]:
        return self.recogniser.recognise(description, top_k=top_k)

    def register_custom_food(
        self,
        name: str,
        serving_size: str,
        calories: float,
        macronutrients: Optional[Dict[str, float]] = None,
        aliases: Optional[Iterable[str]] = None,
    ) -> FoodItem:
        item = FoodItem(
            name=name,
            serving_size=serving_size,
            calories=calories,
            macronutrients=macronutrients or {},
            aliases=list(aliases or []),
        )
        self.recogniser.add_custom_item(item)
        return item

    # --- Logging ---------------------------------------------------------
    def log_food(self, food_item: FoodItem, quantity: float = 1.0, timestamp: datetime | None = None) -> FoodEntry:
        if timestamp is None:
            timestamp = datetime.utcnow()
        entry = FoodEntry(food=food_item, quantity=quantity, timestamp=timestamp)
        self._entries.append(entry)
        self.repository.save_entries(self._entries)
        return entry

    def manual_food_entry(
        self,
        name: str,
        serving_size: str,
        calories: float,
        quantity: float = 1.0,
        macronutrients: Optional[Dict[str, float]] = None,
    ) -> FoodEntry:
        item = FoodItem(
            name=name,
            serving_size=serving_size,
            calories=calories,
            macronutrients=macronutrients or {},
        )
        return self.log_food(item, quantity=quantity)

    # --- Reporting -------------------------------------------------------
    def entries(self) -> List[FoodEntry]:
        return list(self._entries)

    def entries_for_day(self, target_day: date) -> DailyLog:
        grouped = group_entries_by_day(self._entries)
        if target_day not in grouped:
            return DailyLog(day=target_day)
        return grouped[target_day]

    def daily_summary(self) -> List[DailyLog]:
        grouped = group_entries_by_day(self._entries)
        return [grouped[day] for day in sorted(grouped)]

    def total_calories(self) -> float:
        return sum(entry.calories for entry in self._entries)

    def total_macros(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for entry in self._entries:
            for nutrient, amount in entry.macronutrients.items():
                totals[nutrient] = totals.get(nutrient, 0.0) + amount
        return totals

    # --- Goal and stats helpers ------------------------------------------
    def nutrition_goals(self) -> NutritionGoals:
        return NutritionGoals(
            calories=self._goals.calories,
            macronutrients=self._goals.cleaned_macros(),
        )

    def update_goals(self, calories: float | None = None, macronutrients: Optional[Dict[str, float]] = None) -> NutritionGoals:
        self._goals = self._goals.merge(calories=calories, macronutrients=macronutrients)
        self.goal_repository.save_goals(self._goals)
        return self.nutrition_goals()

    def progress_for_day(self, target_day: date | None = None) -> Dict[str, object]:
        target_day = target_day or date.today()
        daily_log = self.entries_for_day(target_day)
        consumed_macros = daily_log.total_macros()
        consumed_calories = daily_log.total_calories()
        goals = self.nutrition_goals()
        macro_targets = goals.cleaned_macros()

        def _progress(consumed: float, goal: float | None) -> float | None:
            if goal is None or goal == 0:
                return None
            return consumed / goal

        macro_breakdown: Dict[str, Dict[str, float | None]] = {}
        for nutrient in sorted(set(consumed_macros) | set(macro_targets)):
            consumed_value = consumed_macros.get(nutrient, 0.0)
            goal_value = macro_targets.get(nutrient)
            macro_breakdown[nutrient] = {
                "target": goal_value,
                "consumed": consumed_value,
                "remaining": (goal_value - consumed_value) if goal_value is not None else None,
                "progress": _progress(consumed_value, goal_value),
            }

        return {
            "day": target_day.isoformat(),
            "calories": {
                "target": goals.calories,
                "consumed": consumed_calories,
                "remaining": (goals.calories - consumed_calories) if goals.calories is not None else None,
                "progress": _progress(consumed_calories, goals.calories),
            },
            "macronutrients": macro_breakdown,
        }

    def weekly_overview(self, days: int = 7) -> Dict[str, object]:
        if days <= 0:
            return {"days": [], "average_calories": 0.0, "active_days": 0, "current_streak": self.logging_streak()}

        grouped = group_entries_by_day(self._entries)
        today = date.today()
        start_day = today - timedelta(days=days - 1)
        series: List[Dict[str, object]] = []
        active_calories: List[float] = []

        for offset in range(days):
            day = start_day + timedelta(days=offset)
            log = grouped.get(day, DailyLog(day=day))
            calories = log.total_calories()
            macros = log.total_macros()
            entry_count = len(log.entries)
            if entry_count:
                active_calories.append(calories)
            series.append(
                {
                    "day": day.isoformat(),
                    "calories": calories,
                    "macronutrients": macros,
                    "entry_count": entry_count,
                }
            )

        average_calories = sum(active_calories) / len(active_calories) if active_calories else 0.0
        return {
            "days": series,
            "average_calories": average_calories,
            "active_days": sum(1 for entry in series if entry["entry_count"]),
            "current_streak": self.logging_streak(),
        }

    def logging_streak(self) -> int:
        if not self._entries:
            return 0
        grouped = group_entries_by_day(self._entries)
        streak = 0
        pointer = date.today()
        while True:
            log = grouped.get(pointer)
            if log and log.entries:
                streak += 1
                pointer -= timedelta(days=1)
            else:
                break
        return streak

    def lifetime_stats(self) -> Dict[str, object]:
        if not self._entries:
            return {
                "total_entries": 0,
                "total_calories": 0.0,
                "unique_foods": 0,
                "first_entry": None,
                "most_logged_food": None,
            }

        entries_sorted = sorted(self._entries, key=lambda entry: entry.timestamp)
        counts = Counter(entry.food.name for entry in self._entries)
        most_common = counts.most_common(1)[0]
        return {
            "total_entries": len(self._entries),
            "total_calories": self.total_calories(),
            "unique_foods": len(counts),
            "first_entry": entries_sorted[0].timestamp.isoformat(),
            "most_logged_food": {"name": most_common[0], "count": most_common[1]},
        }

    def remove_entry(self, entry_id: int) -> None:
        """Remove an entry by its index."""
        if 0 <= entry_id < len(self._entries):
            del self._entries[entry_id]
            self.repository.save_entries(self._entries)
        else:
            raise IndexError(f"Entry ID {entry_id} is out of range.")

    def edit_entry(self, entry_id: int, quantity: float) -> FoodEntry:
        """Edit the quantity of an existing entry."""
        if 0 <= entry_id < len(self._entries):
            self._entries[entry_id].quantity = quantity
            self.repository.save_entries(self._entries)
            return self._entries[entry_id]
        else:
            raise IndexError(f"Entry ID {entry_id} is out of range.")
