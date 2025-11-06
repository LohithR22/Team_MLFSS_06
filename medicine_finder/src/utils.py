"""Helper utilities and default configuration."""
from typing import Dict, Any
import json
import os

DEFAULT_CONFIG = {
    "ALT_SIM_THRESHOLD": 0.75,
    "WEIGHTS": {"availability": 0.6, "price": 0.25, "distance": 0.15},
    "EMB_PROVIDER": "sentence-transformers",
    "EMB_MODEL_NAME": "all-MiniLM-L6-v2",
}


def ensure_data_dir(base_path: str):
    d = os.path.join(base_path, "data")
    os.makedirs(d, exist_ok=True)
    return d


def dump_json_pretty(obj: Dict[str, Any], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def ensure_log_dir(base_path: str):
    """Creates a 'logs' directory in the project root and returns its path."""
    d = os.path.join(base_path, "logs")
    os.makedirs(d, exist_ok=True)
    return d
