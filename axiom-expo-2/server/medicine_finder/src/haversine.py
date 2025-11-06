"""Vectorized Haversine distance utilities."""
from typing import Iterable
import numpy as np

R = 6371.0  # Earth radius km


def haversine_np(lat1: float, lon1: float, lat2_arr: Iterable[float], lon2_arr: Iterable[float]) -> np.ndarray:
    """Compute Haversine distance (km) from a single point (lat1, lon1)
    to arrays of points lat2_arr, lon2_arr.

    Returns an array of distances in kilometers.
    """
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2 = np.radians(np.array(lat2_arr, dtype=float))
    lon2 = np.radians(np.array(lon2_arr, dtype=float))
    dlat = lat2 - lat1_rad
    dlon = lon2 - lon1_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c
