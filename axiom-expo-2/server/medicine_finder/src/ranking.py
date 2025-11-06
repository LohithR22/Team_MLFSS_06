"""Scoring and ranking utilities."""
from typing import Dict, Any, Tuple
import numpy as np


def compute_scores(store_entry: Dict[str, Any], avg_price_ref: float, weights: Dict[str, float]):
    """Compute composite score and breakdown for a store_entry produced by app logic.

    store_entry must contain counts and total_price and distance_km.
    """
    total_requested = store_entry.get("total_requested", 1)
    counts = store_entry.get("counts", {})
    count_available = counts.get("available", 0)
    count_alternatives = counts.get("alternatives", 0)
    count_missing = counts.get("missing", 0)

    availability_score = (count_available + 0.5 * count_alternatives) / float(total_requested)

    # price normalization: avoid divide by zero
    total_price = store_entry.get("total_price", 0.0)
    ref = avg_price_ref if avg_price_ref > 0 else 1.0
    normalized_total_price = total_price / ref
    price_score = 1.0 / (1.0 + normalized_total_price)

    distance_km = float(store_entry.get("distance_km", 0.0))
    distance_score = 1.0 / (1.0 + distance_km)

    w1 = weights.get("availability", 0.6)
    w2 = weights.get("price", 0.25)
    w3 = weights.get("distance", 0.15)

    composite = w1 * availability_score + w2 * price_score + w3 * distance_score

    breakdown = {
        "availability": availability_score,
        "price": price_score,
        "distance": distance_score,
    }

    return float(composite), breakdown
