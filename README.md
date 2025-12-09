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

Mobile camera scanning (Expo Go)
1) Enable vision AI on the backend (required):
   - Provide an OpenAI key: `export OPENAI_API_KEY=...`
   - Start the API bound to your LAN IP so your phone can reach it:
     `uvicorn food_tracker.api:app --host 0.0.0.0 --port 8000 --reload`

2) Install the mobile app dependencies (from the repo root):
   - `cd mobile && npm install` (requires network access)

3) Point the app at your backend:
   - Set `EXPO_PUBLIC_API_BASE=http://<your-lan-ip>:8000/api`

4) Run the Expo dev server and open the project in Expo Go on your phone:
   - `npm start` (inside `mobile/`), then scan the QR code with Expo Go.

5) In the app, tap Take photo (or Choose from library), then Scan image. The app will:
   - Capture the image
   - Send it to `/api/foods/scan-image`
   - Display predicted foods/macros with a Log button that calls `/api/entries`
