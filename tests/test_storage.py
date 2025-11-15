"""Tests for the storage module."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from food_tracker.models import FoodEntry, FoodItem, NutritionGoals
from food_tracker.storage import FoodLogRepository, NutritionGoalRepository


class TestFoodLogRepository:
    """Tests for FoodLogRepository."""

    def test_repository_default_path(self, tmp_path, monkeypatch):
        """Test repository uses default path when none provided."""
        # Mock Path.home() to return tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        repo = FoodLogRepository()
        expected_path = tmp_path / ".food_tracker" / "log.json"
        assert repo._storage_path == expected_path
        assert expected_path.parent.exists()

    def test_repository_custom_path(self, temp_storage_path):
        """Test repository with custom storage path."""
        repo = FoodLogRepository(storage_path=temp_storage_path)
        assert repo._storage_path == temp_storage_path
        assert temp_storage_path.parent.exists()

    def test_save_and_load_empty(self, repository):
        """Test saving and loading an empty list."""
        repository.save_entries([])
        assert repository._storage_path.exists()
        entries = repository.load_entries()
        assert entries == []

    def test_save_and_load_single_entry(self, repository, sample_food_entry):
        """Test saving and loading a single entry."""
        repository.save_entries([sample_food_entry])
        loaded = repository.load_entries()
        assert len(loaded) == 1
        assert loaded[0].food.name == sample_food_entry.food.name
        assert loaded[0].quantity == sample_food_entry.quantity
        assert loaded[0].timestamp == sample_food_entry.timestamp

    def test_save_and_load_multiple_entries(self, repository, sample_food_item):
        """Test saving and loading multiple entries."""
        entries = [
            FoodEntry(
                food=sample_food_item,
                quantity=1.0,
                timestamp=datetime(2024, 1, 15, 12, 0, 0),
            ),
            FoodEntry(
                food=sample_food_item,
                quantity=2.0,
                timestamp=datetime(2024, 1, 15, 18, 0, 0),
            ),
        ]
        repository.save_entries(entries)
        loaded = repository.load_entries()
        assert len(loaded) == 2
        assert loaded[0].quantity == 1.0
        assert loaded[1].quantity == 2.0

    def test_load_nonexistent_file(self, repository):
        """Test loading from a file that doesn't exist."""
        # Ensure file doesn't exist
        if repository._storage_path.exists():
            repository._storage_path.unlink()
        entries = repository.load_entries()
        assert entries == []

    def test_save_preserves_all_fields(self, repository, sample_food_item):
        """Test that all fields are preserved when saving and loading."""
        entry = FoodEntry(
            food=FoodItem(
                name="Test Food",
                serving_size="100g",
                calories=200.0,
                macronutrients={"protein": 20.0, "carbs": 30.0},
                aliases=["test", "food"],
            ),
            quantity=1.5,
            timestamp=datetime(2024, 1, 15, 12, 30, 45),
        )
        repository.save_entries([entry])
        loaded = repository.load_entries()
        assert len(loaded) == 1
        loaded_entry = loaded[0]
        assert loaded_entry.food.name == "Test Food"
        assert loaded_entry.food.serving_size == "100g"
        assert loaded_entry.food.calories == 200.0
        assert loaded_entry.food.macronutrients == {"protein": 20.0, "carbs": 30.0}
        assert loaded_entry.food.aliases == ["test", "food"]
        assert loaded_entry.quantity == 1.5
        assert loaded_entry.timestamp == datetime(2024, 1, 15, 12, 30, 45)

    def test_save_handles_missing_optional_fields(self, repository):
        """Test loading entries with missing optional fields."""
        # Create a minimal entry
        entry = FoodEntry(
            food=FoodItem(name="Simple Food", serving_size="1 serving", calories=100.0),
            quantity=1.0,
        )
        repository.save_entries([entry])
        loaded = repository.load_entries()
        assert len(loaded) == 1
        assert loaded[0].food.macronutrients == {}
        assert loaded[0].food.aliases == []

    def test_load_handles_legacy_format(self, repository):
        """Test loading entries from legacy format (missing fields)."""
        # Manually create JSON with missing optional fields
        legacy_data = [
            {
                "food": "Test Food",
                "serving_size": "100g",
                "calories": 200.0,
                "quantity": 1.0,
                "timestamp": "2024-01-15T12:00:00",
            }
        ]
        with repository._storage_path.open("w", encoding="utf8") as f:
            json.dump(legacy_data, f)
        loaded = repository.load_entries()
        assert len(loaded) == 1
        assert loaded[0].food.name == "Test Food"
        assert loaded[0].food.macronutrients == {}
        assert loaded[0].food.aliases == []

    def test_save_overwrites_existing_file(self, repository, sample_food_item):
        """Test that saving overwrites existing entries."""
        entry1 = FoodEntry(food=sample_food_item, quantity=1.0)
        repository.save_entries([entry1])
        assert len(repository.load_entries()) == 1

        entry2 = FoodEntry(food=sample_food_item, quantity=2.0)
        repository.save_entries([entry2])
        loaded = repository.load_entries()
        assert len(loaded) == 1
        assert loaded[0].quantity == 2.0

    def test_json_file_format(self, repository, sample_food_entry):
        """Test that saved JSON file has correct format."""
        repository.save_entries([sample_food_entry])
        with repository._storage_path.open("r", encoding="utf8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert "food" in data[0]
        assert "quantity" in data[0]
        assert "timestamp" in data[0]
        assert data[0]["timestamp"] == sample_food_entry.timestamp.isoformat()


class TestNutritionGoalRepository:
    """Tests for NutritionGoalRepository."""

    def test_default_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        repo = NutritionGoalRepository()
        expected = tmp_path / ".food_tracker" / "goals.json"
        assert repo._storage_path == expected
        assert expected.parent.exists()

    def test_custom_path(self, temp_goal_path):
        repo = NutritionGoalRepository(storage_path=temp_goal_path)
        assert repo._storage_path == temp_goal_path

    def test_load_without_file(self, temp_goal_path):
        repo = NutritionGoalRepository(storage_path=temp_goal_path)
        goals = repo.load_goals()
        assert goals.calories is None
        assert goals.macronutrients == {}

    def test_save_and_load_goals(self, temp_goal_path):
        repo = NutritionGoalRepository(storage_path=temp_goal_path)
        goals = NutritionGoals(calories=2100, macronutrients={"protein": 150})
        repo.save_goals(goals)

        loaded = repo.load_goals()
        assert loaded.calories == 2100
        assert loaded.macronutrients == {"protein": 150}
