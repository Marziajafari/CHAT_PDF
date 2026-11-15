"""Download all-MiniLM-L6-v2 once (needs internet). Afterwards the app works fully offline.

Run from the backend folder:  python scripts/download_embedding_model.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentence_transformers import SentenceTransformer  # noqa: E402

from app.core.config import settings  # noqa: E402

print(f"Downloading '{settings.embedding_model}' ...")
model = SentenceTransformer(settings.embedding_model, device="cpu")
vector = model.encode(["hello world"], normalize_embeddings=True)
print(f"OK. Embedding size: {len(vector[0])}. The model is cached for offline use.")
