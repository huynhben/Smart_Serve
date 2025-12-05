"""Image recognition helpers using CLIP to match photos to foods.json.

This module performs a simple image->text embedding match using the
Hugging Face CLIP model. It loads the food catalog from
`food_tracker/data/foods.json`, builds a short text description for each
food (name + aliases), computes text embeddings once, and exposes
`match_image_to_foods(image_bytes, top_k)` which returns the best matches.

Notes:
- Requires `transformers`, `torch`, `Pillow`, and `numpy`.
- This implementation is intentionally minimal for a prototype.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

import numpy as np
from PIL import Image

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
except Exception:  # pragma: no cover - optional dependency
    CLIPModel = None  # type: ignore
    CLIPProcessor = None  # type: ignore
    torch = None  # type: ignore


ROOT = Path(__file__).resolve().parent
FOODS_FILE = ROOT / "data" / "foods.json"
EMBED_FILE = ROOT / "data" / "food_text_embeddings.npz"

# Module-level cache
_model = None
_processor = None
_text_embeddings = None
_food_records: List[Dict] | None = None


def _load_foods() -> List[Dict]:
    global _food_records
    if _food_records is None:
        with FOODS_FILE.open("r", encoding="utf8") as f:
            _food_records = json.load(f)
    return _food_records


def _ensure_model() -> None:
    global _model, _processor
    if _model is None or _processor is None:
        if CLIPModel is None or CLIPProcessor is None:
            raise RuntimeError("CLIP dependencies not installed. Install torch and transformers.")
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        if torch is not None:
            _model.eval()


def _build_text_corpus(foods: List[Dict]) -> List[str]:
    texts: List[str] = []
    for item in foods:
        parts = [item.get("name", "")]
        aliases = item.get("aliases") or []
        parts.extend(aliases)
        # join name + aliases into a single short string
        texts.append(" ".join(parts))
    return texts


def _ensure_text_embeddings() -> None:
    """Compute and cache text embeddings for the foods corpus."""
    global _text_embeddings
    if _text_embeddings is not None:
        return

    foods = _load_foods()
    texts = _build_text_corpus(foods)

    # Try to load precomputed embeddings from disk
    if EMBED_FILE.exists():
        try:
            npz = np.load(EMBED_FILE, allow_pickle=True)
            embeddings = npz["embeddings"]
            names = npz.get("names")
            # validate size matches foods
            if embeddings.shape[0] == len(foods):
                _text_embeddings = embeddings.astype(float)
                return
            else:
                # mismatch: fall back to recomputing
                pass
        except Exception:
            # ignore and compute fresh
            pass

    _ensure_model()
    assert _processor is not None and _model is not None

    # Tokenize text and compute embeddings
    inputs = _processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        text_feats = _model.get_text_features(**{k: v.to(_model.device) for k, v in inputs.items()})

    # convert to numpy and normalize
    feats = text_feats.cpu().numpy()
    norms = np.linalg.norm(feats, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    feats = feats / norms
    _text_embeddings = feats

    # attempt to save embeddings for faster startup later
    try:
        np.savez_compressed(EMBED_FILE, embeddings=feats.astype(np.float32), names=np.array([f.get("name") for f in foods], dtype=object), texts=np.array(texts, dtype=object))
    except Exception:
        # best-effort: don't fail on save errors
        pass


def match_image_to_foods(image_bytes: bytes, top_k: int = 5) -> List[Dict]:
    """Return top-K matching foods for the provided image bytes.

    Each result is a dict with keys: `food` (dict from foods.json) and
    `confidence` (float 0..1 cosine similarity).
    """
    foods = _load_foods()
    _ensure_text_embeddings()
    if _text_embeddings is None:
        return []

    _ensure_model()
    assert _processor is not None and _model is not None

    # Use PIL to open image from bytes
    from io import BytesIO

    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # Preprocess and get image embedding
    inputs = _processor(images=img, return_tensors="pt")
    with torch.no_grad():
        image_feats = _model.get_image_features(**{k: v.to(_model.device) for k, v in inputs.items()})

    img_vec = image_feats.cpu().numpy()
    img_vec = img_vec / (np.linalg.norm(img_vec, axis=1, keepdims=True) + 1e-12)
    img_vec = img_vec[0]

    # cosine similarity with all text embeddings
    sims = (np.dot(_text_embeddings, img_vec)).astype(float)
    # Get top_k indices
    idx = np.argsort(-sims)[:top_k]

    results: List[Dict] = []
    for i in idx:
        results.append({"food": foods[i], "confidence": float(sims[i])})

    return results
