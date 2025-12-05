"""Precompute CLIP text embeddings for the foods corpus.

Saves a compressed `.npz` file into `food_tracker/data/food_text_embeddings.npz`.

Usage:
  python scripts/precompute_embeddings.py

Notes:
- Requires `torch` and `transformers` installed and available to the interpreter.
"""

from pathlib import Path
import json
import numpy as np

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
except Exception as exc:  # pragma: no cover - dev tool
    raise SystemExit("Missing dependencies: install torch and transformers") from exc


ROOT = Path(__file__).resolve().parent.parent
FOODS_FILE = ROOT / "food_tracker" / "data" / "foods.json"
OUT_FILE = ROOT / "food_tracker" / "data" / "food_text_embeddings.npz"


def build_texts(foods):
    return [" ".join([item.get("name", "")] + item.get("aliases", [])) for item in foods]


def main():
    with FOODS_FILE.open("r", encoding="utf8") as f:
        foods = json.load(f)

    texts = build_texts(foods)

    print(f"Computing embeddings for {len(texts)} food texts...")

    model_name = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.eval()

    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        feats = model.get_text_features(**{k: v for k, v in inputs.items()})

    feats = feats.cpu().numpy()
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    feats = feats / norms

    names = [item.get("name") for item in foods]
    np.savez_compressed(OUT_FILE, embeddings=feats.astype(np.float32), names=np.array(names, dtype=object), texts=np.array(texts, dtype=object))

    print(f"Saved embeddings to {OUT_FILE}")


def _friendly_install_instructions():
    return (
        "\nPossible fixes:\n"
        "  - Activate your virtualenv (if you created one):\n"
        "      source .venv/bin/activate\n"
        "  - Upgrade pip and install requirements:\n"
        "      python -m pip install --upgrade pip\n"
        "      pip install -r requirements.txt\n"
        "  - If `pip install torch` fails on macOS (Apple Silicon), follow the official guide:\n"
        "      https://pytorch.org/get-started/locally/\n"
        "    Use the selector to get the correct install command for your OS/Python/CUDA setup.\n"
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # re-raise SystemExit so callers still see non-zero exit code
        raise
    except Exception as exc:  # pragma: no cover - runtime helper
        print("Failed to precompute embeddings:\n")
        import traceback

        traceback.print_exc()
        print(_friendly_install_instructions())
        raise
