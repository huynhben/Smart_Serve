"""FastAPI application exposing the food tracker over HTTP."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from .ai import FoodRecognitionEngine
from .models import DailyLog, FoodEntry, FoodItem
from .tracker import FoodTracker

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


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


def _build_tracker() -> FoodTracker:
    """Initialise the tracker with the default recognition engine."""
    try:
        recogniser = FoodRecognitionEngine()
        tracker = FoodTracker(recogniser=recogniser)
        logger.info("Food tracker initialized successfully")
        return tracker
    except Exception as e:
        logger.error(f"Failed to initialize food tracker: {e}", exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Food Tracker API")
    app.state.tracker = _build_tracker()
    yield
    # Shutdown
    logger.info("Shutting down Food Tracker API")


# Configure CORS - restrict to localhost and common development origins
# In production, set this via environment variable
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]

app = FastAPI(title="Food Tracker", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def get_tracker() -> FoodTracker:
    """Get the tracker instance from app state."""
    tracker: FoodTracker | None = getattr(app.state, "tracker", None)
    if tracker is None:
        logger.warning("Tracker not found in app state, creating new instance")
        tracker = _build_tracker()
        app.state.tracker = tracker
    return tracker


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "message": str(exc)},
    )


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


@api_router.get("/foods/search")
def search_foods(query: str = Query("", min_length=0), tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Search for foods by description."""
    try:
        if not query.strip():
            return {"items": []}
        logger.info(f"Searching for foods with query: {query}")
        results = tracker.scan_description(query)
        items = [
            {
                "food": _serialise_food(result.item),
                "confidence": result.confidence,
            }
            for result in results
        ]
        logger.info(f"Found {len(items)} results for query: {query}")
        return {"items": items}
    except Exception as e:
        logger.error(f"Error searching foods: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search foods: {str(e)}",
        )


@api_router.get("/foods/library")
def library(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Get all foods in the library."""
    try:
        items = [_serialise_food(item) for item in tracker.recogniser.known_items()]
        logger.info(f"Retrieved {len(items)} items from library")
        return {"items": items}
    except Exception as e:
        logger.error(f"Error retrieving food library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve food library: {str(e)}",
        )


@api_router.post("/foods", status_code=201)
def register_food(payload: CustomFoodPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Register a custom food item."""
    try:
        # Validate macronutrients are non-negative
        for nutrient, amount in payload.macronutrients.items():
            if amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Macronutrient '{nutrient}' cannot be negative",
                )
        
        logger.info(f"Registering custom food: {payload.name}")
        item = tracker.register_custom_food(
            name=payload.name,
            serving_size=payload.serving_size,
            calories=payload.calories,
            macronutrients=payload.macronutrients,
            aliases=payload.aliases,
        )
        logger.info(f"Successfully registered food: {payload.name}")
        return _serialise_food(item)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering food: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register food: {str(e)}",
        )


@api_router.get("/entries")
def list_entries(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """List all food entries."""
    try:
        entries = [_serialise_entry(entry) for entry in tracker.entries()]
        logger.info(f"Retrieved {len(entries)} entries")
        return {"items": entries}
    except Exception as e:
        logger.error(f"Error listing entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list entries: {str(e)}",
        )


@api_router.post("/entries", status_code=201)
def create_entry(payload: EntryPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Create a new food entry."""
    try:
        # Validate macronutrients are non-negative
        for nutrient, amount in payload.food.macronutrients.items():
            if amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Macronutrient '{nutrient}' cannot be negative",
                )
        
        # Validate quantity is reasonable (max 1000)
        if payload.quantity > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity cannot exceed 1000",
            )
        
        logger.info(f"Creating entry for food: {payload.food.name}, quantity: {payload.quantity}")
        food = FoodItem(
            name=payload.food.name,
            serving_size=payload.food.serving_size,
            calories=payload.food.calories,
            macronutrients=payload.food.macronutrients,
            aliases=payload.food.aliases,
        )
        entry = tracker.log_food(food, quantity=payload.quantity, timestamp=payload.timestamp)
        logger.info(f"Successfully created entry for: {payload.food.name}")
        return _serialise_entry(entry)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entry: {str(e)}",
        )


@api_router.get("/summary")
def summary(tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
    """Get daily summaries."""
    try:
        logs = [_serialise_daily_log(log) for log in tracker.daily_summary()]
        logger.info(f"Retrieved summary for {len(logs)} days")
        return {"days": logs}
    except Exception as e:
        logger.error(f"Error retrieving summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve summary: {str(e)}",
        )


app.include_router(api_router)


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("food_tracker.api:app", host="0.0.0.0", port=8000, reload=True)
