import pandas as pd
import difflib
import os

def janaushadhi_lookup(medicine_list, csv_path="Product List_6_11_2025 @ 15_1_15.csv"):
    """
    Perform Jan Aushadhi medicine price lookup and return nearby clinic information.

    Parameters
    ----------
    medicine_list : list[str]
        List of medicine names to look up.
    csv_path : str
        Path to the CSV file containing medicine name and price data.

    Returns
    -------
    tuple (pandas.DataFrame, list[dict])
        - DataFrame: columns ['Medicine', 'Matched_Name', 'Price', 'Vendor']
        - List of dicts: [{'name', 'address', 'lat', 'lon'}] for Jan Aushadhi clinics.
    """

    # --- Load the CSV safely ---
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        df = pd.read_csv(csv_path, encoding="latin1")

    # --- Identify key columns automatically ---
    name_col = None; price_col = None; vendor_col = None
    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in ["product", "product name", "name", "medicine", "item", "title"]) and not name_col:
            name_col = c
        if any(k in cl for k in ["price", "mrp", "rate", "amount"]) and not price_col:
            price_col = c
        if any(k in cl for k in ["vendor", "seller", "store", "shop", "source"]) and not vendor_col:
            vendor_col = c

    if name_col is None:
        raise ValueError("Could not find a product/medicine name column in the CSV file.")

    candidates = df[name_col].astype(str).tolist()

    # --- Perform fuzzy match & price lookup ---
    results = []
    for med in medicine_list:
        matches = difflib.get_close_matches(med, candidates, n=5, cutoff=0.5)

        if matches:
            best = None
            for m in matches:
                idx = candidates.index(m)
                price_val = None
                vendor_val = None
                if price_col and price_col in df.columns:
                    try:
                        price_val = float(str(df.at[idx, price_col]).replace(",", "").strip())
                    except Exception:
                        price_val = None
                if vendor_col and vendor_col in df.columns:
                    vendor_val = str(df.at[idx, vendor_col])

                # Pick the lowest valid price
                if best is None or (price_val is not None and (best["price"] is None or price_val < best["price"])):
                    best = {"match_name": m, "price": price_val, "vendor": vendor_val}

            if best is None:
                best = {"match_name": matches[0], "price": None, "vendor": None}

            results.append({
                "Medicine": med,
                "Matched_Name": best["match_name"],
                "Price": f"₹{best['price']:.2f}" if best["price"] is not None else "N/A",
                "Vendor": best.get("vendor") or ""
            })
        else:
            results.append({"Medicine": med, "Matched_Name": "", "Price": "Not found", "Vendor": ""})

    df_results = pd.DataFrame(results)

    # --- Jan Aushadhi clinic info (from app12.py) ---
    jan_aushadhi_clinics = [
        {
            "name": "Pradhan Mantri JanAushadhi Kendra - Gokhale Rd",
            "address": "921, Gokhale Rd, Rajarajeshwari Nagar, Bengaluru 560098",
            "lat": 12.917612214940876,
            "lon": 77.51904488091897
        },
        {
            "name": "Pradhan Mantri Janaushadhi Kendra - BHEL 2nd Stage",
            "address": "Sir M Vishnuvardhan Main Rd, Rajarajeshwari Nagar, Bengaluru 560098",
            "lat": 12.917612214940876,
            "lon": 77.50978399033598
        },
        {
            "name": "Pradhan Mantri Jan Aushadhi Kendra - Kenchena Halli Rd",
            "address": "17 ground floor, Kenchena Halli Rd, Rajarajeshwari Nagar, Bengaluru 560098",
            "lat": 12.910492603965448,
            "lon": 77.51343617253772
        },
        {
            "name": "PRADHAN MANTRI BHARTIYA JANAUSHADHI KENDRA - Channasandra",
            "address": "No 851, Dr.Vishnuvardhan Rd, Channasandra, Bengaluru 560098",
            "lat": 12.903563502133089,
            "lon": 77.52067531940189
        },
        {
            "name": "Pradhan mantri Janaushadhi kendra - Kodipalya",
            "address": "Shop No.F4, Vasthu Green Shopping Complex, Kodipalya, Bengaluru, Karnataka 560060",
            "lat": 12.906666049048614,
            "lon": 77.48845393143118
        },
        {
            "name": "Pradhan Mantri Bhartiya Jan Aushadhi Kendra Kengeri",
            "address": "Kengeri, Bengaluru, Karnataka 560060",
            "lat": 12.915871335395288,
            "lon": 77.4804822691128
        }
    ]

    return df_results, jan_aushadhi_clinics
