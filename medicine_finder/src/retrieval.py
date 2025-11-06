"""Per-store retrieval utilities (cosine similarity search)."""
from typing import Tuple, Optional, List
import numpy as np


def build_store_matrix(embeddings_list):
    """Given list of embeddings (N, D) or list of vectors, return np.ndarray (N, D).
    If input is empty, returns an empty array shape (0, D).
    """
    if len(embeddings_list) == 0:
        return np.zeros((0, 0), dtype=float)
    arr = np.vstack(embeddings_list)
    return arr


def find_best_alternatives_sorted(request_emb: np.ndarray, store_embs: np.ndarray) -> Tuple[List[int], List[float]]:
    """
    Finds all items, sorted by similarity (cosine). Assumes normalized embeddings.
    Returns (sorted_indices, sorted_similarities) as lists.
    If store_embs is empty returns ([], []).
    """
    if store_embs.size == 0:
        return [], []
    
    if request_emb.ndim == 1:
        q = request_emb
    else:
        q = request_emb.ravel()

    # Dot product since embeddings assumed normalized
    sims = store_embs.dot(q)
    
    # Sort indices by similarity, descending
    sorted_indices = np.argsort(sims)[::-1]
    sorted_similarities = sims[sorted_indices]
    
    return sorted_indices.tolist(), sorted_similarities.tolist()


def find_best_alternative(request_emb: np.ndarray, store_embs: np.ndarray) -> Tuple[Optional[int], float]:
    """Backward-compatible wrapper returning the single best match (index, sim).
    Uses find_best_alternatives_sorted under the hood.
    """
    indices, sims = find_best_alternatives_sorted(request_emb, store_embs)
    if not indices:
        return None, 0.0
    return int(indices[0]), float(sims[0])
