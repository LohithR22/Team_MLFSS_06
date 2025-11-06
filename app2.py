# app.py
"""
Streamlit app: show nearby pharmacies / chemists (OSM) and draw routes to each one.
Improvements:
 - Robust preprocessing for pasted Google Maps addresses/URLs (extract coords or clean address)
 - All POIs shown, routes drawn in different colors, route popup opens Google Maps directions
Notes: Public OSM/OSRM endpoints are rate-limited. For production or many routes, self-host or use paid services.
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

# ----------------- Config -----------------
HEADERS = {"User-Agent": "streamlit-pharmacy-poc/1.0 (contact: you@example.com)"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_SERVER = "https://router.project-osrm.org"  # public demo server
ROUTE_COLORS = ["blue", "green", "red", "purple", "orange", "darkred", "cadetblue", "darkgreen", "pink", "gray"]
# ------------------------------------------

st.set_page_config(page_title="Pharmacy Finder (OSM)", layout="wide")
st.title("Pharmacy / Medical Shop Finder — Streamlit POC")
st.markdown(
    "Paste an address or Google Maps link (the app will try to extract full address or coords). "
    "Choose search radius and max results. Click a route to open Google Maps Directions."
)

# ----- Sidebar controls -----
with st.sidebar:
    st.header("Search settings")
    raw_input = st.text_input("Address or paste Google Maps link / text", value="MG Road, Bangalore")
    radius_m = st.slider("Search radius (meters)", 200, 10000, 2000, step=100)
    max_results = st.number_input("Max places to display (routes drawn)", min_value=1, max_value=50, value=8)
    mode = st.selectbox("Routing mode (OSRM profile)", options=["driving", "walking", "cycling"], index=0)
    st.write("Note: Public OSM endpoints are rate-limited. For production, self-host or use paid services.")
    st.markdown("---")
    st.markdown("**Tips**:\n- Paste full Google Maps URL or copy address from the place card. The app will attempt to parse it.")

# ----- Preprocess pasted input (handle Google Maps links / messy copy) -----
def preprocess_input(s: str) -> Dict:
    """
    Return a dict:
      - if coords detected: {'type':'coords', 'lat':..., 'lon':..., 'display_name': original}
      - else: {'type':'address', 'address': cleaned_string}
    Handles:
      - Google Maps URL with @lat,lon (e.g. https://www.google.com/maps/@12.34,56.78,15z)
      - Google Maps URL with query param query=...
      - pasted address with trailing ' - Google Maps' etc.
      - newline cleanup and stray unicode markers
    """
    if not s:
        return {"type": "address", "address": ""}
    s0 = s.strip()
    # remove invisible unicode markers and bullets
    s0 = s0.replace("\u200e", "").replace("\u200f", "").replace("\u2022", " ").replace("\u00b7", " ")
    s0 = s0.replace("\n", " ").replace("\r", " ").strip()
    # remove common suffixes like " - Google Maps" or " · Google Maps"
    s0 = re.sub(r"\s+[-·]\s*Google\s*Maps\s*$", "", s0, flags=re.I).strip()

    # If it looks like a URL, parse it
    if s0.startswith("http://") or s0.startswith("https://") or "google.com/maps" in s0 or "goo.gl/maps" in s0:
        try:
            # ensure URL decoding
            parsed = urlparse(s0)
            qs = parse_qs(parsed.query)
            # 1) try @lat,lon pattern in path (common)
            m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', s0)
            if m:
                lat = float(m.group(1)); lon = float(m.group(2))
                return {"type": "coords", "lat": lat, "lon": lon, "display_name": f"{lat},{lon} (from Google Maps URL)"}
            # 2) try query param 'query' (maps URLs with ?q= or query=)
            for key in ("q", "query"):
                if key in qs and qs[key]:
                    candidate = qs[key][0]
                    candidate = unquote_plus(candidate)
                    candidate = re.sub(r"\s+[-·]\s*Google\s*Maps\s*$", "", candidate, flags=re.I).strip()
                    # if candidate looks like coords
                    if re.match(r'^\s*-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?\s*$', candidate):
                        lat_s, lon_s = [p.strip() for p in candidate.split(",")]
                        return {"type":"coords", "lat":float(lat_s), "lon":float(lon_s), "display_name": f"{lat_s},{lon_s} (from query param)"}
                    return {"type":"address", "address": candidate}
            # 3) some Google Maps short links contain place names in path after /place/
            path = parsed.path or ""
            m_place = re.search(r'/place/([^/]+)', path)
            if m_place:
                place = unquote_plus(m_place.group(1)).replace('+', ' ').strip()
                place = re.sub(r'\+',' ', place)
                return {"type":"address", "address": place}
            # 4) fallback: try to extract any coords in the URL (lat,lon)
            m2 = re.search(r'(-?\d+\.\d+),(-?\d+\.\d+)', s0)
            if m2:
                lat = float(m2.group(1)); lon = float(m2.group(2))
                return {"type":"coords", "lat":lat, "lon":lon, "display_name": f"{lat},{lon} (from URL fallback)"}
            # otherwise return cleaned URL-decoded path/query as address
            combined = (parsed.path + " " + parsed.query).replace("/", " ").strip()
            combined = unquote_plus(combined)
            combined = re.sub(r'\s+', ' ', combined).strip()
            if combined:
                return {"type":"address", "address": combined}
        except Exception:
            # If parsing fails, fall through to treat as plain text
            pass

    # If the input itself looks like coords "lat,lon"
    mcoords = re.match(r'^\s*(-?\d+(\.\d+)?)\s*,\s*(-?\d+(\.\d+)?)\s*$', s0)
    if mcoords:
        return {"type":"coords", "lat": float(mcoords.group(1)), "lon": float(mcoords.group(3)), "display_name": f"{mcoords.group(1)},{mcoords.group(3)}"}
    # else return cleaned address string
    cleaned = re.sub(r'\s+', ' ', s0).strip()
    return {"type":"address", "address": cleaned}

# ----- Helper functions with caching -----
@st.cache_data(ttl=60*60)
def geocode(address_or_coord: str) -> Optional[Dict]:
    """
    Accepts either:
      - an address string
      - a coords string "lat,lon"
    But the caller should ideally run preprocess_input() first.
    """
    if not address_or_coord:
        return None
    txt = address_or_coord.strip()
    # if looks like coords (lat,lon)
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
    data = r.json()
    if not data:
        return None
    top = data[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top.get("display_name","")}

@st.cache_data(ttl=60*30)
def overpass_search(lat: float, lon: float, radius: int = 2000) -> List[Dict]:
    q = f"""
    [out:json][timeout:25];
    (
      node["amenity"="pharmacy"](around:{radius},{lat},{lon});
      way["amenity"="pharmacy"](around:{radius},{lat},{lon});
      relation["amenity"="pharmacy"](around:{radius},{lat},{lon});
      node["shop"="chemist"](around:{radius},{lat},{lon});
      way["shop"="chemist"](around:{radius},{lat},{lon});
      relation["shop"="chemist"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    r = requests.post(OVERPASS_URL, data=q.encode('utf-8'), headers=HEADERS, timeout=60)
    r.raise_for_status()
    data = r.json()
    results = []
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
        results.append(place)
    return results

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

# ----- Utility functions -----
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

# ----- Main UI flow -----
col_map, col_list = st.columns([2.2, 1])

# Preprocess the raw input first
processed = preprocess_input(raw_input)

with st.spinner("Resolving origin..."):
    origin = None
    try:
        if processed["type"] == "coords":
            origin = {"lat": processed["lat"], "lon": processed["lon"], "display_name": processed.get("display_name", f"{processed['lat']},{processed['lon']}")}
        else:
            # pass cleaned address to geocode
            origin = geocode(processed.get("address",""))
    except Exception as e:
        st.error(f"Geocoding error: {e}")

if origin is None:
    st.warning("No origin yet. Enter an address or coordinates in the sidebar and wait briefly.")
else:
    with st.spinner("Searching nearby pharmacies/chemists..."):
        try:
            raw_places = overpass_search(origin["lat"], origin["lon"], radius=radius_m)
        except Exception as e:
            st.error(f"Overpass error: {e}")
            raw_places = []

    if not raw_places:
        st.warning("No medical shops found in the chosen radius. Try increasing the radius or changing location.")
    else:
        places = sort_places_by_distance(origin, raw_places)
        show_places = places[: max(1, int(min(len(places), 300)))]
        route_places = places[: int(min(len(places), int(max_results)))]

        # left: map
        with col_map:
            st.subheader("Map")
            st.write(f"Origin: **{origin.get('display_name','(coords)')}** — showing {len(show_places)} POIs, drawing routes for top {len(route_places)}")
            selected_index = st.selectbox(
                "Select place to focus on (does not affect routes drawn)",
                options=list(range(len(show_places))),
                format_func=lambda i: f"{i+1}. {show_places[i]['name']} - {int(show_places[i].get('distance_m',0))} m",
                index=0
            )
            selected = show_places[int(selected_index)]

            m = folium.Map(location=[origin["lat"], origin["lon"]], zoom_start=14)
            folium.Marker([origin["lat"], origin["lon"]],
                          tooltip="Origin",
                          popup=origin.get("display_name","Origin"),
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
                popup_html += "<small>OSM tags: " + ", ".join([f"{k}={v}" for k,v in list(p.get('tags',{}).items())[:4]]) + "</small>"
                folium.Marker([p["lat"], p["lon"]], popup=folium.Popup(popup_html, max_width=300)).add_to(mc)

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
                    folium.PolyLine(locations=coords, color=color, weight=5, opacity=0.8,
                                    tooltip=f"{p.get('name')} ({int(p.get('distance_m',0))} m)",
                                    popup=folium.Popup(popup_html, max_width=300)).add_to(m)
                else:
                    folium.CircleMarker([p["lat"], p["lon"]], radius=4, color="gray", fill=True, fill_color="gray").add_to(m)

            folium.CircleMarker([selected["lat"], selected["lon"]], radius=9, color="red", fill=True, fill_color="red").add_to(m)

            html = m._repr_html_()
            st.components.v1.html(html, height=720, scrolling=True)

        # right: list and details
        with col_list:
            st.subheader("Nearby medical shops (top results)")
            df = pd.DataFrame([{
                "Name": p["name"],
                "Distance (m)": int(p.get("distance_m", 0)),
                "Address": p.get("address",""),
                "Phone": p.get("phone",""),
                "Hours": p.get("opening_hours","")
            } for p in places[:100]])
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
            st.markdown("**Actions**")
            st.markdown("- Click any route on the map and choose *Open in Google Maps (Directions)* to view full turn-by-turn directions.")
            st.markdown("- Reduce 'Max places to display' to lower OSRM calls if you see errors from the routing server.")
