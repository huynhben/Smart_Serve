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

## Image scan (camera) — Local CLIP prototype

This repository includes a local CLIP-based image scanner prototype that lets you capture a photo from your laptop camera (or upload an image) and returns the best-matching foods from `food_tracker/data/foods.json`.

Prerequisites

- Python 3.9+ (use a virtual environment)
- `torch`, `transformers`, `Pillow`, `numpy` (see note for macOS/Apple Silicon)
- `python-multipart` (required for file uploads)

Installation (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install python-multipart
```

Note: Installing `torch` on macOS (especially Apple Silicon) can require platform-specific wheels. If `pip install -r requirements.txt` fails when installing `torch`, visit https://pytorch.org/get-started/locally/ and use the selector to get the correct install command for your macOS/Python configuration.

## Precompute embeddings (recommended)

The first request that uses CLIP will compute text embeddings for the whole food corpus which can be slow. Precompute them once with:

```bash
python scripts/precompute_embeddings.py
```

This writes `food_tracker/data/food_text_embeddings.npz` so the server starts and responds faster.

## Run the app

```bash
# after venv and precompute
uvicorn food_tracker.api:app --reload
```

Open http://127.0.0.1:8000 in your browser. The frontend contains a "Scan a food" card with a camera preview and "Capture & Scan" button — grant camera permission and capture a photo to scan.

Troubleshooting

- If you see: "Form data requires \"python-multipart\" to be installed" — run `pip install python-multipart`.
- If you see SSL/OpenSSL related warnings from `urllib3` on macOS, they are warnings only and can be ignored; resolving them may require reinstalling Python linked to OpenSSL.
- If CLIP/model download fails due to network or model cache issues, re-run the precompute script; ensure your machine can access the Hugging Face model repo.

Next steps

- Add an LRU cache or limit upload size for production use.
- Consider a cloud-vision fallback (Google Vision) if installing `torch` is not feasible.
