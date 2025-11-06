import os
import json
import numpy as np

from src.embeddings import init_model, embed_texts
from src.retrieval import find_best_alternative


def test_alternative_found_dummy():
    # Use dummy provider for deterministic vectors
    init_model(provider="dummy")
    # inventory two similar items and one different
    inventory_texts = ["Paracetamol 500mg pain relief", "Paracetamol 650mg extra strength", "Vitamin C chews"]
    embs = embed_texts(inventory_texts)

    query = "Paracetamol 500 mg tablet"
    q_emb = embed_texts([query])[0]
    idx, sim = find_best_alternative(q_emb, embs)
    assert idx is not None
    assert sim > 0.6  # dummy hashing still gives some similarity
