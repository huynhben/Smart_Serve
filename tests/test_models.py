"""Tests for the models module."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from food_tracker.models import DailyLog, FoodEntry, FoodItem, NutritionGoals, group_entries_by_day


class TestFoodItem:
    """Tests for FoodItem model."""

    def test_food_item_creation(self):
        """Test creating a FoodItem with all fields."""
        item = FoodItem(
            name="Test Food",
            serving_size="100g",
            calories=200.0,
            macronutrients={"protein": 20.0, "carbs": 30.0, "fat": 10.0},
            aliases=["test", "food"],
        )
        assert item.name == "Test Food"
        assert item.serving_size == "100g"
        assert item.calories == 200.0
        assert item.macronutrients == {"protein": 20.0, "carbs": 30.0, "fat": 10.0}
        assert item.aliases == ["test", "food"]

    def test_food_item_defaults(self):
        """Test FoodItem with default values."""
        item = FoodItem(name="Test", serving_size="1 serving", calories=100.0)
        assert item.macronutrients == {}
        assert item.aliases == []

    def test_food_item_matches_exact_name(self):
        """Test matching by exact name."""
        item = FoodItem(name="Chicken Breast", serving_size="100g", calories=165.0)
        assert item.matches("Chicken Breast")
        assert item.matches("chicken breast")  # Case insensitive
        assert item.matches("  chicken breast  ")  # Whitespace trimmed

    def test_food_item_matches_alias(self):
        """Test matching by alias."""
        item = FoodItem(
            name="Chicken Breast",
            serving_size="100g",
            calories=165.0,
            aliases=["grilled chicken", "chicken"],
        )
        assert item.matches("grilled chicken")
        assert item.matches("Grilled Chicken")  # Case insensitive
        assert item.matches("chicken")

    def test_food_item_no_match(self):
        """Test that non-matching text returns False."""
        item = FoodItem(name="Chicken Breast", serving_size="100g", calories=165.0)
        assert not item.matches("Beef Steak")
        assert not item.matches("chicken soup")  # Partial match doesn't count


class TestFoodEntry:
    """Tests for FoodEntry model."""

    def test_food_entry_creation(self, sample_food_item):
        """Test creating a FoodEntry."""
        entry = FoodEntry(food=sample_food_item, quantity=1.5)
        assert entry.food == sample_food_item
        assert entry.quantity == 1.5
        assert isinstance(entry.timestamp, datetime)

    def test_food_entry_calories_calculation(self, sample_food_item):
        """Test calories calculation based on quantity."""
        entry = FoodEntry(food=sample_food_item, quantity=2.0)
        # 165 calories * 2.0 = 330
        assert entry.calories == 330.0

    def test_food_entry_macronutrients_calculation(self, sample_food_item):
        """Test macronutrients calculation based on quantity."""
        entry = FoodEntry(food=sample_food_item, quantity=2.0)
        macros = entry.macronutrients
        assert macros["protein"] == 62.0  # 31 * 2
        assert macros["fat"] == 7.2  # 3.6 * 2
        assert macros["carbs"] == 0.0  # 0 * 2

    def test_food_entry_custom_timestamp(self, sample_food_item):
        """Test FoodEntry with custom timestamp."""
        custom_time = datetime(2024, 1, 15, 12, 30, 0)
        entry = FoodEntry(food=sample_food_item, quantity=1.0, timestamp=custom_time)
        assert entry.timestamp == custom_time


class TestDailyLog:
    """Tests for DailyLog model."""

    def test_daily_log_creation(self):
        """Test creating a DailyLog."""
        log = DailyLog(day=date(2024, 1, 15))
        assert log.day == date(2024, 1, 15)
        assert log.entries == []

    def test_daily_log_add_entry(self, sample_food_entry):
        """Test adding entries to DailyLog."""
        log = DailyLog(day=date(2024, 1, 15))
        log.add_entry(sample_food_entry)
        assert len(log.entries) == 1
        assert log.entries[0] == sample_food_entry

    def test_daily_log_total_calories(self, sample_food_item):
        """Test total calories calculation."""
        log = DailyLog(day=date(2024, 1, 15))
        entry1 = FoodEntry(food=sample_food_item, quantity=1.0)
        entry2 = FoodEntry(food=sample_food_item, quantity=0.5)
        log.add_entry(entry1)
        log.add_entry(entry2)
        # 165 * 1.0 + 165 * 0.5 = 247.5
        assert log.total_calories() == 247.5

    def test_daily_log_total_macros(self, sample_food_item):
        """Test total macronutrients calculation."""
        log = DailyLog(day=date(2024, 1, 15))
        entry1 = FoodEntry(food=sample_food_item, quantity=1.0)
        entry2 = FoodEntry(food=sample_food_item, quantity=1.0)
        log.add_entry(entry1)
        log.add_entry(entry2)
        totals = log.total_macros()
        assert totals["protein"] == 62.0  # 31 * 2
        assert totals["fat"] == 7.2  # 3.6 * 2
        assert totals["carbs"] == 0.0

    def test_daily_log_empty_totals(self):
        """Test totals for empty log."""
        log = DailyLog(day=date(2024, 1, 15))
        assert log.total_calories() == 0.0
        assert log.total_macros() == {}

    def test_daily_log_to_dict(self, sample_food_entry):
        """Test converting DailyLog to dictionary."""
        log = DailyLog(day=date(2024, 1, 15))
        log.add_entry(sample_food_entry)
        result = log.to_dict()
        assert result["day"] == "2024-01-15"
        assert len(result["entries"]) == 1
        assert result["total_calories"] > 0
        assert "total_macronutrients" in result


class TestGroupEntriesByDay:
    """Tests for group_entries_by_day function."""

    def test_group_single_entry(self, sample_food_entry):
        """Test grouping a single entry."""
        grouped = group_entries_by_day([sample_food_entry])
        assert len(grouped) == 1
        assert date(2024, 1, 15) in grouped
        assert len(grouped[date(2024, 1, 15)].entries) == 1

    def test_group_multiple_entries_same_day(self, sample_food_item):
        """Test grouping multiple entries on the same day."""
        entry1 = FoodEntry(
            food=sample_food_item,
            quantity=1.0,
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
        )
        entry2 = FoodEntry(
            food=sample_food_item,
            quantity=2.0,
            timestamp=datetime(2024, 1, 15, 18, 0, 0),
        )
        grouped = group_entries_by_day([entry1, entry2])
        assert len(grouped) == 1
        assert len(grouped[date(2024, 1, 15)].entries) == 2

    def test_group_entries_different_days(self, sample_food_item):
        """Test grouping entries from different days."""
        entry1 = FoodEntry(
            food=sample_food_item,
            quantity=1.0,
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
        )
        entry2 = FoodEntry(
            food=sample_food_item,
            quantity=1.0,
            timestamp=datetime(2024, 1, 16, 12, 0, 0),
        )
        grouped = group_entries_by_day([entry1, entry2])
        assert len(grouped) == 2
        assert date(2024, 1, 15) in grouped
        assert date(2024, 1, 16) in grouped

    def test_group_empty_list(self):
        """Test grouping an empty list."""
        grouped = group_entries_by_day([])
        assert grouped == {}


class TestNutritionGoals:
    """Tests for NutritionGoals dataclass."""

    def test_defaults(self):
        goals = NutritionGoals()
        assert goals.calories is None
        assert goals.macronutrients == {}

    def test_from_dict(self):
        data = {"calories": 2000, "macronutrients": {"protein": 150}}
        goals = NutritionGoals.from_dict(data)
        assert goals.calories == 2000
        assert goals.macronutrients == {"protein": 150}

    def test_merge_updates_and_clears(self):
        goals = NutritionGoals(calories=2000, macronutrients={"protein": 150, "fat": 60})
        updated = goals.merge(macronutrients={"protein": 160, "fat": None})
        assert updated.macronutrients == {"protein": 160}
        assert updated.calories == 2000

    def test_cleaned_macros_casts_to_float(self):
        goals = NutritionGoals(macronutrients={"protein": 150})
        assert isinstance(goals.cleaned_macros()["protein"], float)
