"""Embedding provider abstraction with caching and a dummy provider for tests."""
from typing import List, Optional, Iterable, Dict
import numpy as np
import os
import hashlib

_model = None
_provider = None


def init_model(provider: str = "sentence-transformers", model_name: str = "all-MiniLM-L6-v2"):
    """Initialize embedding provider. Supports 'sentence-transformers', 'openai' (placeholder), or 'dummy'."""
    global _model, _provider
    _provider = provider
    if provider == "sentence-transformers":
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(model_name)
        except Exception as e:
            # fall back to dummy
            _model = None
            _provider = "dummy"
    elif provider == "openai":
        # Placeholder: user must supply OPENAI_API_KEY and implement later
        _model = None
    elif provider == "dummy":
        _model = None
    else:
        _model = None
        _provider = "dummy"


def _dummy_embed_texts(texts: Iterable[str]) -> np.ndarray:
    # deterministic pseudo-embedding from sha256 -> vector
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        # take first 32 bytes -> 32 dims
        vec = np.frombuffer(h, dtype=np.uint8).astype(float)
        vec = vec / (np.linalg.norm(vec) + 1e-12)
        out.append(vec)
    return np.vstack(out)


def embed_texts(texts: List[str], normalize: bool = True) -> np.ndarray:
    """Embed a list of texts. Returns numpy array (N, D). If provider supports normalization, vectors are normalized.
    Falls back to dummy provider if configured or import fails.
    """
    global _model, _provider
    if _provider is None:
        init_model()

    if _provider == "sentence-transformers" and _model is not None:
        embs = _model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=normalize)
        return embs
    # fallback dummy
    embs = _dummy_embed_texts(texts)
    if normalize:
        from sklearn.preprocessing import normalize as _norm

        embs = _norm(embs, axis=1)
    return embs


def cache_embeddings(cache_path: str, keys: List[str], embeddings: np.ndarray):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    # Save as npz with keys and embeddings
    np.savez(cache_path, keys=np.array(keys, dtype=object), embs=embeddings)


def load_cached_embeddings(cache_path: str):
    if not os.path.exists(cache_path):
        return None, None
    data = np.load(cache_path, allow_pickle=True)
    keys = list(data["keys"])
    embs = data["embs"]
    return keys, embs
