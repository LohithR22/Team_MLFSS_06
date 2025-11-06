# app.py
"""
Streamlit app (improved debugging + wider tag coverage + Overpass fallbacks)
- Shows debug info: processed input, resolved origin coordinates
- Tries multiple Overpass endpoints if one fails
- Uses additional tags: shop=pharmacy, healthcare=pharmacy, shop=chemist, amenity=pharmacy
- Auto-expands radius (tries several radii) if no results initially
- Draws routes (colored) and links to Google Maps directions
"""
import streamlit as st
import requests
import math
import re
from urllib.parse import urlencode, quote_plus, urlparse, parse_qs, unquote_plus
import folium
from folium.plugins import MarkerCluster
import pandas as pd
from typing import List, Dict, Tuple, Optional
import time

# --------------- Config ---------------
HEADERS = {"User-Agent": "streamlit-pharmacy-poc/1.0 (contact: you@example.com)"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# multiple Overpass endpoints to try if one is busy
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter"
]
OSRM_SERVER = "https://router.project-osrm.org"
ROUTE_COLORS = ["blue", "green", "red", "purple", "orange", "darkred", "cadetblue", "darkgreen", "pink", "gray"]
# radii to attempt (meters) when expanding search automatically
RADIUS_TRIES = [int(x) for x in (2000, 4000, 8000, 15000)]
# ---------------------------------------

st.set_page_config(page_title="Pharmacy Finder (debuggable)", layout="wide")
st.title("Pharmacy / Medical Shop Finder — Debuggable POC")
st.markdown(
    "Paste an address or Google Maps link / text. The app will try to extract coordinates/address, query Overpass (multiple endpoints), "
    "auto-expand search radius if needed, and draw routes. Debug info shown below."
)

# ----- Sidebar controls -----
with st.sidebar:
    st.header("Search settings")
    raw_input = st.text_input("Address or paste Google Maps link / text", value="Kengeri, Bangalore")
    max_results = st.number_input("Max places to draw routes for", min_value=1, max_value=50, value=8)
    mode = st.selectbox("Routing mode (OSRM profile)", options=["driving", "walking", "cycling"], index=0)
    manual_radius = st.number_input("Force radius (meters, 0 = auto)", min_value=0, max_value=50000, value=0, step=100)
    st.markdown("---")
    st.markdown("Debug options")
    show_overpass_query = st.checkbox("Show Overpass query", value=True)
    st.markdown("Note: Public endpoints are rate-limited. Auto-radius may try larger radii to find POIs.")

# ---------- preprocessing (Google Maps paste handling) ----------
def preprocess_input(s: str) -> Dict:
    if not s:
        return {"type": "address", "address": ""}
    s0 = s.strip()
    s0 = s0.replace("\u200e", "").replace("\u200f", "").replace("\u2022", " ").replace("\u00b7", " ")
    s0 = s0.replace("\n", " ").replace("\r", " ").strip()
    s0 = re.sub(r"\s+[-·]\s*Google\s*Maps\s*$", "", s0, flags=re.I).strip()
    if s0.startswith("http://") or s0.startswith("https://") or "google.com/maps" in s0 or "goo.gl/maps" in s0:
        try:
            parsed = urlparse(s0)
            qs = parse_qs(parsed.query)
            m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', s0)
            if m:
                lat = float(m.group(1)); lon = float(m.group(2))
                return {"type": "coords", "lat": lat, "lon": lon, "display_name": f"{lat},{lon} (from URL @)"}
            for key in ("q", "query"):
                if key in qs and qs[key]:
                    candidate = qs[key][0]
                    candidate = unquote_plus(candidate)
                    if re.match(r'^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$', candidate):
                        lat_s, lon_s = [p.strip() for p in candidate.split(",")]
                        return {"type":"coords", "lat":float(lat_s), "lon":float(lon_s), "display_name": f"{lat_s},{lon_s} (from query param)"}
                    return {"type":"address", "address": candidate}
            path = parsed.path or ""
            m_place = re.search(r'/place/([^/]+)', path)
            if m_place:
                place = unquote_plus(m_place.group(1)).replace('+', ' ').strip()
                return {"type":"address", "address": place}
            m2 = re.search(r'(-?\d+\.\d+),(-?\d+\.\d+)', s0)
            if m2:
                lat = float(m2.group(1)); lon = float(m2.group(2))
                return {"type":"coords", "lat":lat, "lon":lon, "display_name": f"{lat},{lon} (from URL fallback)"}
            combined = (parsed.path + " " + parsed.query).replace("/", " ").strip()
            combined = unquote_plus(combined)
            combined = re.sub(r'\s+', ' ', combined).strip()
            if combined:
                return {"type":"address", "address": combined}
        except Exception:
            pass
    mcoords = re.match(r'^\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*$', s0)
    if mcoords:
        return {"type":"coords", "lat": float(mcoords.group(1)), "lon": float(mcoords.group(3)), "display_name": f"{mcoords.group(1)},{mcoords.group(3)}"}
    cleaned = re.sub(r'\s+', ' ', s0).strip()
    return {"type":"address", "address": cleaned}

# ----- geocode (Nominatim) -----
@st.cache_data(ttl=60*60)
def geocode(addr_txt: str) -> Optional[Dict]:
    if not addr_txt:
        return None
    txt = addr_txt.strip()
    # coords fast path
    if ',' in txt:
        parts = [p.strip() for p in txt.split(',')]
        try:
            lat = float(parts[0]); lon = float(parts[1])
            return {"lat": lat, "lon": lon, "display_name": f"{lat},{lon}"}
        except Exception:
            pass
    params = {"q": txt, "format": "jsonv2", "limit": 1}
    url = NOMINATIM_URL + "?" + urlencode(params)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    d = r.json()
    if not d:
        return None
    top = d[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top.get("display_name","")}

# ----- Overpass search with multiple tag options and endpoints -----
def build_overpass_query(lat: float, lon: float, radius: int) -> str:
    # broader tag coverage: amenity=pharmacy, shop=chemist, shop=pharmacy, healthcare=pharmacy
    q = f"""
    [out:json][timeout:45];
    (
      node["amenity"="pharmacy"](around:{radius},{lat},{lon});
      way["amenity"="pharmacy"](around:{radius},{lat},{lon});
      relation["amenity"="pharmacy"](around:{radius},{lat},{lon});
      node["shop"="chemist"](around:{radius},{lat},{lon});
      way["shop"="chemist"](around:{radius},{lat},{lon});
      relation["shop"="chemist"](around:{radius},{lat},{lon});
      node["shop"="pharmacy"](around:{radius},{lat},{lon});
      way["shop"="pharmacy"](around:{radius},{lat},{lon});
      relation["shop"="pharmacy"](around:{radius},{lat},{lon});
      node["healthcare"="pharmacy"](around:{radius},{lat},{lon});
      way["healthcare"="pharmacy"](around:{radius},{lat},{lon});
      relation["healthcare"="pharmacy"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    return q

def try_overpass(lat: float, lon: float, radius: int, show_query=False) -> Tuple[List[Dict], str, str]:
    """
    Try multiple Overpass endpoints until one returns results or exhausted.
    Returns (places_list, used_endpoint, query_text)
    """
    q = build_overpass_query(lat, lon, radius)
    last_exc = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(endpoint, data=q.encode('utf-8'), headers=HEADERS, timeout=60)
            r.raise_for_status()
            data = r.json()
            places = []
            for el in data.get("elements", []):
                if el.get("type") == "node":
                    lat_e = el.get("lat"); lon_e = el.get("lon")
                else:
                    center = el.get("center")
                    if not center:
                        continue
                    lat_e = center.get("lat"); lon_e = center.get("lon")
                tags = el.get("tags", {}) or {}
                name = tags.get("name") or tags.get("operator") or "Unknown"
                addr_parts = []
                for k in ["addr:housenumber","addr:street","addr:city","addr:postcode","addr:state","addr:country"]:
                    if tags.get(k):
                        addr_parts.append(tags.get(k))
                address = ", ".join(addr_parts) if addr_parts else tags.get("addr:full") or ""
                place = {
                    "id": el.get("id"),
                    "osm_type": el.get("type"),
                    "lat": lat_e,
                    "lon": lon_e,
                    "name": name,
                    "address": address,
                    "phone": tags.get("phone") or tags.get("contact:phone"),
                    "website": tags.get("website") or tags.get("contact:website"),
                    "opening_hours": tags.get("opening_hours"),
                    "tags": tags
                }
                places.append(place)
            return places, endpoint, q
        except Exception as e:
            last_exc = e
            # try next endpoint after short wait
            time.sleep(0.5)
            continue
    # all endpoints failed or returned nothing: return empty and last endpoint attempted
    return [], (OVERPASS_ENDPOINTS[-1] if OVERPASS_ENDPOINTS else ""), q

# ----- routing (OSRM) -----
@st.cache_data(ttl=60*60)
def get_route_osrm_cached(origin: Dict, dest: Dict, profile: str = "driving") -> Tuple[Optional[List[List[float]]], Optional[Dict]]:
    coords = f"{origin['lon']},{origin['lat']};{dest['lon']},{dest['lat']}"
    params = "overview=full&geometries=geojson"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords}?{params}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None, None
    route = data["routes"][0]
    coords_lonlat = route["geometry"]["coordinates"]
    coords_latlon = [[c[1], c[0]] for c in coords_lonlat]
    summary = {"distance_m": route.get("distance"), "duration_s": route.get("duration")}
    return coords_latlon, summary

# ----- helpers -----
def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def sort_places_by_distance(origin: Dict, places: List[Dict]) -> List[Dict]:
    for p in places:
        p["distance_m"] = haversine_m(origin["lat"], origin["lon"], p["lat"], p["lon"])
    return sorted(places, key=lambda x: x["distance_m"])

def google_maps_directions_link(origin: Dict, dest: Dict, travelmode: str = "driving"):
    origin_str = f"{origin['lat']},{origin['lon']}"
    dest_str = f"{dest['lat']},{dest['lon']}"
    params = {"api": "1", "origin": origin_str, "destination": dest_str, "travelmode": travelmode}
    url = "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())
    return url

# ---------------- Main UI flow ----------------
col_map, col_list = st.columns([2.2, 1])

processed = preprocess_input(raw_input)
st.sidebar.markdown("**Processed input (debug)**")
st.sidebar.write(processed)

with st.spinner("Resolving origin (geocoding or coords)..."):
    origin = None
    try:
        if processed["type"] == "coords":
            origin = {"lat": processed["lat"], "lon": processed["lon"], "display_name": processed.get("display_name", f"{processed['lat']},{processed['lon']}")}
        else:
            origin = geocode(processed.get("address", ""))
    except Exception as e:
        st.error(f"Geocoding error: {e}")
        origin = None

if origin is None:
    st.warning("No origin resolved. Try pasting a different address or a Google Maps URL with coordinates.")
else:
    st.sidebar.markdown("**Resolved origin**")
    st.sidebar.write(origin)

    # determine radii to try
    radii_to_try = RADIUS_TRIES if manual_radius == 0 else [manual_radius]
    found_places = []
    used_endpoint = ""
    used_query = ""
    used_radius = None

    # Try a sequence of radii until we get at least one result (or exhaust)
    for r_try in radii_to_try:
        with st.spinner(f"Searching Overpass within {r_try} m ..."):
            places, endpoint, qtext = try_overpass(origin["lat"], origin["lon"], r_try, show_query=show_overpass_query)
        # store debug
        used_endpoint = endpoint
        used_query = qtext
        used_radius = r_try
        if places:
            found_places = places
            break
        # otherwise continue loop to next larger radius
    # after trying radii
    if not found_places:
        st.error(f"No medical shops found within radii {radii_to_try}. Tried Overpass endpoint: {used_endpoint}")
        if show_overpass_query:
            st.code(used_query[:4000])  # show first chunk of query
        st.stop()

    # sort and trim
    places = sort_places_by_distance(origin, found_places)
    st.sidebar.markdown(f"**Overpass endpoint used:** {used_endpoint}")
    st.sidebar.markdown(f"**Radius used:** {used_radius} m")
    st.sidebar.markdown(f"**Total POIs found:** {len(places)} (showing top {min(len(places),200)})")
    # debug preview of first few elements
    preview = []
    for p in places[:8]:
        preview.append({"name": p["name"], "lat": p["lat"], "lon": p["lon"], "address": p.get("address",""), "tags_preview": dict(list(p.get("tags",{}).items())[:6])})
    st.sidebar.markdown("**First few POIs (preview)**")
    st.sidebar.write(preview)

    show_places = places[: max(1, min(len(places), 300))]
    route_places = places[: max(1, min(len(places), int(max_results)))]

    # --- map column
    with col_map:
        st.subheader("Map")
        st.write(f"Origin: **{origin.get('display_name','(coords)')}** — results: {len(show_places)} POIs, drawing routes for top {len(route_places)}")
        selected_index = st.selectbox(
            "Select place to focus on (does not affect routes drawn)",
            options=list(range(len(show_places))),
            format_func=lambda i: f"{i+1}. {show_places[i]['name']} - {int(show_places[i].get('distance_m',0))} m",
            index=0
        )
        selected = show_places[int(selected_index)]

        m = folium.Map(location=[origin["lat"], origin["lon"]], zoom_start=14)
        folium.Marker([origin["lat"], origin["lon"]], tooltip="Origin", popup=origin.get("display_name","Origin"),
                      icon=folium.Icon(color="blue", icon="user")).add_to(m)

        mc = MarkerCluster().add_to(m)
        for i, p in enumerate(show_places):
            popup_html = f"<b>{p.get('name')}</b><br>"
            popup_html += f"Distance: {int(p.get('distance_m',0))} m<br>"
            if p.get("address"):
                popup_html += f"Address: {p.get('address')}<br>"
            if p.get("opening_hours"):
                popup_html += f"Hours: {p.get('opening_hours')}<br>"
            if p.get("phone"):
                popup_html += f"Phone: {p.get('phone')}<br>"
            gmaps = google_maps_directions_link(origin, {"lat": p["lat"], "lon": p["lon"]}, travelmode=mode)
            popup_html += f"<a href='{gmaps}' target='_blank'>Open directions in Google Maps</a><br>"
            popup_html += "<small>OSM tags: " + ", ".join([f"{k}={v}" for k,v in list(p.get('tags',{}).items())[:6]]) + "</small>"
            folium.Marker([p["lat"], p["lon"]], popup=folium.Popup(popup_html, max_width=350)).add_to(mc)

        st.info(f"Computing routes for {len(route_places)} places (this may take a few seconds).")
        for idx, p in enumerate(route_places):
            try:
                coords, summary = get_route_osrm_cached(origin, {"lat": p["lat"], "lon": p["lon"]}, profile=mode)
            except Exception as e:
                coords, summary = None, None
            if coords:
                color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
                gmaps = google_maps_directions_link(origin, {"lat": p["lat"], "lon": p["lon"]}, travelmode=mode)
                popup_html = f"<b>{p.get('name')}</b><br>Route to this place<br>"
                if summary:
                    popup_html += f"Distance: {int(summary['distance_m'])} m<br>ETA: {int(summary['duration_s']/60)} min<br>"
                popup_html += f"<a href='{gmaps}' target='_blank'>Open in Google Maps (Directions)</a>"
                folium.PolyLine(locations=coords, color=color, weight=5, opacity=0.85,
                                tooltip=f"{p.get('name')} ({int(p.get('distance_m',0))} m)",
                                popup=folium.Popup(popup_html, max_width=350)).add_to(m)
            else:
                folium.CircleMarker([p["lat"], p["lon"]], radius=4, color="gray", fill=True, fill_color="gray").add_to(m)

        folium.CircleMarker([selected["lat"], selected["lon"]], radius=9, color="red", fill=True, fill_color="red").add_to(m)

        html = m._repr_html_()
        st.components.v1.html(html, height=720, scrolling=True)

    # --- right column: list + debug
    with col_list:
        st.subheader("Nearby medical shops (top results)")
        df = pd.DataFrame([{
            "Name": p["name"],
            "Distance (m)": int(p.get("distance_m", 0)),
            "Address": p.get("address",""),
            "Phone": p.get("phone",""),
            "Hours": p.get("opening_hours","")
        } for p in places[:200]])
        st.dataframe(df, use_container_width=True)

        st.markdown("### Selected place details")
        st.write(selected)

        try:
            coords_sel, summary_sel = get_route_osrm_cached(origin, {"lat": selected["lat"], "lon": selected["lon"]}, profile=mode)
        except Exception:
            coords_sel, summary_sel = None, None
        if summary_sel:
            st.success(f"Selected route: {int(summary_sel['distance_m'])} m, approx {int(summary_sel['duration_s']/60)} min")

        st.markdown("---")
        st.markdown("**Debug / fallback info**")
        st.write({
            "processed_input": processed,
            "origin": origin,
            "overpass_endpoint_used": used_endpoint,
            "radius_used_m": used_radius,
            "total_pois_found": len(places)
        })
        if show_overpass_query:
            st.markdown("**Overpass query (first 4000 chars)**")
            st.code(used_query[:4000])

