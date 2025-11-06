import numpy as np
from src.haversine import haversine_np


def test_haversine_equator_degree():
    # approximate distance from (0,0) to (0,1) ~ 111.32 km
    d = haversine_np(0.0, 0.0, [0.0], [1.0])[0]
    assert abs(d - 111.32) < 0.5
