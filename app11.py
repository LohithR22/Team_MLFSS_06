# app.py
"""
Delivery Map — shop-name matching
- If a UI-entered store coordinate matches one of the known shop coords (within MATCH_RADIUS_METERS),
  we show and store the shop's real name instead of a generic label.
- Shop DB is hardcoded (the list you provided).
- Matched shop names are placed into stores_flat[*]["meta"]["shop_name"] and shown in popups / selection.
- All prior functionality (gov, agents, assignments, billing, preserved map) preserved.
"""

import streamlit as st
import folium
from folium import IFrame, Popup
from branca.element import Element
import requests, random, json, os, math
from urllib.parse import quote_plus
from streamlit.components.v1 import html as st_html

# ---------- CONFIG ----------
OSRM_SERVER = "https://router.project-osrm.org"
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTR = "© OpenStreetMap contributors"
YELLOW_SHADES = ["#E0A800", "#FFD43B", "#FFEB99"]
PURPLE_HEX = "#800080"
BLUE_GOV_COLOR = "blue"
# match radius for shop coordinate -> name mapping (meters)
MATCH_RADIUS_METERS = 50.0
# Hidden agents + profiles
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

# ------------------ Known shop DB (from user) ------------------
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

# Hardcoded GOV initiatives with full addresses (from user)
GOV_INITIATIVES = [
    {
        "name": "Pradhan Mantri JanAushadhi Kendra - Gokhale Rd",
        "address": "921, Gokhale Rd, Behind rangamadira, III Stage 3 Block, BEML Layout 3rd Stage, Rajarajeshwari Nagar, Bengaluru, Karnataka 560098",
        "latlon": (12.917612214940876, 77.51904488091897)
    },
    {
        "name": "Pradhan Mantri Janaushadhi Kendra - BHEL / Sir M Vishveshwaraiah Main Rd",
        "address": "Sir M Vishveshwaraiah Main Rd, BHEL 2nd Stage, Pattanagere, Rajarajeshwari Nagar, Bengaluru, Karnataka 560098",
        "latlon": (12.917612214940876, 77.50978399033598)
    },
    {
        "name": "Pradhan Mantri Jan Aushadhi Kendra - Kenchena Halli Rd (YGR signature Mall)",
        "address": "17 ground floor, 1st main road, Kenchena Halli Rd, opposite to YGR signature Mall, 5th Stage, Rajarajeshwari Nagar, Bengaluru, Karnataka 560098",
        "latlon": (12.910492603965448, 77.51343617253772)
    },
    {
        "name": "PRADHAN MANTRI BHARTIYA JANAUSHADHI KENDRA - Channasandra",
        "address": "No 851, Dr.Vishnuvardhan Rd, Channasandra, Srinivaspura, Bengaluru, Karnataka 560098",
        "latlon": (12.903563502133089, 77.52067531940189)
    },
    {
        "name": "Pradhan mantri Janaushadhi kendra - Kodipalya",
        "address": "Shop No.F4, Vasthu Green Shopping Complex, near Gutte Anjaneya swamy Temple, Kodipalya, Bengaluru, Karnataka 560060",
        "latlon": (12.906666049048614, 77.48845393143118)
    },
    {
        "name": "Pradhan Mantri Bhartiya Jan Aushadhi Kendra Kengeri",
        "address": "WF7J+W7F, #674 ,3RD MAIN ROAD, KOMMAGHATTA ROAD, NEAR HOTEL NAMMANE COFFEE KENGERI SATALLITE TOWN, Kengeri, Bengaluru, Karnataka 560060",
        "latlon": (12.915871335395288, 77.4804822691128)
    }
]

# -----------------------------

st.set_page_config(page_title="Delivery Map — shop-name matching", layout="wide")
st.title("Delivery Map — Shop name matching & preserved map")

# -------------- Helpers ----------------
def parse_coord(txt: str):
    parts = [p.strip() for p in txt.split(",")]
    return (float(parts[0]), float(parts[1]))

def haversine_m(p1, p2):
    # p1, p2 are (lat, lon)
    R = 6371000.0
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def find_shop_name(coord):
    """Return shop dict if any in SHOP_DATABASE is within MATCH_RADIUS_METERS of coord."""
    for shop in SHOP_DATABASE:
        d = haversine_m(coord, shop["latlon"])
        if d <= MATCH_RADIUS_METERS:
            # include the distance for debugging if needed
            return {"name": shop["name"], "latlon": shop["latlon"], "distance_m": d}
    return None

def google_maps_link(origin, dest):
    params = {
        "api": "1",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest[0]},{dest[1]}",
        "travelmode": "driving"
    }
    return "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())

def get_osrm_route(src, dst, profile="driving"):
    coords_str = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=18)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        geom = route["geometry"]["coordinates"]  # lon,lat
        coords_latlon = [[c[1], c[0]] for c in geom]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception:
        return None, None, None

def compute_billing_from_meters(total_m):
    if total_m is None:
        return None
    km = total_m/1000.0
    if km <= 5.0:
        return 20
    elif km <= 10.0:
        return 30
    else:
        return 50

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
    html = "<br>".join(lines)
    return IFrame(html, width=340, height=160)

# ---------- Session init ----------
if "map_html" not in st.session_state:
    st.session_state["map_html"] = None
if "assignments" not in st.session_state:
    st.session_state["assignments"] = []

# -------------- Sidebar inputs (one-line coords) --------------
with st.sidebar:
    st.header("Inputs")
    origin_input = st.text_input("Origin (lat, lon)", value="12.9716, 77.5946")
    st.markdown("**Green stores (2)**")
    g1 = st.text_input("Green 1", "")
    g2 = st.text_input("Green 2", "")
    st.markdown("**Yellow stores (3)**")
    y1 = st.text_input("Yellow 1", "")
    y2 = st.text_input("Yellow 2", "")
    y3 = st.text_input("Yellow 3", "")
    st.markdown("**Red stores (2)**")
    r1 = st.text_input("Red 1", "")
    r2 = st.text_input("Red 2", "")
    st.markdown(f"Note: Known shop list has {len(SHOP_DATABASE)} entries — if your entered coordinates match one within {MATCH_RADIUS_METERS}m, the app will show the shop name.")

# parse helper
def collect_coords(*txts):
    out = []
    for t in txts:
        if t and t.strip():
            try:
                out.append(parse_coord(t))
            except Exception:
                st.sidebar.error(f"Invalid coordinate: {t}")
    return out

try:
    origin = parse_coord(origin_input)
except Exception:
    st.sidebar.error("Invalid origin format. Use: lat, lon")
    st.stop()

greens = collect_coords(g1, g2)
yellows = collect_coords(y1, y2, y3)
reds = collect_coords(r1, r2)

# Build stores_flat including GOV as selectable "blue" stores.
# For UI-entered coords we attempt to match shop DB and store shop name in meta if matched.
stores_flat = []
def add_store(coord, color):
    meta = {}
    shop = find_shop_name(coord)
    if shop:
        meta["shop_name"] = shop["name"]
        meta["matched_shop_coord"] = shop["latlon"]
        meta["match_distance_m"] = shop["distance_m"]
    stores_flat.append({"color": color, "coord": coord, "label": color.capitalize(), "meta": meta})

for c in greens:
    add_store(c, "green")
for c in yellows:
    add_store(c, "yellow")
for c in reds:
    add_store(c, "red")
# append govt initiatives as blue, include name/address
for g in GOV_INITIATIVES:
    stores_flat.append({"color": "blue", "coord": g["latlon"], "label": "Gov", "meta": {"name": g["name"], "address": g["address"]}})

# --------------- Map builder (draw everything) ----------------
def build_map_and_store_html(origin, stores_flat, gov_items, assignments):
    m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

    # origin marker
    folium.Marker(
        location=origin,
        icon=folium.Icon(color="blue", icon="home"),
        popup=Popup(make_popup_html("Origin", origin, gm_link=google_maps_link(origin, origin)), max_width=300)
    ).add_to(m)

    # red -> yellow -> green -> blue stacking
    for s in [s for s in stores_flat if s["color"] == "red"]:
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        # label: prefer matched shop_name if exists
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "Red store"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        folium.Marker(location=coord, icon=folium.Icon(color="darkred"), popup=Popup(make_popup_html(title, coord, gm_link=gm, extra_html=extra), max_width=360)).add_to(m)
        coords, dist, dur = get_osrm_route(origin, coord)
        if coords:
            folium.PolyLine(coords, color="red", weight=4, opacity=0.6).add_to(m)
        else:
            folium.PolyLine([origin, coord], color="red", weight=3, opacity=0.4, dash_array="5,5").add_to(m)

    yellow_shades = YELLOW_SHADES
    yellow_list = [s for s in stores_flat if s["color"] == "yellow"]
    for idx, s in enumerate(yellow_list):
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "Yellow store"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        folium.Marker(location=coord, icon=folium.Icon(color="lightgray"), popup=Popup(make_popup_html(title, coord, gm_link=gm, extra_html=extra), max_width=360)).add_to(m)
        coords, dist, dur = get_osrm_route(origin, coord)
        color = yellow_shades[min(idx, len(yellow_shades) - 1)]
        if coords:
            folium.PolyLine(coords, color=color, weight=4, opacity=0.6).add_to(m)
        else:
            folium.PolyLine([origin, coord], color=color, weight=3, opacity=0.4, dash_array="5,5").add_to(m)

    for s in [s for s in stores_flat if s["color"] == "green"]:
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "Green store"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        folium.Marker(location=coord, icon=folium.Icon(color="green"), popup=Popup(make_popup_html(title, coord, gm_link=gm, extra_html=extra), max_width=360)).add_to(m)
        coords, dist, dur = get_osrm_route(origin, coord)
        if coords:
            folium.PolyLine(coords, color="green", weight=5, opacity=0.7).add_to(m)
        else:
            folium.PolyLine([origin, coord], color="green", weight=4, opacity=0.45, dash_array="5,5").add_to(m)

    # blue gov markers — add popup with name/address + Show route toggle anchor
    gov_routes_data = []
    for i, g in enumerate(gov_items):
        coord = g["latlon"]
        gm = google_maps_link(origin, coord)
        extra_html = f"<a href='#show-gov-{i}' class='show-gov' data-idx='{i}'>Show route on map</a><br><small>{g['name']}</small>"
        popup_iframe = make_popup_html("Gov Initiative (blue)", coord, gm_link=gm, extra_html=extra_html)
        folium.Marker(location=coord, icon=folium.Icon(color=BLUE_GOV_COLOR, icon="info-sign"), popup=Popup(popup_iframe, max_width=360)).add_to(m)
        coords, dist, dur = get_osrm_route(origin, coord)
        gov_routes_data.append({"index": i, "coords": coords, "distance": dist, "duration": dur, "meta": {"name": g["name"], "address": g["address"]}})
        if not coords:
            folium.PolyLine([origin, coord], color="blue", weight=3, opacity=0.0, dash_array="5,5").add_to(m)

    # draw assignments (visible purple)
    for a in assignments:
        agent_coord = a["agent_coord"]
        profile = a["agent_profile"]
        store_coord = a["store_coord"]
        profile_html = f"<b>{profile['name']}</b><br>{profile['phone']}<br>{profile['vehicle']}"
        popup = make_popup_html("Assigned Agent", agent_coord, gm_link=google_maps_link(agent_coord, store_coord), extra_html=profile_html)
        folium.Marker(location=agent_coord, icon=folium.Icon(color="purple"), popup=Popup(popup, max_width=300)).add_to(m)
        if a.get("coords_agent_store"):
            folium.PolyLine(a["coords_agent_store"], color=PURPLE_HEX, weight=5, opacity=0.9).add_to(m)
        else:
            folium.PolyLine([agent_coord, store_coord], color=PURPLE_HEX, weight=4, opacity=0.8, dash_array="3,6").add_to(m)
        if a.get("coords_store_origin"):
            folium.PolyLine(a["coords_store_origin"], color=PURPLE_HEX, weight=7, opacity=0.95).add_to(m)
        else:
            folium.PolyLine([store_coord, origin], color=PURPLE_HEX, weight=6, opacity=0.9, dash_array="3,6").add_to(m)
        folium.CircleMarker(location=store_coord, radius=6, color=PURPLE_HEX, fill=True, fill_color=PURPLE_HEX).add_to(m)

    # inject JS to create hidden gov polylines and toggle them on popup link click
    gov_routes_json = json.dumps(gov_routes_data)
    js_template = """
    <script>
    (function(){
        try {
            const govRoutes = GOV_ROUTES_JSON;
            const Lmap = window.map || window._leaflet_map || (function(){
                for (const k in window) {
                    try {
                        const v = window[k];
                        if (v && typeof v === 'object' && v.hasOwnProperty && v.hasOwnProperty('_layers')) return v;
                    } catch(e){}
                }
                return null;
            })();
            const govPolylines = {};
            if (govRoutes && govRoutes.length>0) {
                govRoutes.forEach(function(gr){
                    if (!gr.coords) {
                        govPolylines[gr.index] = null;
                        return;
                    }
                    const latlngs = gr.coords.map(function(pt){ return [pt[0], pt[1]]; });
                    try {
                        const pl = L.polyline(latlngs, {color: 'blue', weight: 5, opacity: 0.0});
                        if (Lmap && Lmap.addLayer) pl.addTo(Lmap);
                        govPolylines[gr.index] = pl;
                    } catch(e) {
                        console.warn('gov polyline creation failed', e);
                        govPolylines[gr.index] = null;
                    }
                });
            }
            document.addEventListener('click', function(ev){
                const target = ev.target;
                if (!target) return;
                if (target.tagName === 'A' && target.getAttribute('href') && target.getAttribute('href').startsWith('#show-gov-')) {
                    ev.preventDefault();
                    const idxStr = target.getAttribute('data-idx') || target.getAttribute('href').split('-').pop();
                    const idx = parseInt(idxStr);
                    const pl = govPolylines[idx];
                    if (!pl) {
                        alert('Route not available for this government initiative (OSRM may have failed). A straight-line fallback is shown instead.');
                        return;
                    }
                    const current = pl.options.opacity || (pl._path && pl._path.getAttribute ? parseFloat(pl._path.getAttribute('stroke-opacity') || 0.0) : 0.0);
                    if (current <= 0.01) {
                        pl.setStyle({opacity:0.95});
                        try{ pl.bringToFront(); }catch(e){}
                    } else {
                        pl.setStyle({opacity:0.0});
                    }
                }
            }, false);
        } catch(err) { console.error('gov-route-js', err); }
    })();
    </script>
    """
    js_filled = js_template.replace("GOV_ROUTES_JSON", gov_routes_json)
    safe_script = "{% raw %}\n" + js_filled + "\n{% endraw %}"
    m.get_root().html.add_child(Element(safe_script))

    # bounds
    all_points = [origin] + [s["coord"] for s in stores_flat] + [g["latlon"] for g in gov_items] + HIDDEN_AGENTS_COORDS
    try:
        lats = [p[0] for p in all_points if p]
        lons = [p[1] for p in all_points if p]
        if lats and lons:
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20,20))
    except Exception:
        pass

    st.session_state["map_html"] = m._repr_html_()

# ----------------- UI actions -----------------
col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("Generate Map (preserve)"):
        build_map_and_store_html(origin, stores_flat, GOV_INITIATIVES, st.session_state["assignments"])
        st.success("Map generated and preserved. Known shops matched where coordinates fell within tolerance.")

with col2:
    if st.button("Clear Assignments"):
        st.session_state["assignments"] = []
        build_map_and_store_html(origin, stores_flat, GOV_INITIATIVES, st.session_state["assignments"])
        st.success("Cleared all assignments.")

with col3:
    if st.button("Export assignments JSON"):
        payload = json.dumps(st.session_state["assignments"], default=str, indent=2)
        st.download_button("Download assignments.json", payload.encode("utf-8"), file_name="assignments.json")

# store selection UI (shows shop names if matched)
if stores_flat:
    st.subheader("Select a store (green/yellow/red/blue) to assign an agent to")
    labels = []
    for i, s in enumerate(stores_flat):
        shop_name = s.get("meta", {}).get("shop_name")
        label = f"{i+1}. [{s['color'].upper()}] {s['coord'][0]:.6f}, {s['coord'][1]:.6f}"
        if s["color"] == "blue":
            meta = s.get("meta", {})
            if meta.get("name"):
                label += f" — {meta['name']}"
        elif shop_name:
            label += f" — {shop_name}"
        labels.append(label)
    sel = st.selectbox("Store", options=list(range(len(labels))), format_func=lambda i: labels[i])

    if st.button("Assign Random Agent to Selected Store"):
        chosen = stores_flat[sel]
        store_coord = chosen["coord"]
        store_color = chosen["color"]
        shop_name = chosen.get("meta", {}).get("shop_name")
        agent_idx = random.randrange(len(HIDDEN_AGENTS_COORDS))
        agent_coord = HIDDEN_AGENTS_COORDS[agent_idx]
        agent_profile = AGENT_PROFILES[agent_idx] if agent_idx < len(AGENT_PROFILES) else {"name":"Agent","phone":"NA","vehicle":"NA"}

        coords_ag_st, dist_ag_st, dur_ag_st = get_osrm_route(agent_coord, store_coord)
        coords_st_org, dist_st_org, dur_st_org = get_osrm_route(store_coord, origin)

        if dist_ag_st is None:
            dist_ag_st = haversine_m(agent_coord, store_coord)
        if dist_st_org is None:
            dist_st_org = haversine_m(store_coord, origin)

        total_m = None
        if dist_ag_st is not None and dist_st_org is not None:
            total_m = dist_ag_st + dist_st_org

        charge = compute_billing_from_meters(total_m) if total_m is not None else None

        assignment = {
            "agent_idx": agent_idx,
            "agent_coord": agent_coord,
            "agent_profile": agent_profile,
            "store_coord": store_coord,
            "store_color": store_color,
            "store_shop_name": shop_name,
            "coords_agent_store": coords_ag_st,
            "dist1_m": dist_ag_st,
            "coords_store_origin": coords_st_org,
            "dist2_m": dist_st_org,
            "total_m": total_m,
            "charge": charge
        }

        st.session_state["assignments"].append(assignment)
        build_map_and_store_html(origin, stores_flat, GOV_INITIATIVES, st.session_state["assignments"])

        # summary display
        st.success("Assigned delivery agent (hidden). Map updated and preserved.")
        # Agent details
        st.markdown(f"**Agent:** {agent_profile['name']}  \n**Phone:** {agent_profile['phone']}  \n**Vehicle:** {agent_profile['vehicle']}")
        # Store / shop name
        if shop_name:
            st.markdown(f"**Store (matched):** {shop_name} — {store_coord[0]:.6f}, {store_coord[1]:.6f}")
        else:
            st.markdown(f"**Store:** {store_coord[0]:.6f}, {store_coord[1]:.6f} (no match)")

        if total_m is not None:
            leg1_km = (dist_ag_st/1000.0) if dist_ag_st is not None else 0.0
            leg2_km = (dist_st_org/1000.0) if dist_st_org is not None else 0.0
            st.markdown(f"Leg 1 (agent → store): **{leg1_km:.3f} km**  \nLeg 2 (store → origin): **{leg2_km:.3f} km**")
            st.markdown(f"<div style='font-size:20px;color:green;font-weight:700'>Total distance: {total_m/1000.0:.3f} km</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:28px;color:#d9534f;font-weight:900'>Estimated charge: Rs. {charge}</div>", unsafe_allow_html=True)
        else:
            st.warning("Distance calculation failed; billing unavailable.")

# ---------- Render preserved map ----------
st.subheader("Map (preserved)")
if st.session_state.get("map_html"):
    st_html(st.session_state["map_html"], height=720)
else:
    st.info("No map generated yet. Click 'Generate Map (preserve)' to create it.")
