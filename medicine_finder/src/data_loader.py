"""CSV loader for prototype: expects flattened rows with an `availability` boolean.

This simplified loader intentionally avoids heavy normalization. It expects the CSV to contain
per-row inventory entries with the following columns (case-insensitive):

- store_id
- store_name
- latitude
- longitude
- medicine_id
- medicine_name
- medicine_desc (optional)
- price
- availability (True/False or 1/0 or Y/N)

If `availability` is missing but `stock` exists, stock>0 will be treated as available.

Returns:
  store_meta: dict store_id -> {store_name, latitude, longitude}
  inventory: dict store_id -> list of items {medicine_id, medicine_name, medicine_desc, price, availability}
"""
from typing import Dict, List, Any
import pandas as pd
import os


def _parse_bool(val: Any) -> bool:
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("true", "t", "1", "yes", "y"):  # common truthy
        return True
    return False


def load_and_normalize(csv_path: str):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # lowercase mapping for convenience
    cols = {c.lower(): c for c in df.columns}

    # required mappings (with extra fallbacks present in final_realistic.csv)
    store_id_col = cols.get("store_id") or cols.get("store") or cols.get("store_name")
    store_name_col = cols.get("store_name") or cols.get("name")
    lat_col = cols.get("latitude") or cols.get("lat") or cols.get("store_latitude")
    lon_col = cols.get("longitude") or cols.get("lon") or cols.get("store_longitude")
    med_id_col = cols.get("medicine_id") or cols.get("med_id") or cols.get("medicine") or cols.get("drug_name")
    med_name_col = cols.get("medicine_name") or cols.get("drug_name")
    med_desc_col = cols.get("medicine_desc") or cols.get("description") or cols.get("medical_condition_description")
    price_col = cols.get("price") or cols.get("cost")
    avail_col = cols.get("availability") or cols.get("available")
    stock_col = cols.get("stock") or cols.get("quantity") or cols.get("qty")

    store_meta: Dict[str, Dict[str, Any]] = {}
    inventory: Dict[str, List[Dict[str, Any]]] = {}

    # map medicine_name (lowercased) -> description (first seen)
    medicine_description_map: Dict[str, str] = {}

    for _, row in df.iterrows():
        sid = str(row[store_id_col]) if store_id_col and store_id_col in row.index else "default_store"
        sname = row[store_name_col] if store_name_col and store_name_col in row.index else sid
        lat = float(row[lat_col]) if lat_col and lat_col in row.index and pd.notna(row[lat_col]) else 0.0
        lon = float(row[lon_col]) if lon_col and lon_col in row.index and pd.notna(row[lon_col]) else 0.0

        store_meta.setdefault(sid, {"store_name": sname, "latitude": lat, "longitude": lon})

        med_id = str(row[med_id_col]) if med_id_col and med_id_col in row.index else str(_)
        med_name = str(row[med_name_col]) if med_name_col and med_name_col in row.index else ""
        med_desc = str(row[med_desc_col]) if med_desc_col and med_desc_col in row.index and pd.notna(row[med_desc_col]) else ""
        price = float(row[price_col]) if price_col and price_col in row.index and pd.notna(row[price_col]) else 0.0

        if avail_col and avail_col in row.index:
            available = _parse_bool(row[avail_col])
        elif stock_col and stock_col in row.index:
            try:
                available = float(row[stock_col]) > 0
            except Exception:
                available = _parse_bool(row[stock_col])
        else:
            # default to False if not present
            available = False

        med = {
            "medicine_id": med_id,
            "medicine_name": med_name,
            "medicine_desc": med_desc,
            "price": price,
            "availability": bool(available),
        }
        inventory.setdefault(sid, []).append(med)

        # Populate the description map using the first description seen for a medicine name
        if med_name and med_desc:
            mn = med_name.strip().lower()
            if mn not in medicine_description_map:
                medicine_description_map[mn] = med_desc
    return store_meta, inventory, medicine_description_map


def save_processed(data_dir: str, store_meta: Dict[str, Any], inventory: Dict[str, List[Dict[str, Any]]], med_desc_map: Dict[str, str]):
    """Save processed store_meta, inventory and med_desc_map to JSON files under data_dir."""
    import json, os
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "processed_store_meta.json"), "w", encoding="utf-8") as f:
        json.dump(store_meta, f, indent=2, ensure_ascii=False)
    with open(os.path.join(data_dir, "processed_inventory.json"), "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    with open(os.path.join(data_dir, "processed_med_desc_map.json"), "w", encoding="utf-8") as f:
        json.dump(med_desc_map, f, indent=2, ensure_ascii=False)


def load_processed(data_dir: str):
    """Load processed store_meta, inventory and med_desc_map from data_dir if present.
    Returns (store_meta, inventory, med_desc_map) or (None, None, None)."""
    import json, os
    meta_path = os.path.join(data_dir, "processed_store_meta.json")
    inv_path = os.path.join(data_dir, "processed_inventory.json")
    map_path = os.path.join(data_dir, "processed_med_desc_map.json")
    if not (os.path.exists(meta_path) and os.path.exists(inv_path) and os.path.exists(map_path)):
        return None, None, None
    with open(meta_path, "r", encoding="utf-8") as f:
        store_meta = json.load(f)
    with open(inv_path, "r", encoding="utf-8") as f:
        inventory = json.load(f)
    with open(map_path, "r", encoding="utf-8") as f:
        med_desc_map = json.load(f)
    return store_meta, inventory, med_desc_map

