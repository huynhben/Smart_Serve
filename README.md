Getting Started
Ensure you have Python 3.9+ installed.

Create and activate a virtual environment:

Bash

# Create the environment

python3 -m venv venv

# Activate it (on macOS/Linux)

source venv/bin/activate

Install dependencies:

Bash

# Make sure your (venv) is active first

pip install -r requirements.txt

Start the web application:

Bash

uvicorn food_tracker.api:app --reload

Visit http://localhost:8000 to use the AI-assisted food tracker in your browser. The API is exposed under the /api prefix if you want to integrate with other clients.

(Optional) Run the CLI instead of, or alongside, the web app:

Bash

# Make sure your (venv) is active

python ai.py --help
Example sessions:

Bash

# Ask the AI to recognise a food item

python ai.py scan "grilled chicken salad"

# Log the best match returned by the AI

python ai.py log "grilled chicken salad" --quantity 1.5

# Manually log a custom food

python ai.py add "Homemade Protein Bar" "1 bar" 210 --protein 15 --carbs 18 --fat 8

Features at a Glance
- AI-assisted food scanning with instant logging from the browser or CLI.
- Custom food logging with optional macro tracking and shared persistence between UI/CLI.
- Personalised nutrition goals with live progress bars for calories and macros.
- Weekly insights with streak tracking, per-day calorie totals, and lifetime stats.
- New API endpoints (`/api/goals`, `/api/stats`) plus CLI helpers (`goals`, `stats`) for advanced workflows.
