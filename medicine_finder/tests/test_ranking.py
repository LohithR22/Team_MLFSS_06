from src.ranking import compute_scores


def test_ranking_prefers_availability():
    # Two stores with same total_requested
    s1 = {"counts": {"available": 2, "alternatives": 0, "missing": 0}, "total_price": 50.0, "distance_km": 5.0, "total_requested": 2}
    s2 = {"counts": {"available": 1, "alternatives": 1, "missing": 0}, "total_price": 20.0, "distance_km": 1.0, "total_requested": 2}

    avg_ref = 35.0
    weights = {"availability": 0.6, "price": 0.25, "distance": 0.15}
    c1, _ = compute_scores(s1, avg_ref, weights)
    c2, _ = compute_scores(s2, avg_ref, weights)
    # s1 has higher availability -> should have higher score despite price/distance
    assert c1 > c2
