"""High level API for the food tracking app."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Dict, Iterable, List, Optional

from .ai import FoodRecognitionEngine, RecognisedFood
from .models import DailyLog, FoodEntry, FoodItem, group_entries_by_day
from .storage import FoodLogRepository

logger = logging.getLogger(__name__)


@dataclass
class FoodTracker:
    """Coordinates food recognition, logging, and reporting."""

    recogniser: FoodRecognitionEngine
    repository: FoodLogRepository = field(default_factory=FoodLogRepository)
    _entries: List[FoodEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize tracker by loading existing entries."""
        if not self._entries:
            try:
                loaded_entries = self.repository.load_entries()
                self._entries.extend(loaded_entries)
                logger.info(f"Loaded {len(loaded_entries)} entries from storage")
            except IOError as e:
                logger.warning(f"Failed to load entries from storage: {e}. Starting with empty log.")
                # Continue with empty entries rather than failing
                self._entries = []

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
        """Register a custom food item with validation."""
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Food name cannot be empty")
        if not serving_size or not serving_size.strip():
            raise ValueError("Serving size cannot be empty")
        if calories < 0:
            raise ValueError(f"Calories cannot be negative, got {calories}")
        if calories > 10000:
            raise ValueError(f"Calories value seems unreasonably high: {calories}")
        
        # Validate macronutrients
        if macronutrients:
            for nutrient, amount in macronutrients.items():
                if amount < 0:
                    raise ValueError(f"Macronutrient '{nutrient}' cannot be negative, got {amount}")
                if amount > 1000:
                    logger.warning(f"Macronutrient '{nutrient}' value seems high: {amount}")
        
        logger.info(f"Registering custom food: {name}")
        item = FoodItem(
            name=name.strip(),
            serving_size=serving_size.strip(),
            calories=calories,
            macronutrients=macronutrients or {},
            aliases=list(aliases or []) if aliases else [],
        )
        self.recogniser.add_custom_item(item)
        logger.info(f"Successfully registered custom food: {name}")
        return item

    # --- Logging ---------------------------------------------------------
    def log_food(self, food_item: FoodItem, quantity: float = 1.0, timestamp: datetime | None = None) -> FoodEntry:
        """Log a food entry with validation."""
        # Validate quantity
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if quantity > 1000:
            raise ValueError(f"Quantity seems unreasonably high: {quantity}")
        
        if timestamp is None:
            timestamp = datetime.now(UTC)
        
        try:
            entry = FoodEntry(food=food_item, quantity=quantity, timestamp=timestamp)
            self._entries.append(entry)
            self.repository.save_entries(self._entries)
            logger.info(f"Logged food: {food_item.name}, quantity: {quantity}")
            return entry
        except IOError as e:
            logger.error(f"Failed to save entry: {e}")
            # Remove entry from memory if save failed
            if entry in self._entries:
                self._entries.remove(entry)
            raise
        except Exception as e:
            logger.error(f"Unexpected error logging food: {e}", exc_info=True)
            raise

    def manual_food_entry(
        self,
        name: str,
        serving_size: str,
        calories: float,
        quantity: float = 1.0,
        macronutrients: Optional[Dict[str, float]] = None,
    ) -> FoodEntry:
        """Create a manual food entry with validation."""
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Food name cannot be empty")
        if not serving_size or not serving_size.strip():
            raise ValueError("Serving size cannot be empty")
        if calories < 0:
            raise ValueError(f"Calories cannot be negative, got {calories}")
        if calories > 10000:
            raise ValueError(f"Calories value seems unreasonably high: {calories}")
        
        # Validate macronutrients
        if macronutrients:
            for nutrient, amount in macronutrients.items():
                if amount < 0:
                    raise ValueError(f"Macronutrient '{nutrient}' cannot be negative, got {amount}")
        
        logger.info(f"Creating manual food entry: {name}")
        item = FoodItem(
            name=name.strip(),
            serving_size=serving_size.strip(),
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
