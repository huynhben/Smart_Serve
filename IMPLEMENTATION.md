PM4 – AI Assisted Food Tracker
This project contains a lightweight food tracking application that blends the standard features of calorie trackers with an AI-inspired recognition engine. The codebase now offers both a command-line experience and a fullstack web application. The FastAPI backend exposes the tracker over HTTP, while the bundled frontend delivers a responsive interface for scanning foods, logging meals, and reviewing summaries.

Features
AI-assisted food scanning – type or paste a description to get the top matches along with confidence scores in the browser or via the CLI.

Manual logging – quickly add foods that are not part of the reference database while still storing macros and calories.

Daily summaries – review the foods eaten each day alongside total calories and macronutrients.

Fullstack delivery – FastAPI powers a JSON API and serves a polished single-page interface without extra build steps.

Extensible design – the recognition engine is intentionally simple so it can run offline, but its API can be swapped for a heavier ML model when needed.

Goal tracking – define daily calorie and macro targets and monitor progress via the new `/api/goals` endpoint, CLI helpers, and UI progress panels.

Weekly intelligence – the `/api/stats` endpoint powers streaks, average calories, and lifetime stats rendered directly in the dashboard.

python ai.py summary
Data is stored as JSON under ~/.food_tracker/log.json so you can safely delete that file to reset your log. The web UI, API, and CLI all share the same persistent log.

Extending the AI Component
The FoodRecognitionEngine in food_tracker/ai.py uses a simple bag-of-words embedding so the project remains dependency free. To integrate a more sophisticated model:

Replace the implementation of EmbeddingModel.encode with calls to your preferred ML library.

Expand food_tracker/data/foods.json or connect the tracker to a nutrition API.

Update the CLI or build a GUI/mobile frontend using the FoodTracker class from food_tracker/tracker.py.

Project Layout
food_tracker/
├── ai.py # AI recognition helpers
├── api.py # FastAPI application & static file server
├── cli.py # Command line interface
├── data/foods.json # Reference nutrition dataset
├── models.py # Data classes and helpers
├── storage.py # Persistence utilities
└── tracker.py # High-level orchestration
frontend/
├── app.js # Browser client logic
├── index.html # Single-page shell served by FastAPI
└── styles.css # UI styling
Use FoodTracker as the main entry point if you intend to embed the tracking logic into another application layer.
