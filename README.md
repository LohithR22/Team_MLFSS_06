# Medicine Finder

This backend service finds and ranks local pharmacies based on a user's location and a list of requested medicines.

It ranks stores by a composite score of availability, price, and distance. A key feature is its ability to use semantic search to find available alternatives for out-of-stock or unlisted items, ensuring the user gets the best possible fulfillment options.

## Features
- Location-Based Search: Finds the top_k closest pharmacies to a given latitude and longitude.
- Composite Ranking: Ranks the closest stores not just by distance, but by a weighted score of medicine availability (60%), price (25%), and distance (15%).
- Intelligent Search:
	- Finds exact matches for requested medicines.
	- If an exact match is unavailable or out-of-stock, it uses vector-based semantic search to find the best available alternative (e.g., "CoughRelief" -> "Relentus").
	- Checks the availability of alternatives, even checking the top-2 best matches before marking an item as "missing." 
- High-Speed Caching: On first run the app processes the dataset, creates embeddings, and caches all data. Subsequent runs read from the pre-computed cache for near-instant response.
- Logging: Saves a detailed JSON log of every full request for debugging and analysis.

## How It Works (Application Flow)

1. Entry Point: An external application calls `get_medicine_recommendations()` (in `app.py`) with a location and a list of medicine names.

2. Data Caching (First Run Only):
	 - `_load_and_cache_data` checks for a `medicine_finder/data` folder.
	 - If not found, `data_loader.py` reads `final_realistic.csv`, normalizes the data, and builds a medicine-to-description map.
	 - `embeddings.py` (using `sentence-transformers`) is loaded and used to create vector embeddings for every item in every store's inventory.
	 - The normalized data (`.json`) and embeddings (`.npz`) are saved to `medicine_finder/data/` for future use.

3. Data Retrieval (Subsequent Runs): Cached data and embeddings are loaded directly from the `/data/` folder (fast).

4. Core Logic (`find_best_stores`):
	 - `haversine.py` calculates distance from the user to all stores.
	 - The list is sorted by distance to find the top_k nearest stores.
	 - For each store, the app runs fulfillment logic:
		 - Exact Match: finds an available item by exact name.
		 - Alternative Match: if no exact match, `retrieval.py` performs a vector search returning items sorted by similarity. The app checks the top 2 alternatives, ensuring they are above the similarity threshold and available.
		 - Missing: if none found, the item is marked "missing." 

5. Ranking: `ranking.py` calculates a composite score for each store based on availability, price, and distance.

6. Output: The final store list is resorted by composite score (best to worst), a detailed log is written to `/logs/`, and a simple JSON string is returned.

## Project Structure
Place and run the project with the following layout so relative paths work as expected:

```
/Your-Main-Project/
├── main_app.py                 <-- Your main application script
├── final_realistic.csv         <-- Your data (MUST be in the root)
├── requirements.txt            <-- The file with all dependencies
│
├── logs/                       <-- Logs are created here
│   └── result_...json
│
└── medicine_finder/            <-- The complete application package
		├── __init__.py
		├── data/                   <-- Cache & embeddings are created here
		│   ├── processed_store_meta.json
		│   ├── processed_med_desc_map.json
		│   ├── emb_cache_...npz
		│   └── ...
		└── src/                    <-- All source code
				├── __init__.py
				├── app.py              (Main logic and API function)
				├── data_loader.py      (CSV parsing and data caching)
				├── embeddings.py       (Handles the ML model)
				├── haversine.py        (Distance calculation)
				├── ranking.py          (Scoring logic)
				├── retrieval.py        (Vector search logic)
				└── utils.py            (Configuration and path helpers)
```

## Setup & Installation
1. Place files: Organize your project exactly as shown above.

2. Create environment: In the project root run:

```powershell
python -m venv .venv
```

Activate environment:

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install requirements: Create a `requirements.txt` in your root with these packages and run `pip install -r requirements.txt`:

```
pandas
numpy
sentence-transformers
scikit-learn
pytest
```

## How to Run
The library is designed to be imported by your main script. Example `main_app.py`:

```python
from medicine_finder.src.app import get_medicine_recommendations
import json

lat = 12.91
lon = 77.51
meds_to_find = ["Paracetamol", "Pan D", "CoughRelief", "Aspirin"]

json_result_string = get_medicine_recommendations(
		source_lat=lat,
		source_lon=lon,
		medicine_names=meds_to_find,
		top_k=3
)

result = json.loads(json_result_string)
print(json.dumps(result, indent=2))
```

### First Run vs. Subsequent Runs
- First Run: Will take longer (model download + CSV processing + embedding generation). Expect ~1–2 minutes depending on machine and network.
- Subsequent Runs: Near-instant because the app uses the cached data in `medicine_finder/data/`.

To refresh data, delete the `medicine_finder/data/` folder and re-run the script.

## Module Overview
- `app.py`: main API function `get_medicine_recommendations` and `find_best_stores` core logic.
- `data_loader.py`: CSV parsing and med-description map creation.
- `embeddings.py`: model initialization and embedding helpers (uses `sentence-transformers`).
- `retrieval.py`: vector search helpers. `find_best_alternatives_sorted` returns items sorted by cosine similarity.
- `ranking.py`: computes composite scores (Availability 60%, Price 25%, Distance 15%).
- `haversine.py`: fast distance calculations using numpy.
- `utils.py`: `DEFAULT_CONFIG` and helpers like `ensure_data_dir` and `ensure_log_dir`.

## Notes
- The `EMB_PROVIDER` in `DEFAULT_CONFIG` can be switched to `sentence-transformers` to enable real semantic search. Ensure you have `sentence-transformers` installed.
- The number of alternative candidates checked is currently hard-coded to 2 in `app.py` (this can be made configurable via `DEFAULT_CONFIG`).

## Troubleshooting
- If you change `final_realistic.csv`, delete `medicine_finder/data/` before running again so caches are rebuilt.
- If embedding model initialization fails, check that `sentence-transformers` is installed and that your environment has internet access to download the model on first run.

---