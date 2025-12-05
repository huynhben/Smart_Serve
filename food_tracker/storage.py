"""Persistence helpers for the food tracker."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import FoodEntry, FoodItem

logger = logging.getLogger(__name__)


class FoodLogRepository:
    """Persist food entries to a JSON file on disk."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            storage_path = Path.home() / ".food_tracker" / "log.json"
        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_entries(self, entries: Iterable[FoodEntry]) -> None:
        """Save food entries to storage with error handling."""
        try:
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
            
            # Create backup before writing
            if self._storage_path.exists():
                backup_path = self._storage_path.with_suffix(".json.bak")
                try:
                    import shutil
                    shutil.copy2(self._storage_path, backup_path)
                    logger.debug(f"Created backup at {backup_path}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Write to temporary file first, then rename (atomic operation)
            temp_path = self._storage_path.with_suffix(".json.tmp")
            with temp_path.open("w", encoding="utf8") as handle:
                json.dump(payload, handle, indent=2)
            
            # Atomic rename
            temp_path.replace(self._storage_path)
            logger.info(f"Successfully saved {len(payload)} entries to {self._storage_path}")
        except PermissionError as e:
            logger.error(f"Permission denied writing to {self._storage_path}: {e}")
            raise IOError(f"Cannot write to storage file: permission denied") from e
        except OSError as e:
            logger.error(f"OS error writing to {self._storage_path}: {e}")
            raise IOError(f"Failed to write to storage file: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error saving entries: {e}", exc_info=True)
            raise IOError(f"Failed to save entries: {e}") from e

    def load_entries(self) -> List[FoodEntry]:
        """Load food entries from storage with error handling."""
        if not self._storage_path.exists():
            logger.debug(f"Storage file does not exist: {self._storage_path}")
            return []
        
        try:
            with self._storage_path.open("r", encoding="utf8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in storage file {self._storage_path}: {e}")
            # Try to load from backup
            backup_path = self._storage_path.with_suffix(".json.bak")
            if backup_path.exists():
                logger.warning(f"Attempting to load from backup: {backup_path}")
                try:
                    with backup_path.open("r", encoding="utf8") as handle:
                        data = json.load(handle)
                    logger.info("Successfully loaded from backup")
                except Exception as backup_error:
                    logger.error(f"Failed to load from backup: {backup_error}")
                    raise IOError(f"Storage file is corrupted and backup is also invalid: {e}") from e
            else:
                raise IOError(f"Storage file is corrupted (invalid JSON): {e}") from e
        except PermissionError as e:
            logger.error(f"Permission denied reading {self._storage_path}: {e}")
            raise IOError(f"Cannot read storage file: permission denied") from e
        except OSError as e:
            logger.error(f"OS error reading {self._storage_path}: {e}")
            raise IOError(f"Failed to read storage file: {e}") from e
        
        entries: List[FoodEntry] = []
        for idx, record in enumerate(data):
            try:
                # Validate required fields
                if "food" not in record or "timestamp" not in record:
                    logger.warning(f"Skipping invalid record at index {idx}: missing required fields")
                    continue
                
                # Validate calories and quantity are non-negative
                calories = float(record.get("calories", 0))
                quantity = float(record.get("quantity", 1.0))
                if calories < 0:
                    logger.warning(f"Invalid calories value {calories} in record {idx}, setting to 0")
                    calories = 0.0
                if quantity < 0:
                    logger.warning(f"Invalid quantity value {quantity} in record {idx}, setting to 1.0")
                    quantity = 1.0
                
                food = FoodItem(
                    name=record["food"],
                    serving_size=record.get("serving_size", "1 serving"),
                    calories=calories,
                    macronutrients=record.get("macronutrients", {}),
                    aliases=record.get("aliases", []),
                )
                timestamp = datetime.fromisoformat(record["timestamp"])
                entries.append(
                    FoodEntry(food=food, quantity=quantity, timestamp=timestamp)
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid record at index {idx}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(entries)} entries from {self._storage_path}")
        return entries
