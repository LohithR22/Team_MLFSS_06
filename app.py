# app.py
"""
Streamlit app: Find nearby pharmacies / chemists using OpenStreetMap (Nominatim + Overpass)
and compute a driving route using OSRM. No API keys required.
"""
import streamlit as st
import requests
import math
from urllib.parse import urlencode
import folium
from folium.plugins import MarkerCluster
from streamlit.components.v1 import components
import pandas as pd
from typing import List, Dict, Tuple, Optional

# ----------------- Config -----------------
HEADERS = {"User-Agent": "streamlit-pharmacy-poc/1.0 (contact: you@example.com)"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_SERVER = "https://router.project-osrm.org"  # public demo server (light use)
# ------------------------------------------

st.set_page_config(page_title="Pharmacy Finder (OSM)", layout="wide")
st.title("Pharmacy / Medical Shop Finder — Streamlit POC")
st.markdown("Enter an address or `lat,lon`, choose search radius, then pick a shop to route to. Uses free OSM services.")

# ----- Sidebar controls -----
with st.sidebar:
    st.header("Search settings")
    address_input = st.text_input("Address or lat,lon", value="MG Road, Bangalore")
    radius_m = st.slider("Search radius (meters)", 200, 10000, 2000, step=100)
    max_results = st.number_input("Max places to display", min_value=1, max_value=300, value=50)
    mode = st.selectbox("Routing mode (OSRM profile)", options=["driving", "walking", "cycling"], index=0)
    st.write("Note: Public OSM endpoints are rate-limited. For production, self-host or use paid services.")

# ----- Helpers -----
def geocode(address_or_coord: str) -> Optional[Dict]:
    addr = address_or_coord.strip()
    # if looks like coords
    if ',' in addr:
        parts = [p.strip() for p in addr.split(',')]
        try:
            lat = float(parts[0]); lon = float(parts[1])
            return {"lat": lat, "lon": lon, "display_name": f"{lat},{lon}"}
        except Exception:
            pass
    params = {"q": addr, "format": "jsonv2", "limit": 1}
    url = NOMINATIM_URL + "?" + urlencode(params)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    top = data[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top.get("display_name","")}

def overpass_search(lat: float, lon: float, radius: int = 2000) -> List[Dict]:
    # Query both amenity=pharmacy and shop=chemist
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

def get_route_osrm(origin: Dict, dest: Dict, profile: str = "driving") -> Tuple[Optional[List[List[float]]], Optional[Dict]]:
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

def build_folium_map(origin: Dict, places: List[Dict], route_coords: Optional[List[List[float]]] = None, selected_place: Optional[Dict] = None) -> folium.Map:
    m = folium.Map(location=[origin["lat"], origin["lon"]], zoom_start=14)
    folium.Marker([origin["lat"], origin["lon"]], tooltip="Origin", popup=origin.get("display_name","Origin"),
                  icon=folium.Icon(color="blue", icon="user")).add_to(m)
    mc = MarkerCluster().add_to(m)
    for p in places:
        popup_html = f"<b>{p.get('name')}</b><br>"
        popup_html += f"Distance: {int(p.get('distance_m',0))} m<br>"
        if p.get("address"):
            popup_html += f"Address: {p.get('address')}<br>"
        if p.get("opening_hours"):
            popup_html += f"Hours: {p.get('opening_hours')}<br>"
        if p.get("phone"):
            popup_html += f"Phone: {p.get('phone')}<br>"
        if p.get("website"):
            popup_html += f"Website: <a href='{p.get('website')}' target='_blank'>{p.get('website')}</a><br>"
        popup_html += "<small>OSM tags: " + ", ".join([f"{k}={v}" for k,v in list(p.get('tags',{}).items())[:4]]) + "</small>"
        folium.Marker([p["lat"], p["lon"]], popup=folium.Popup(popup_html, max_width=300)).add_to(mc)
    if route_coords:
        folium.PolyLine(route_coords, weight=6, opacity=0.8).add_to(m)
        if selected_place:
            folium.CircleMarker([selected_place["lat"], selected_place["lon"]], radius=8,
                                color="red", fill=True, fill_color="red").add_to(m)
    return m

# ----- Main UI flow -----
col_map, col_list = st.columns([2.2, 1])

with st.spinner("Geocoding..."):
    origin = None
    try:
        if address_input and address_input.strip():
            origin = geocode(address_input)
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
        places = sort_places_by_distance(origin, raw_places)[: int(max_results)]
        # left: map
        with col_map:
            st.subheader("Map")
            # default select first
            selected_index = st.selectbox(
                "Select place to route to",
                options=list(range(len(places))),
                format_func=lambda i: f"{i+1}. {places[i]['name']} - {int(places[i]['distance_m'])} m",
                index=0
            )
            selected = places[int(selected_index)]
            # request route
            route_coords, summary = None, None
            try:
                route_coords, summary = get_route_osrm(origin, {"lat": selected["lat"], "lon": selected["lon"]}, profile=mode)
            except Exception as e:
                st.info(f"Routing unavailable or failed: {e}")
            m = build_folium_map(origin, places, route_coords=route_coords, selected_place=selected)
            # render folium
            html = m._repr_html_()
            st.components.v1.html(html, height=700, scrolling=True)

        # right: list and details
        with col_list:
            st.subheader("Results (top {})".format(len(places)))
            df = pd.DataFrame([{
                "Name": p["name"],
                "Distance (m)": int(p["distance_m"]),
                "Address": p.get("address",""),
                "Phone": p.get("phone",""),
                "Hours": p.get("opening_hours","")
            } for p in places])
            st.dataframe(df, use_container_width=True)
            st.markdown("### Selected place details")
            st.write(selected)
            if summary:
                st.success(f"Route summary: {int(summary['distance_m'])} m, approx {int(summary['duration_s']/60)} min")

# Footer / hints
st.markdown("---")
st.markdown("### Hints & next steps")
st.markdown(
    "- Public services (Nominatim, Overpass, OSRM) are fine for testing. For heavier/production use self-host or use paid providers.\n"
    "- To enable walking routes change the **Routing mode** to `walking` (OSRM server must support that profile)."
)
