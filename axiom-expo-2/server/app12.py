# app11.py
"""
Updated app11.py — duplicate Streamlit button IDs fixed (unique keys).
Jan Aushadhi list can be provided programmatically via st.session_state["medicines_list"]
or pasted in the Jan tile. CSV price lookup uses CSV_PATH placed in project root.
Map & agent assignment functionality preserved.
"""

import streamlit as st
import folium
from folium import IFrame, Popup
from branca.element import Element
import requests, random, json, os, math
from urllib.parse import quote_plus
from streamlit.components.v1 import html as st_html
import pandas as pd
import difflib

# ---------- Config ----------
OSRM_SERVER = "https://router.project-osrm.org"
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTR = "© OpenStreetMap contributors"
YELLOW_SHADES = ["#E0A800", "#FFD43B", "#FFEB99"]
PURPLE_HEX = "#800080"
BLUE_GOV_COLOR = "blue"
MATCH_RADIUS_METERS = 50.0

CSV_PATH = "Product List_6_11_2025 @ 15_1_15.csv"  # Price CSV (put in project root)

# ---------- Hardcoded agents, shops, and gov clinics ----------
HIDDEN_AGENTS_COORDS = [
    (12.9650, 77.6000),
    (12.9800, 77.5900),
    (12.9550, 77.6050),
    (12.9750, 77.6100),
    (12.9900, 77.5800)
]
AGENT_PROFILES = [
    {"name": "Ravi Kumar", "phone": "+91-98765-00001", "vehicle": "Bike - KTM Duke"},
    {"name": "Asha Devi", "phone": "+91-98765-00002", "vehicle": "Scooter - TVS Jupiter"},
    {"name": "Suresh N", "phone": "+91-98765-00003", "vehicle": "Bike - Hero Splendor"},
    {"name": "Priya R", "phone": "+91-98765-00004", "vehicle": "Scooter - Honda Activa"},
    {"name": "Manoj K", "phone": "+91-98765-00005", "vehicle": "Bike - Yamaha FZ"}
]

SHOP_DATABASE = [
    {"name": "MedPlus Rajarajeshwari Nagar", "latlon": (12.9260174804538, 77.51873873639585)},
    {"name": "MedPLus RR Nagar, Kenchenahalli Road", "latlon": (12.916062252168635, 77.51315974188867)},
    {"name": "MedPlus RR Nagar, 60 Feet Road", "latlon": (12.912046585611204, 77.52105616488345)},
    {"name": "Apollo Pharmacy Kenchenahalli Road, RR Nagar", "latlon": (12.910958998147274, 77.51350306462756)},
    {"name": "Lakshmi Pharma", "latlon": (12.900447828509314, 77.5096368705969)},
    {"name": "Omkar Medicals and General Store", "latlon": (12.907003244263793, 77.5049541035601)},
    {"name": "Be Well Drugs", "latlon": (12.909722477406175, 77.50923833723208)},
    {"name": "Krishna Medicals and Departmental Stores", "latlon": (12.907120961825331, 77.49881980852739)}
]

GOV_INITIATIVES = [
    {"name":"Pradhan Mantri JanAushadhi Kendra - Gokhale Rd",
     "address":"921, Gokhale Rd, Rajarajeshwari Nagar, Bengaluru 560098",
     "latlon": (12.917612214940876, 77.51904488091897)},
    {"name":"Pradhan Mantri Janaushadhi Kendra - BHEL 2nd Stage",
     "address":"Sir M Vishnuvardhan Main Rd, Rajarajeshwari Nagar, Bengaluru 560098",
     "latlon": (12.917612214940876, 77.50978399033598)},
    {"name":"Pradhan Mantri Jan Aushadhi Kendra - Kenchena Halli Rd",
     "address":"17 ground floor, Kenchena Halli Rd, Rajarajeshwari Nagar, Bengaluru 560098",
     "latlon": (12.910492603965448, 77.51343617253772)},
    {"name":"PRADHAN MANTRI BHARTIYA JANAUSHADHI KENDRA - Channasandra",
     "address":"No 851, Dr.Vishnuvardhan Rd, Channasandra, Bengaluru 560098",
     "latlon": (12.903563502133089, 77.52067531940189)},
    {"name":"Pradhan mantri Janaushadhi kendra - Kodipalya",
     "address":"Shop No.F4, Vasthu Green Shopping Complex, Kodipalya, Bengaluru, Karnataka 560060",
     "latlon": (12.906666049048614, 77.48845393143118)},
    {"name":"Pradhan Mantri Bhartiya Jan Aushadhi Kendra Kengeri",
     "address":"Kengeri, Bengaluru, Karnataka 560060",
     "latlon": (12.915871335395288, 77.4804822691128)}
]

# ---------- Streamlit page ----------
st.set_page_config(page_title="Delivery Map — Jan Aushadhi & Agents", layout="wide")
st.markdown("<h2 style='margin:0'>Delivery Map — Jan Aushadhi & Agents</h2>", unsafe_allow_html=True)
st.write("Sidebar: use the Jan Aushadhi button to view Jan Aushadhi tile. Map is shown on the right and is preserved unless regenerated.")

# ---------- WHERE TO PASS TABLET NAMES (EXPLICIT) ----------
# Option A (programmatic): set the list from another script/cell before rendering.
#   Example (uncomment to test / programmatically provide):
# st.session_state["medicines_list"] = ["Dolo 650", "Paracetamol", "Pantoprazole"]
#
# Option B (UI): leave session key absent and paste names in the Jan Aushadhi tile textarea (newline, comma-separated, or Python list literal).
#
# The Jan tile will prefer st.session_state["medicines_list"] if present.

# ---------- helpers ----------
def parse_coord(txt: str):
    p = [s.strip() for s in txt.split(",")]
    return (float(p[0]), float(p[1]))

def haversine_m(a, b):
    R = 6371000.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    x = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(x))

def google_maps_link(origin, dest):
    params = {"api":"1","origin":f"{origin[0]},{origin[1]}","destination":f"{dest[0]},{dest[1]}","travelmode":"driving"}
    return "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())

def get_osrm_route(src, dst, profile="driving"):
    coords_str = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        geom = route["geometry"]["coordinates"]
        coords_latlon = [[c[1], c[0]] for c in geom]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception:
        return None, None, None

def make_popup_html(title, point, dist_m=None, dur_s=None, gm_link=None, extra_html=""):
    lines = [f"<b>{title}</b>", f"{point[0]:.6f}, {point[1]:.6f}"]
    if dist_m is not None:
        lines.append(f"Distance: {dist_m/1000.0:.2f} km")
    if dur_s is not None:
        lines.append(f"ETA: {int(dur_s/60)} min")
    if gm_link:
        lines.append(f"<a href='{gm_link}' target='_blank'>Open in Google Maps</a>")
    if extra_html:
        lines.append(extra_html)
    return IFrame("<br>".join(lines), width=320, height=140)

# ---------- session ----------
if "map_html" not in st.session_state:
    st.session_state["map_html"] = None
if "assignments" not in st.session_state:
    st.session_state["assignments"] = []
if "medicines" not in st.session_state:
    st.session_state["medicines"] = []
if "csv_df" not in st.session_state:
    st.session_state["csv_df"] = None
if "csv_cols" not in st.session_state:
    st.session_state["csv_cols"] = None
if "show_jana" not in st.session_state:
    st.session_state["show_jana"] = False
# medicines_list is the place we prefer (user can set it programmatically):
if "medicines_list" not in st.session_state:
    st.session_state["medicines_list"] = None

# ---------- load CSV & fuzzy match helpers ----------
def load_price_csv(path=CSV_PATH):
    if not os.path.exists(path):
        return None, None
    try:
        df = pd.read_csv(path)
    except Exception:
        try:
            df = pd.read_csv(path, encoding="latin1")
        except Exception:
            return None, None
    name_col = None; price_col = None; vendor_col = None
    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in ["product","product name","name","medicine","item","title"]) and not name_col:
            name_col = c
        if any(k in cl for k in ["price","mrp","rate","amount"]) and not price_col:
            price_col = c
        if any(k in cl for k in ["vendor","seller","store","shop","source"]) and not vendor_col:
            vendor_col = c
    return df, {"name":name_col,"price":price_col,"vendor":vendor_col}

def find_best_price_info(med_name, df, cols_map, top_n=3):
    if df is None or cols_map is None or cols_map.get("name") is None:
        return []
    name_col = cols_map["name"]; price_col = cols_map.get("price"); vendor_col = cols_map.get("vendor")
    candidates = df[name_col].astype(str).tolist()
    matches = difflib.get_close_matches(med_name, candidates, n=top_n, cutoff=0.5)
    results = []
    for m in matches:
        idx = candidates.index(m)
        price_val = None
        vendor_val = None
        if price_col and price_col in df.columns:
            try:
                price_val = float(str(df.at[idx, price_col]).replace(",","").strip())
            except Exception:
                price_val = None
        if vendor_col and vendor_col in df.columns:
            vendor_val = str(df.at[idx, vendor_col])
        results.append({"match_name": m, "price": price_val, "vendor": vendor_val})
    if not results:
        # fallback substring
        q = med_name.lower()
        for i, cand in enumerate(candidates):
            if q in cand.lower():
                pv = None; vv = None
                if price_col and price_col in df.columns:
                    try:
                        pv = float(str(df.at[i, price_col]).replace(",","").strip())
                    except Exception:
                        pv = None
                if vendor_col and vendor_col in df.columns:
                    vv = str(df.at[i, vendor_col])
                results.append({"match_name": df.at[i, name_col], "price": pv, "vendor": vv})
    return results

# load CSV if present
if os.path.exists(CSV_PATH):
    df_prices, cols_map = load_price_csv(CSV_PATH)
    st.session_state["csv_df"] = df_prices
    st.session_state["csv_cols"] = cols_map
else:
    st.session_state["csv_df"] = None
    st.session_state["csv_cols"] = None

# ---------- Sidebar: navigation ----------
st.sidebar.header("Navigation")

# Add explicit Jan Aushadhi button (bold) and Show Map button — unique keys
if st.sidebar.button("**Jan Aushadhi**", key="btn_jana"):
    st.session_state["show_jana"] = True
if st.sidebar.button("Show Map", key="btn_show_map"):
    st.session_state["show_jana"] = False

st.sidebar.markdown("---")
st.sidebar.markdown("Map controls (optional) — regenerate map to update preserved view.")

# Sidebar: origin & manual stores (optional inputs)
st.sidebar.markdown("### Map inputs (optional)")
origin_input = st.sidebar.text_input("Origin (lat, lon)", value="12.9716, 77.5946", key="sid_origin")
st.sidebar.markdown("Green stores (optional)")
g1 = st.sidebar.text_input("Green 1", "", key="sid_g1")
g2 = st.sidebar.text_input("Green 2", "", key="sid_g2")
st.sidebar.markdown("Yellow stores (optional)")
y1 = st.sidebar.text_input("Yellow 1", "", key="sid_y1")
y2 = st.sidebar.text_input("Yellow 2", "", key="sid_y2")
y3 = st.sidebar.text_input("Yellow 3", "", key="sid_y3")
st.sidebar.markdown("Red stores (optional)")
r1 = st.sidebar.text_input("Red 1", "", key="sid_r1")
r2 = st.sidebar.text_input("Red 2", "", key="sid_r2")

def safe_parse(txt):
    try:
        if not txt or not txt.strip():
            return None
        return parse_coord(txt)
    except Exception:
        return None

origin = safe_parse(origin_input)
manual_greens = [c for c in [safe_parse(g1), safe_parse(g2)] if c]
manual_yellows = [c for c in [safe_parse(y1), safe_parse(y2), safe_parse(y3)] if c]
manual_reds = [c for c in [safe_parse(r1), safe_parse(r2)] if c]

# ---------- Map build function ----------
def build_map(origin, greens, yellows, reds, govs, assignments):
    m = folium.Map(location=origin or (12.9716,77.5946), zoom_start=13, tiles=TILE_URL, attr=ATTR)
    if origin:
        folium.Marker(location=origin, icon=folium.Icon(color="blue", icon="home"),
                      popup=Popup(make_popup_html("Origin", origin), max_width=300)).add_to(m)
    def add_marker(coord, color, title):
        folium.Marker(location=coord, icon=folium.Icon(color=color),
                      popup=Popup(make_popup_html(title, coord), max_width=300)).add_to(m)
    for c in reds:
        add_marker(c, "darkred", "Red store")
        coords, _, _ = get_osrm_route(origin, c) if origin else (None,None,None)
        if coords:
            folium.PolyLine(coords, color="darkred", weight=4, opacity=0.6).add_to(m)
        else:
            folium.PolyLine([origin, c], color="darkred", weight=3, opacity=0.4, dash_array="5,5").add_to(m)
    for idx,c in enumerate(yellows):
        color = YELLOW_SHADES[min(idx, len(YELLOW_SHADES)-1)]
        add_marker(c, "lightgray", "Yellow store")
        coords, _, _ = get_osrm_route(origin, c) if origin else (None,None,None)
        if coords:
            folium.PolyLine(coords, color=color, weight=4, opacity=0.6).add_to(m)
        else:
            folium.PolyLine([origin, c], color=color, weight=3, opacity=0.4, dash_array="5,5").add_to(m)
    for c in greens:
        add_marker(c, "green", "Green store")
        coords, _, _ = get_osrm_route(origin, c) if origin else (None,None,None)
        if coords:
            folium.PolyLine(coords, color="green", weight=5, opacity=0.7).add_to(m)
        else:
            folium.PolyLine([origin, c], color="green", weight=4, opacity=0.45, dash_array="5,5").add_to(m)
    for i,g in enumerate(govs):
        coord = g["latlon"]
        popup_html = f"<b>{g['name']}</b><br/>{g['address']}<br/><a href='{google_maps_link(origin, coord)}' target='_blank'>Directions</a>"
        folium.Marker(location=coord, icon=folium.Icon(color="blue", icon="info-sign"),
                      popup=Popup(IFrame(popup_html, width=320, height=140))).add_to(m)
    for a in st.session_state["assignments"]:
        agent = a["agent_coord"]
        store = a["store_coord"]
        prof = a["agent_profile"]
        folium.Marker(location=agent, icon=folium.Icon(color="purple"),
                      popup=Popup(IFrame(f"<b>{prof['name']}</b><br/>{prof['phone']}<br/>{prof['vehicle']}", width=220, height=90))).add_to(m)
        if a.get("coords_agent_store"):
            folium.PolyLine(a["coords_agent_store"], color=PURPLE_HEX, weight=5, opacity=0.9).add_to(m)
        else:
            folium.PolyLine([agent, store], color=PURPLE_HEX, weight=4, opacity=0.8, dash_array="3,6").add_to(m)
        if a.get("coords_store_origin"):
            folium.PolyLine(a["coords_store_origin"], color=PURPLE_HEX, weight=7, opacity=0.95).add_to(m)
        else:
            folium.PolyLine([store, origin], color=PURPLE_HEX, weight=6, opacity=0.9, dash_array="3,6").add_to(m)
    all_pts = []
    if origin: all_pts.append(origin)
    all_pts += greens + yellows + reds + [g["latlon"] for g in govs] + HIDDEN_AGENTS_COORDS
    try:
        lats = [p[0] for p in all_pts if p]
        lons = [p[1] for p in all_pts if p]
        if lats and lons:
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20,20))
    except Exception:
        pass
    st.session_state["map_html"] = m._repr_html_()

# ---------- Generate Map ----------
if st.sidebar.button("Generate Map (preserve)", key="generate_map_preserve"):
    build_map(origin, manual_greens, manual_yellows, manual_reds, GOV_INITIATIVES, st.session_state["assignments"])
    st.success("Map generated and preserved. Use Jan Aushadhi button to view prices & locations.")

# ---------- Layout: 3 columns ----------
col_left, col_mid, col_right = st.columns([3, 2, 6])

# ---------- LEFT: Jan Aushadhi tile (uses programmatic list or paste) ----------
with col_left:
    if st.session_state.get("show_jana"):
        st.markdown("## **Jan Aushadhi**")
        st.write("Locations and price lookup for a list of medicines. Provide the list programmatically via `st.session_state['medicines_list']`, or paste it below.")
        # ======= NEW: get medicines list from session or textarea =======
        meds = []
        # 1) prefer a programmatic list already stored in session
        if st.session_state.get("medicines_list"):
            val = st.session_state.get("medicines_list")
            if isinstance(val, (list, tuple)):
                meds = [str(x).strip() for x in val if str(x).strip()]
            elif isinstance(val, str):
                raw = val.strip()
                try:
                    import ast
                    parsed = ast.literal_eval(raw)
                    if isinstance(parsed, (list, tuple)):
                        meds = [str(x).strip() for x in parsed if str(x).strip()]
                    else:
                        meds = [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]
                except Exception:
                    meds = [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]
        else:
            st.markdown("Paste your medicine names below (one per line OR comma-separated OR a Python list literal).")
            paste = st.text_area("Medicines list (paste here)", value="", height=180, key="jana_paste")
            if paste and paste.strip():
                raw = paste.strip()
                try:
                    import ast
                    parsed = ast.literal_eval(raw)
                    if isinstance(parsed, (list, tuple)):
                        meds = [str(x).strip() for x in parsed if str(x).strip()]
                    else:
                        meds = [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]
                except Exception:
                    meds = [s.strip() for s in raw.replace(",", "\n").splitlines() if s.strip()]
                # persist into session for programmatic re-use if desired
                st.session_state["medicines_list"] = meds

        if not meds:
            st.info("No medicines provided yet. Paste them above or set st.session_state['medicines_list'] programmatically.")
        else:
            st.markdown("### Requested medicines")
            st.write(", ".join(meds))
            # price lookup using CSV
            df = st.session_state.get("csv_df")
            cols = st.session_state.get("csv_cols")
            if df is None:
                st.warning(f"Price CSV not found at '{CSV_PATH}'. Place the CSV in project root to enable lookups.")
            else:
                st.markdown("### Prices (best matches from CSV)")
                rows = []
                for med in meds:
                    matches = find_best_price_info(med, df, cols, top_n=5)
                    if matches:
                        best = None
                        for m in matches:
                            if m.get("price") is not None:
                                if best is None or m["price"] < best["price"]:
                                    best = m
                        if best is None:
                            best = matches[0]
                        rows.append({
                            "medicine": med,
                            "matched_name": best.get("match_name"),
                            "price": (f"₹{best.get('price'):.2f}" if best.get("price") is not None else "N/A"),
                            "vendor": best.get("vendor") or ""
                        })
                    else:
                        rows.append({"medicine": med, "matched_name":"", "price":"Not found", "vendor":""})
                df_prices = pd.DataFrame(rows)
                st.dataframe(df_prices, use_container_width=True)

        st.markdown("---")
        st.markdown("### Jan Aushadhi Clinic Locations")
        for g in GOV_INITIATIVES:
            st.markdown(f"**{g['name']}**  \n{g['address']}  \nCoords: {g['latlon'][0]:.6f}, {g['latlon'][1]:.6f}")
    else:
        st.markdown("## Jan Aushadhi")
        st.markdown("Click the **Jan Aushadhi** button in the sidebar to open the Jan Aushadhi tile (price lookup & locations).")

# ---------- MIDDLE: Delivery Agents ----------
with col_mid:
    st.markdown("## Delivery Agents")
    st.markdown("Hidden / hardcoded agents and current assignments.")
    agents_list = []
    for i, coord in enumerate(HIDDEN_AGENTS_COORDS):
        prof = AGENT_PROFILES[i] if i < len(AGENT_PROFILES) else {"name":f"Agent{i}","phone":"","vehicle":""}
        agents_list.append({"idx": i, "name": prof["name"], "phone": prof["phone"], "vehicle": prof["vehicle"], "lat": coord[0], "lon": coord[1]})
    df_agents = pd.DataFrame(agents_list)
    st.dataframe(df_agents, use_container_width=True, key="df_agents")

    st.markdown("### Current assignments")
    if st.session_state["assignments"]:
        rows = []
        for a in st.session_state["assignments"]:
            prof = a.get("agent_profile", {})
            rows.append({
                "agent": prof.get("name"),
                "phone": prof.get("phone"),
                "vehicle": prof.get("vehicle"),
                "store_coord": f"{a['store_coord'][0]:.6f}, {a['store_coord'][1]:.6f}",
                "distance_km": (f"{(a['total_m']/1000.0):.3f}" if a.get("total_m") else ""),
                "fare": (f"₹{a.get('charge')}" if a.get("charge") else "")
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, key="df_assigns")
    else:
        st.info("No assignments yet.")

    # Quick assign
    st.markdown("---")
    st.markdown("### Quick Assign")
    store_options = []
    for s in SHOP_DATABASE:
        store_options.append((s["name"], s["latlon"]))
    chosen_store = st.selectbox("Choose store to assign (quick)", options=store_options, format_func=lambda x: x[0], key="quick_store_select")
    if st.button("Assign random agent to chosen store", key="assign_random_quick"):
        store_coord = chosen_store[1]
        agent_idx = random.randrange(len(HIDDEN_AGENTS_COORDS))
        agent_coord = HIDDEN_AGENTS_COORDS[agent_idx]
        agent_profile = AGENT_PROFILES[agent_idx] if agent_idx < len(AGENT_PROFILES) else {"name":"Agent","phone":"", "vehicle":""}
        coords_ag_st, dist_ag_st, dur_ag_st = get_osrm_route(agent_coord, store_coord)
        coords_st_org, dist_st_org, dur_st_org = get_osrm_route(store_coord, origin) if origin else (None,None,None)
        if dist_ag_st is None:
            dist_ag_st = haversine_m(agent_coord, store_coord)
        if dist_st_org is None:
            dist_st_org = haversine_m(store_coord, origin) if origin else 0.0
        total_m = None
        if dist_ag_st is not None and dist_st_org is not None:
            total_m = dist_ag_st + dist_st_org
        charge = None
        if total_m is not None:
            km = total_m/1000.0
            if km <= 5: charge = 20
            elif km <= 10: charge = 30
            else: charge = 50
        assignment = {"agent_idx":agent_idx,"agent_coord":agent_coord,"agent_profile":agent_profile,"store_coord":store_coord,"coords_agent_store":coords_ag_st,"coords_store_origin":coords_st_org,"total_m":total_m,"charge":charge}
        st.session_state["assignments"].append(assignment)
        build_map(origin, manual_greens, manual_yellows, manual_reds, GOV_INITIATIVES, st.session_state["assignments"])
        st.success("Agent assigned and map updated (preserved).")

# ---------- RIGHT: Map (preserved) ----------
with col_right:
    st.markdown("## Map (preserved)")
    if st.session_state.get("map_html"):
        st.components.v1.html(st.session_state["map_html"], height=760)
    else:
        st.info("No preserved map yet. Use 'Generate Map (preserve)' in the sidebar to create it. Map remains frozen here unless you regenerate or assign agents.")
