"""Local semantic scores. Never calls a hosted embedding API."""
import math
import os
from functools import lru_cache
from typing import Any

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _load_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer
    # Download model separately during setup, never during a user's query.
    return SentenceTransformer(model_name, device="cpu", local_files_only=True,
                               trust_remote_code=False)


def semantic_scores(query: str, texts: list[str]) -> list[float]:
    """Cosine similarities using local, normalized embeddings, without text caching."""
    if not texts:
        return []
    model = _load_model(os.getenv("SELFMAP_EMBEDDING_MODEL", DEFAULT_MODEL))
    vectors = model.encode([query, *texts], normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False,
                           batch_size=32)
    if vectors.ndim != 2 or vectors.shape[0] != len(texts) + 1:
        raise ValueError("Invalid embedding shape")
    scores = (vectors[1:] @ vectors[0]).tolist()
    if not all(math.isfinite(value) for value in scores):
        raise ValueError("Nonfinite similarity")
    return [max(-1.0, min(1.0, float(value))) for value in scores]
