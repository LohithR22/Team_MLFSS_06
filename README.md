-----

# Medicine Finder Application

This is a backend service designed to find and rank local pharmacies based on a user's location and a list of requested medicines.

It ranks stores by a composite score of **availability**, **price**, and **distance**. A key feature is its ability to use semantic search to find available alternatives for out-of-stock or unlisted items, ensuring the user gets the best possible fulfillment options.

## Features

  * **Location-Based Search:** Finds the `top_k` closest pharmacies to a given latitude and longitude using the Haversine formula.
  * **Composite Ranking:** Ranks the closest stores not just by distance, but by a weighted score of medicine availability (60%), price (25%), and distance (15%).
  * **Intelligent Search:**
      * Finds **exact matches** for requested medicines.
      * If an exact match is unavailable or out-of-stock, it uses **vector-based semantic search** to find the best available alternative (e.g., "CoughRelief" -\> "Relentus").
      * Checks the availability of alternatives, even checking the top-2 best matches before marking an item as "missing."
  * **High-Speed Caching:** On the first run, the application processes the dataset, creates embeddings, and caches all data. All subsequent runs are near-instant, reading from the pre-computed cache.
  * **Logging:** Saves a detailed JSON log of every full request for debugging and analysis.

## How It Works: Application Flow

1.  **Entry Point:** An external application calls `get_medicine_recommendations()` (in `app.py`) with a location and a list of medicine names.
2.  **Data Caching (First Run Only):**
      * The `_load_and_cache_data` function checks for a `medicine_finder/data` folder.
      * If it's not found, `data_loader.py` reads the `final_realistic.csv`, normalizes the data, and builds a medicine-to-description map.
      * `embeddings.py` (using `sentence-transformers`) is loaded and used to create vector embeddings for every item in every store's inventory.
      * The normalized data (`.json`) and embeddings (`.npz`) are saved to `medicine_finder/data/` for future use.
3.  **Data Retrieval (Subsequent Runs):** The cached data and embeddings are loaded directly from the `/data/` folder, which is much faster.
4.  **Core Logic (`find_best_stores`):**
      * **Distance Filtering:** `haversine.py` calculates the distance from the user to *all* stores. (See "Distance Calculation Algorithm" below).
      * The list is sorted by distance to find the `top_k` (e.g., 5) nearest stores.
      * **Fulfillment:** For each of these `k` stores, the app runs the fulfillment logic:
          * **Exact Match:** Tries to find an *available* item with the exact same name.
          * **Alternative Match:** If no exact match is found, `retrieval.py` is called. It uses vector search to find all similar items, sorted by relevance. The app checks the top 2 alternatives, ensuring they are both **above the similarity threshold** and **currently available**.
          * **Missing:** If no available exact or alternative match is found, the item is marked "missing."
5.  **Ranking:**
      * `ranking.py` calculates a composite score for each of the `k` stores. (See "Final Ranking Algorithm" below).
6.  **Output:**
      * The final list of stores is re-sorted by this composite score (best to worst).
      * A full, detailed log is written to the `/logs/` folder.
      * A simple, clean JSON string (as requested) is returned to the calling application.

-----

## Algorithm Descriptions

### Distance Calculation: The Haversine Formula

To find the closest pharmacies, we need to calculate the distance between the user's coordinates and every store's coordinates on the surface of the Earth.

  * **What it is:** The **Haversine formula** is a mathematical equation used to calculate the great-circle distance between two points on a sphere (like the Earth) given their latitudes and longitudes.
  * **Why it's used:** A simple 2D distance formula (like the Pythagorean theorem) is inaccurate for global coordinates because it doesn't account for the Earth's curvature. The Haversine formula provides a highly accurate "as-the-crow-flies" distance.
  * **How it's used here:** The `haversine.py` file contains a `numpy`-optimized function (`haversine_np`). This function takes the user's single (lat, lon) point and efficiently calculates the distance to *all* store locations in the dataset in a single, fast operation.

### Final Ranking Algorithm: How Stores are Scored

The initial `top_k` stores are found using distance, but the *final* list is ranked by a **Composite Score**. This score provides a more "human" answer by balancing three key factors.

The score is a weighted average, with weights defined in `utils.py`:

  * **Availability (60% weight):** How many medicines did the store have?
  * **Price (25% weight):** How does the total price compare to other stores?
  * **Distance (15% weight):** How close is the store?

Here is the breakdown of each sub-score:

#### 1. Availability Score

This score measures how well the store fulfilled the user's request. It gives **1 full point** for **"available"** items and **0.5 points** for **"alternative"** items.

**Formula:**
`Score = ( (Count Available * 1.0) + (Count Alternatives * 0.5) ) / Total Medicines Requested`

#### 2. Price Score

This score rewards stores that are cheaper than the average. It is normalized against the *median* price of all the stores being ranked.

**Formula:**
`Score = 1.0 / (1.0 + (Store Total Price / Median Total Price))`

  * A store with a price cheaper than the median gets a score **above 0.5**.
  * A store with a price more expensive than the median gets a score **below 0.5**.

#### 3. Distance Score

This score simply normalizes the distance to reward closer stores.

**Formula:**
`Score = 1.0 / (1.0 + Distance in km)`

#### Final Composite Score

The app combines these three scores to get the final rank:

**Formula:**
`Final Score = (Availability Score * 0.6) + (Price Score * 0.25) + (Distance Score * 0.15)`

The list of stores is then sorted by this `Final Score` (highest to lowest) and returned to the user.

-----

## Project Structure

This is the required layout for all relative paths to work correctly.

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

1.  **Place Files:** Organize your project exactly as shown in the structure above.

2.  **Create Environment:** Open a terminal in `/Your-Main-Project` and create a virtual environment:

    ```bash
    python -m venv .venv
    ```

3.  **Activate Environment:**

      * **Windows (PowerShell):** `.\.venv\Scripts\Activate`
      * **macOS/Linux:** `source .venv/bin/activate`

4.  **Install Requirements:** Create a `requirements.txt` file in your root directory with the following content, then run `pip install -r requirements.txt`.

    **`requirements.txt`:**

    ```
    pandas
    numpy
    sentence-transformers
    scikit-learn
    pytest
    tqdm
    faiss-cpu
    ```

## How to Run

The system is designed to be imported as a package by your main application.

### Example `main_app.py`

This is all you need to run the application from your main script:

```python
# in main_app.py
from medicine_finder.src.app import get_medicine_recommendations
import json

print("Starting the main application...")

# 1. Define your inputs
lat = 12.91
lon = 77.51
meds_to_find = ["Paracetamol", "Pan D", "CoughRelief", "Aspirin"]

# 2. Call the function
print("Calling medicine finder...")
json_result_string = get_medicine_recommendations(
    source_lat=lat,
    source_lon=lon,
    medicine_names=meds_to_find,
    top_k=3 # This is optional, defaults to 5
)

# 3. Use the result
print("--- Results ---")
result = json.loads(json_result_string)
print(json.dumps(result, indent=2))
print("-----------------")
print("Done.")

```

### First Run vs. Subsequent Runs

  * **First Run:** The first time you execute `main_app.py`, it will take 1-2 minutes. During this time, it is downloading the embedding model, processing the entire CSV, generating all vector embeddings, and saving everything to the `medicine_finder/data` cache.
  * **Subsequent Runs:** Every call after that will be nearly instant, as it reads directly from the pre-computed cache.

## Maintenance: How to Update Your Data

Because the application uses a cache, it will **not** automatically detect changes to your `final_realistic.csv`.

To load new data, you must **delete the cache folder**.

1.  Make all your changes to `final_realistic.csv`.
2.  Delete the **entire `medicine_finder/data` folder**.
3.  Run `main_app.py` again. It will perform a one-time "slow" run to rebuild the cache with your new data.

## Code Explanation (Module-by-Module)

  * `app.py`: Contains the main "API" function `get_medicine_recommendations` that formats input/output. It also has the core logic `find_best_stores` which orchestrates the search-and-rank process.
  * `data_loader.py`: Responsible for parsing the complex CSV, normalizing column names, and creating the critical `med_desc_map` used for semantic search.
  * `embeddings.py`: An abstraction layer for the `sentence-transformers` library. It initializes the model and has helpers to create vectors and cache them to `.npz` files.
  * `retrieval.py`: Performs the vector math. `find_best_alternatives_sorted` uses `numpy.dot()` to find the cosine similarity between the query vector and all item vectors in a store.
  * `ranking.py`: Contains the `compute_scores` function, which implements the weighted scoring logic.
  * `haversine.py`: A `numpy`-optimized function to quickly calculate the Haversine distance from one point to an array of many other points.
  * `utils.py`: Contains the `DEFAULT_CONFIG` (where you can change weights and thresholds) and helper functions like `ensure_data_dir` and `ensure_log_dir`.

  UPdate the algorithm part in the readme (See <attachments> above for file contents. You may not need to search or read the file again.)
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