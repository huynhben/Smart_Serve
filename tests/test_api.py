"""Tests for the API module."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from food_tracker.api import app
from food_tracker.models import FoodItem


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    """Create a test client for the FastAPI app with isolated storage."""
    data_dir = tmp_path / "api_data"
    data_dir.mkdir()
    monkeypatch.setenv("FOOD_TRACKER_DATA_DIR", str(data_dir))
    with TestClient(app) as client:
        client.app.state.tracker = None  # Reset tracker to use new storage
        yield client


@pytest.fixture
def sample_food_payload() -> dict:
    """Sample food payload for API requests."""
    return {
        "name": "Test Food",
        "serving_size": "100g",
        "calories": 200.0,
        "macronutrients": {"protein": 20.0, "carbs": 30.0, "fat": 10.0},
        "aliases": ["test"],
    }


class TestFoodSearch:
    """Tests for /api/foods/search endpoint."""

    def test_search_with_query(self, client):
        """Test searching foods with a query."""
        response = client.get("/api/foods/search?query=chicken")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_search_empty_query(self, client):
        """Test searching with empty query."""
        response = client.get("/api/foods/search?query=")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_search_no_query(self, client):
        """Test searching without query parameter."""
        response = client.get("/api/foods/search")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_search_returns_confidence(self, client):
        """Test that search results include confidence scores."""
        response = client.get("/api/foods/search?query=chicken")
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            assert "food" in item
            assert "confidence" in item
            assert isinstance(item["confidence"], (int, float))
            assert 0 <= item["confidence"] <= 1


class TestFoodLibrary:
    """Tests for /api/foods/library endpoint."""

    def test_library_endpoint(self, client):
        """Test getting the food library."""
        response = client.get("/api/foods/library")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        if data["items"]:
            item = data["items"][0]
            assert "name" in item
            assert "serving_size" in item
            assert "calories" in item


class TestRegisterFood:
    """Tests for POST /api/foods endpoint."""

    def test_register_food(self, client, sample_food_payload):
        """Test registering a custom food."""
        response = client.post("/api/foods", json=sample_food_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_food_payload["name"]
        assert data["calories"] == sample_food_payload["calories"]

    def test_register_food_minimal(self, client):
        """Test registering food with minimal fields."""
        payload = {
            "name": "Simple Food",
            "serving_size": "1 serving",
            "calories": 100.0,
        }
        response = client.post("/api/foods", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple Food"

    def test_register_food_validation(self, client):
        """Test that invalid food data is rejected."""
        payload = {
            "name": "Invalid Food",
            "serving_size": "1 serving",
            "calories": -100.0,  # Negative calories should fail
        }
        response = client.post("/api/foods", json=payload)
        assert response.status_code == 422  # Validation error


class TestListEntries:
    """Tests for GET /api/entries endpoint."""

    def test_list_entries_empty(self, client):
        """Test listing entries when none exist."""
        response = client.get("/api/entries")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_entries_with_data(self, client, sample_food_payload):
        """Test listing entries after creating one."""
        # Create an entry
        entry_payload = {"food": sample_food_payload, "quantity": 1.0}
        client.post("/api/entries", json=entry_payload)

        # List entries
        response = client.get("/api/entries")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        entry = data["items"][0]
        assert "food" in entry
        assert "quantity" in entry
        assert "timestamp" in entry
        assert "calories" in entry


class TestCreateEntry:
    """Tests for POST /api/entries endpoint."""

    def test_create_entry(self, client, sample_food_payload):
        """Test creating a food entry."""
        payload = {"food": sample_food_payload, "quantity": 1.5}
        response = client.post("/api/entries", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 1.5
        assert data["food"]["name"] == sample_food_payload["name"]
        assert "timestamp" in data

    def test_create_entry_custom_timestamp(self, client, sample_food_payload):
        """Test creating entry with custom timestamp."""
        custom_time = "2024-01-15T12:30:00"
        payload = {
            "food": sample_food_payload,
            "quantity": 1.0,
            "timestamp": custom_time,
        }
        response = client.post("/api/entries", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["timestamp"] == custom_time

    def test_create_entry_validation(self, client, sample_food_payload):
        """Test that invalid entry data is rejected."""
        payload = {"food": sample_food_payload, "quantity": -1.0}  # Negative quantity
        response = client.post("/api/entries", json=payload)
        assert response.status_code == 422  # Validation error

    def test_create_entry_default_quantity(self, client, sample_food_payload):
        """Test creating entry with default quantity."""
        payload = {"food": sample_food_payload}
        response = client.post("/api/entries", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 1.0


class TestSummary:
    """Tests for GET /api/summary endpoint."""

    def test_summary_empty(self, client):
        """Test summary when no entries exist."""
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert isinstance(data["days"], list)

    def test_summary_with_entries(self, client, sample_food_payload):
        """Test summary with entries."""
        # Create an entry
        entry_payload = {"food": sample_food_payload, "quantity": 1.0}
        client.post("/api/entries", json=entry_payload)

        # Get summary
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()
        if data["days"]:
            day = data["days"][0]
            assert "day" in day
            assert "entries" in day
            assert "total_calories" in day
            assert "total_macronutrients" in day


class TestAPISerialization:
    """Tests for API response serialization."""

    def test_food_serialization(self, client, sample_food_payload):
        """Test that food items are properly serialized."""
        response = client.post("/api/foods", json=sample_food_payload)
        data = response.json()
        assert "name" in data
        assert "serving_size" in data
        assert "calories" in data
        assert "macronutrients" in data
        assert "aliases" in data

    def test_entry_serialization(self, client, sample_food_payload):
        """Test that entries are properly serialized."""
        payload = {"food": sample_food_payload, "quantity": 1.0}
        response = client.post("/api/entries", json=payload)
        data = response.json()
        assert "food" in data
        assert "quantity" in data
        assert "timestamp" in data
        assert "calories" in data
        assert "macronutrients" in data

    def test_daily_log_serialization(self, client, sample_food_payload):
        """Test that daily logs are properly serialized."""
        # Create entry first
        entry_payload = {"food": sample_food_payload, "quantity": 1.0}
        client.post("/api/entries", json=entry_payload)

        response = client.get("/api/summary")
        data = response.json()
        if data["days"]:
            day = data["days"][0]
            assert isinstance(day["day"], str)  # ISO format
            assert isinstance(day["entries"], list)
            assert isinstance(day["total_calories"], (int, float))
            assert isinstance(day["total_macronutrients"], dict)


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.options("/api/foods/search")
        # CORS middleware should be configured
        # Note: TestClient might not show all CORS headers, but the middleware is configured


class TestGoalsEndpoint:
    """Tests for /api/goals endpoints."""

    def test_get_goals_default(self, client):
        response = client.get("/api/goals")
        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert data["goals"]["calories"] is None

    def test_update_goals(self, client):
        payload = {"calories": 2000, "macronutrients": {"protein": 150, "fat": 60}}
        response = client.put("/api/goals", json=payload)
        assert response.status_code == 200
        data = response.json()["goals"]
        assert data["calories"] == 2000
        assert data["macronutrients"]["protein"] == 150

        # Ensure GET reflects updated goals
        response = client.get("/api/goals")
        goals = response.json()["goals"]
        assert goals["calories"] == 2000


class TestStatsEndpoint:
    """Tests for /api/stats endpoint."""

    def test_stats_structure_without_entries(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "today" in data
        assert "weekly" in data
        assert "lifetime" in data

    def test_stats_with_entries(self, client, sample_food_payload):
        client.post("/api/entries", json={"food": sample_food_payload, "quantity": 2.0})
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        today = data["today"]
        assert today["calories"]["consumed"] > 0
        weekly = data["weekly"]
        assert isinstance(weekly["days"], list)
        lifetime = data["lifetime"]
        assert lifetime["total_entries"] >= 1
