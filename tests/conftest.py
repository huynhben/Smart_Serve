"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from food_tracker.ai import FoodRecognitionEngine
from food_tracker.models import FoodEntry, FoodItem
from food_tracker.storage import FoodLogRepository, NutritionGoalRepository
from food_tracker.tracker import FoodTracker


@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure the application uses a per-test data directory."""
    data_dir = tmp_path / "food_tracker_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FOOD_TRACKER_DATA_DIR", str(data_dir))
    yield


@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage path for testing."""
    storage_dir = tmp_path / "food_tracker"
    storage_dir.mkdir(parents=True)
    return storage_dir / "log.json"


@pytest.fixture
def sample_food_item() -> FoodItem:
    """Create a sample food item for testing."""
    return FoodItem(
        name="Grilled Chicken Breast",
        serving_size="100g",
        calories=165.0,
        macronutrients={"protein": 31.0, "fat": 3.6, "carbs": 0.0},
        aliases=["grilled chicken", "chicken breast"],
    )


@pytest.fixture
def sample_food_entry(sample_food_item: FoodItem) -> FoodEntry:
    """Create a sample food entry for testing."""
    return FoodEntry(
        food=sample_food_item,
        quantity=1.5,
        timestamp=datetime(2024, 1, 15, 12, 30, 0),
    )


@pytest.fixture
def repository(temp_storage_path: Path) -> FoodLogRepository:
    """Create a repository instance with temporary storage."""
    return FoodLogRepository(storage_path=temp_storage_path)


@pytest.fixture
def temp_goal_path(tmp_path: Path) -> Path:
    """Create a temporary path for storing goals."""
    goal_dir = tmp_path / "food_tracker_goals"
    goal_dir.mkdir(parents=True)
    return goal_dir / "goals.json"


@pytest.fixture
def goal_repository(temp_goal_path: Path) -> NutritionGoalRepository:
    """Create a nutrition goal repository for testing."""
    return NutritionGoalRepository(storage_path=temp_goal_path)


@pytest.fixture
def recognition_engine() -> FoodRecognitionEngine:
    """Create a recognition engine instance."""
    return FoodRecognitionEngine()


@pytest.fixture
def tracker(
    recognition_engine: FoodRecognitionEngine,
    repository: FoodLogRepository,
    goal_repository: NutritionGoalRepository,
) -> FoodTracker:
    """Create a tracker instance with test dependencies."""
    return FoodTracker(recogniser=recognition_engine, repository=repository, goal_repository=goal_repository)


@pytest.fixture
def sample_foods_data() -> list[dict]:
    """Sample foods data for testing."""
    return [
        {
            "name": "Grilled Chicken Breast",
            "serving_size": "100g",
            "calories": 165,
            "macronutrients": {"protein": 31, "fat": 3.6, "carbs": 0},
            "aliases": ["grilled chicken", "chicken breast"],
        },
        {
            "name": "Greek Yogurt",
            "serving_size": "170g",
            "calories": 100,
            "macronutrients": {"protein": 17, "carbs": 6, "fat": 0},
            "aliases": ["greek yoghurt", "plain yogurt"],
        },
    ]


@pytest.fixture
def temp_foods_file(tmp_path: Path, sample_foods_data: list[dict]) -> Path:
    """Create a temporary foods.json file for testing."""
    foods_file = tmp_path / "foods.json"
    with foods_file.open("w", encoding="utf8") as f:
        json.dump(sample_foods_data, f)
    return foods_file
