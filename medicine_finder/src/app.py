"""Main application logic and CLI wrapper."""
from typing import List, Dict, Any, Optional
import os
import numpy as np
import json 
import datetime 
from .data_loader import load_and_normalize, load_processed, save_processed
from .haversine import haversine_np
from .embeddings import init_model, embed_texts, cache_embeddings, load_cached_embeddings
from .retrieval import find_best_alternatives_sorted
from .ranking import compute_scores
from .utils import DEFAULT_CONFIG, ensure_data_dir, ensure_log_dir


# --- Global caches to hold data after first load ---
_store_meta_cache = None
_inventory_cache = None
_store_embeddings_map_cache = None
_store_items_map_cache = None
_med_desc_map_cache = None 


def _load_and_cache_data(cfg, csv_path, dry_run):
    """Internal helper to load, embed, and cache data ONCE."""
    global _store_meta_cache, _inventory_cache, _store_embeddings_map_cache, _store_items_map_cache, _med_desc_map_cache

    # 1. If cache is already populated, return it instantly
    if _store_meta_cache is not None:
        return _store_meta_cache, _inventory_cache, _store_embeddings_map_cache, _store_items_map_cache, _med_desc_map_cache

    # --- 2. Prepare data folder (CHANGED) ---
    # Path is now ../ from /src/app.py -> .../medicine_finder/
    base_data_dir = os.path.join(os.path.dirname(__file__), "..")
    cache_dir = ensure_data_dir(base_data_dir) # This will create/use .../medicine_finder/data/

    # 3. Try to load processed (normalized) store_meta & inventory
    store_meta, inventory, med_desc_map = load_processed(cache_dir)
    if store_meta is None or inventory is None or med_desc_map is None:
        # process from CSV and then save processed for future runs
        store_meta, inventory, med_desc_map = load_and_normalize(csv_path)
        try:
            save_processed(cache_dir, store_meta, inventory, med_desc_map)
        except Exception:
            pass # non-fatal
    
    # 4. Init model
    provider = cfg.get("EMB_PROVIDER", "dummy")
    model_name = cfg.get("EMB_MODEL_NAME", "all-MiniLM-L6-v2")
    init_model(provider=provider, model_name=model_name)

    # 5. Precompute embedding caches per store
    store_embeddings_map = {}
    store_items_map = {}
    for sid, items in inventory.items():
        texts = [ (it.get("medicine_name", "") + " " + (it.get("medicine_desc") or "")).strip() for it in items]
        cache_path = os.path.join(cache_dir, f"emb_cache_{sid}.npz")
        keys, embs = load_cached_embeddings(cache_path)
        if keys is None:
            if dry_run:
                embs = np.zeros((len(texts), 32))
            else:
                embs = embed_texts(texts)
            cache_embeddings(cache_path, [it.get("medicine_id") for it in items], embs)
        store_embeddings_map[sid] = embs
        store_items_map[sid] = items

    # 6. Save to global cache
    _store_meta_cache = store_meta
    _inventory_cache = inventory
    _store_embeddings_map_cache = store_embeddings_map
    _store_items_map_cache = store_items_map
    _med_desc_map_cache = med_desc_map
    
    # --- 7. (FIX) Explicitly return the tuple ---
    return store_meta, inventory, store_embeddings_map, store_items_map, med_desc_map


def find_best_stores(source_lat: float,
                     source_lon: float,
                     requested_meds: List[Dict[str, Any]],
                     csv_path: Optional[str] = None,
                     top_k: int = 5,
                     config: Optional[Dict[str, Any]] = None,
                     dry_run: bool = False) -> Dict[str, Any]:
    """
    Core logic engine. Finds best stores.
    """
    cfg = DEFAULT_CONFIG.copy()
    if config:
        cfg.update(config)

    # --- Path logic (CHANGED) ---
    # Default CSV path is ../../ from /src/app.py -> .../final_realistic.csv
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "final_realistic.csv")

    # This call uses the cache, so it's fast after the first run.
    store_meta, inventory, store_embeddings_map, store_items_map, med_desc_map = _load_and_cache_data(
        cfg, csv_path, dry_run
    )

    # compute distances to stores
    store_ids = list(store_meta.keys())
    lats = [store_meta[sid]["latitude"] for sid in store_ids]
    lons = [store_meta[sid]["longitude"] for sid in store_ids]
    dists = haversine_np(source_lat, source_lon, lats, lons)

    # collect store summary list
    stores_summary = []
    for sid, dist in zip(store_ids, dists):
        stores_summary.append({
            "store_id": sid,
            "store_name": store_meta[sid].get("store_name"),
            "distance_km": float(dist),
            "latitude": store_meta[sid].get("latitude"),
            "longitude": store_meta[sid].get("longitude"),
        })

    # sort by distance and pick nearest top_k
    stores_sorted = sorted(stores_summary, key=lambda x: x["distance_km"])[:top_k]

    results = []
    total_prices = []
    for s in stores_sorted:
        sid = s["store_id"]
        items = store_items_map.get(sid, [])
        embs = store_embeddings_map.get(sid, np.zeros((0, 0)))
        
        store_res = {
            "store_id": sid,
            "store_name": s["store_name"],
            "distance_km": s["distance_km"],
            "latitude": s.get("latitude"), 
            "longitude": s.get("longitude"), 
            "counts": {"available": 0, "alternatives": 0, "missing": 0},
            "items": [],
            "total_price": 0.0,
            "total_requested": len(requested_meds),
        }

        # helper index maps for exact matches
        name_to_items = {}
        id_to_items = {}
        for it in items:
            name_to_items.setdefault((it.get("medicine_name", "") or "").lower(), []).append(it)
            id_to_items.setdefault(it.get("medicine_id"), []).append(it)

        for req in requested_meds:
            req_name = (req.get("name") or "").strip()
            req_id = req.get("medicine_id")
            entry = {"requested": {"name": req_name, "id": req_id}, "status": "missing", "matched_item": None, "price_used": None}

            # exact match by id or name
            match_item = None
            if req_id and req_id in id_to_items:
                cand = sorted(id_to_items[req_id], key=lambda x: ((not x.get("availability", False)), x.get("price", float("inf"))))[0]
                if cand.get("availability", False):
                    match_item = cand
            if match_item is None and req_name:
                cands = name_to_items.get(req_name.lower(), [])
                if cands:
                    cand = sorted(cands, key=lambda x: ((not x.get("availability", False)), x.get("price", float("inf"))))[0]
                    if cand.get("availability", False):
                        match_item = cand

            if match_item is not None:
                entry["status"] = "available"
                entry["matched_item"] = match_item
                entry["price_used"] = float(match_item.get("price", 0.0))
                store_res["counts"]["available"] += 1
                store_res["total_price"] += entry["price_used"]
            else:
                # try alternative via embeddings
                if dry_run:
                    entry["status"] = "missing"
                    store_res["counts"]["missing"] += 1
                else:
                    # Use name + description from map
                    req_name_lower = req_name.lower()
                    desc_from_map = med_desc_map.get(req_name_lower, "")
                    text = (req_name + " " + desc_from_map).strip()

                    if not text:
                        entry["status"] = "missing"
                        store_res["counts"]["missing"] += 1
                    else:
                        # --- THIS IS THE NEW LOGIC ---
                        q_emb = embed_texts([text])[0]
                        
                        # 1. Get all sorted alternatives
                        sorted_indices, sorted_sims = find_best_alternatives_sorted(q_emb, embs)
                        
                        found_match = False
                        
                        # 2. Iterate through top 2 (or fewer if less than 2 results)
                        for i in range(min(2, len(sorted_indices))):
                            idx = sorted_indices[i]
                            sim = sorted_sims[i]
                            
                            # Check similarity threshold
                            if sim < cfg.get("ALT_SIM_THRESHOLD", 0.75):
                                # Stop checking if similarity is too low
                                break 
                            
                            alt = items[idx]
                            
                            # Check availability
                            if alt.get("availability", False):
                                entry["status"] = "alternative"
                                entry["matched_item"] = alt
                                entry["similarity"] = float(sim)
                                entry["price_used"] = float(alt.get("price", 0.0))
                                store_res["counts"]["alternatives"] += 1
                                store_res["total_price"] += entry["price_used"]
                                found_match = True
                                # Found a good, available match. Stop iterating.
                                break 

                        # 3. If no match was found after checking top 2
                        if not found_match:
                            entry["status"] = "missing"
                            store_res["counts"]["missing"] += 1
                        # --- END NEW LOGIC ---

            # price jump flag
            if entry.get("status") == "alternative" and entry.get("matched_item"):
                req_est_price = req.get("expected_price")
                if req_est_price and entry["price_used"] > 1.5 * float(req_est_price):
                    entry["price_jump"] = True

            store_res["items"].append(entry)

        total_prices.append(store_res["total_price"] if store_res["total_price"] > 0 else 0.0)
        results.append(store_res)

    # compute avg price reference
    avg_price_ref = float(np.median(total_prices)) if len(total_prices) > 0 else 1.0

    # compute composite scores
    for r in results:
        composite, breakdown = compute_scores(r, avg_price_ref, cfg.get("WEIGHTS", {}))
        r["composite_score"] = composite
        r["score_breakdown"] = breakdown

    # final sort by composite score desc
    final_sorted = sorted(results, key=lambda x: x["composite_score"], reverse=True)

    out = {
        "source": {"lat": source_lat, "lon": source_lon},
        "requested": requested_meds,
        "top_stores": final_sorted,
    }
    return out


def get_medicine_recommendations(source_lat: float, 
                                 source_lon: float, 
                                 medicine_names: List[str], 
                                 top_k: int = 5) -> str:
    """
    Main public entry point for the application.
    """
    
    # 1. Convert simple list of names to the dict format our core logic needs
    requested_meds_list = [{"name": name} for name in medicine_names]
    
    # 2. Call the core logic function
    full_result = find_best_stores(
        source_lat=source_lat,
        source_lon=source_lon,
        requested_meds=requested_meds_list,
        top_k=top_k,
        config=None, 
        dry_run=False
    )
    
    # --- 3. Handle Logging (CHANGED) ---
    try:
        # Log directory in the project root (../.. from /src/app.py)
        base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
        log_dir = ensure_log_dir(base_dir) # This will create/use .../logs/
        
        ts = datetime.datetime.now().isoformat().replace(":", "-").split(".")[0]
        log_file = os.path.join(log_dir, f"result_{ts}.json")
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(full_result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to write log file - {e}")

    # 4. Format the simplified output as requested
    simplified_stores = []
    for store in full_result.get("top_stores", []):
        
        medicine_status = {
            "available": [],
            "alternative": [],
            "missing": []
        }
        for item in store.get("items", []):
            req_name = item.get("requested", {}).get("name")
            status = item.get("status")
            if status == "available":
                medicine_status["available"].append(req_name)
            elif status == "alternative":
                matched_name = item.get("matched_item", {}).get("medicine_name")
                medicine_status["alternative"].append({
                    "requested": req_name,
                    "found": matched_name
                })
            else:
                medicine_status["missing"].append(req_name)
                
        simplified_stores.append({
            "store_name": store.get("store_name"),
            "latitude": store.get("latitude"),
            "longitude": store.get("longitude"),
            "distance_from_source": store.get("distance_km"),
            "total_price": store.get("total_price"),
            "medicine_status": medicine_status
        })
        
    final_output = {
        "source_location": full_result.get("source"),
        "ranked_stores": simplified_stores
    }

    # 5. Return as a JSON string
    return json.dumps(final_output, indent=2, ensure_ascii=False)


def _cli():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Find best stores for medicines")
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--meds-file", type=str, required=True, help="JSON file with list of *just* medicine names")
    
    # --- (CHANGED) Corrected default path ---
    parser.add_argument("--csv", type=str, default=os.path.join(os.path.dirname(__file__), "..", "..", "final_realistic.csv"))
    
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true") # Keep dry-run for core logic

    args = parser.parse_args()
    with open(args.meds_file, "r", encoding="utf-8") as f:
        # Assuming file is like ["Paracetamol", "Pan D"]
        med_names = json.load(f) 
        
    # Call the new wrapper function
    res_json_string = get_medicine_recommendations(
        args.lat, 
        args.lon, 
        med_names, 
        top_k=args.top_k
        # Note: The CLI doesn't use dry_run with get_medicine_recommendations,
        # but you could add it back by modifying the wrapper if needed.
    )
    print(res_json_string)


if __name__ == "__main__":
    _cli()