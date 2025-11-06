import streamlit as st
import folium
from folium import IFrame
import requests
import math
from streamlit.components.v1 import html
from urllib.parse import quote_plus

# ---------- CONFIG ----------
OSRM_SERVER = "https://router.project-osrm.org"
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTR = "© OpenStreetMap contributors"
YELLOW_SHADES = ["#E0A800", "#FFD43B", "#FFEB99", "#FFF3BF"]
# ----------------------------

st.set_page_config(page_title="Route Visualizer (Working Links)", layout="wide")
st.title("🗺️ Multi-Route Visualizer (Working Google Maps Links)")

st.markdown("""
Enter coordinates below and click **Generate Map** to view routes.

✅ Green = Shortest route  
✅ Yellow shades = Other routes (darker → closer)  
✅ Orange = Government clinics  
✅ All popups now have **working Google Maps links**
""")

# ===== UI inputs =====
with st.sidebar:
    st.header("Inputs")
    origin_lat = st.number_input("Origin latitude", value=12.9715987, format="%.7f")
    origin_lon = st.number_input("Origin longitude", value=77.5945627, format="%.7f")

    st.subheader("Destinations (up to 5)")
    destinations = []
    for i in range(1, 6):
        lat = st.text_input(f"Dest {i} latitude", "")
        lon = st.text_input(f"Dest {i} longitude", "")
        if lat.strip() and lon.strip():
            try:
                destinations.append((float(lat), float(lon)))
            except ValueError:
                st.warning(f"Invalid coords for Dest {i} — ignoring.")

    st.subheader("Government clinics (up to 2)")
    govs = []
    for i in range(1, 3):
        glat = st.text_input(f"Gov {i} latitude", "")
        glon = st.text_input(f"Gov {i} longitude", "")
        if glat.strip() and glon.strip():
            try:
                govs.append((float(glat), float(glon)))
            except ValueError:
                st.warning(f"Invalid coords for Gov {i} — ignoring.")

# ===== Helpers =====
def get_osrm_route(src, dst, profile="driving"):
    coords_str = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        coords_lonlat = route["geometry"]["coordinates"]
        coords_latlon = [[pt[1], pt[0]] for pt in coords_lonlat]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception:
        return None, None, None

def google_maps_link(origin, dest):
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin[0]},{origin[1]}"
        f"&destination={dest[0]},{dest[1]}"
        f"&travelmode=driving"
    )

# ===== Main Button =====
if st.button("Generate Map"):
    if not destinations:
        st.error("Please enter at least one destination.")
        st.stop()

    origin = (origin_lat, origin_lon)
    m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

    # Mark origin
    origin_link = google_maps_link(origin, origin)
    popup_html = f"<b>Origin</b><br>{origin[0]}, {origin[1]}<br><a href='{origin_link}' target='_blank'>Open in Google Maps</a>"
    folium.Marker(
        location=origin,
        icon=folium.Icon(color="blue", icon="user"),
        popup=folium.Popup(IFrame(popup_html, width=250, height=100), max_width=250),
    ).add_to(m)

    # Compute routes
    routes = []
    for dst in destinations:
        coords, dist, dur = get_osrm_route(origin, dst)
        routes.append({"dest": dst, "coords": coords, "distance": dist or float("inf"), "duration": dur})

    routes.sort(key=lambda x: x["distance"])

    # Draw YELLOW routes first
    for i, r in enumerate(routes[1:], start=1):
        dst = r["dest"]
        gmap_link = google_maps_link(origin, dst)
        popup_html = (
            f"<b>Destination</b><br>{dst[0]}, {dst[1]}<br>"
            f"Distance: {int(r['distance']/1000)} km<br>"
            f"<a href='{gmap_link}' target='_blank'>Open directions in Google Maps</a>"
        )
        folium.Marker(
            location=dst,
            icon=folium.Icon(color="red"),
            popup=folium.Popup(IFrame(popup_html, width=250, height=120), max_width=250),
        ).add_to(m)

        if r["coords"]:
            shade = YELLOW_SHADES[min(i - 1, len(YELLOW_SHADES) - 1)]
            folium.PolyLine(
                r["coords"],
                color=shade,
                weight=5,
                opacity=0.8,
                tooltip=f"Route {i+1}: {int(r['distance']/1000)} km",
            ).add_to(m)

    # Draw GREEN (shortest) route last (on top)
    if routes:
        shortest = routes[0]
        dst0 = shortest["dest"]
        gmap_link = google_maps_link(origin, dst0)
        popup_html = (
            f"<b>Shortest Route</b><br>{dst0[0]}, {dst0[1]}<br>"
            f"Distance: {int(shortest['distance']/1000)} km<br>"
            f"<a href='{gmap_link}' target='_blank'>Open in Google Maps</a>"
        )
        folium.Marker(
            location=dst0,
            icon=folium.Icon(color="green"),
            popup=folium.Popup(IFrame(popup_html, width=250, height=120), max_width=250),
        ).add_to(m)

        if shortest["coords"]:
            folium.PolyLine(
                shortest["coords"],
                color="green",
                weight=7,
                opacity=0.95,
                tooltip="Shortest route (green)",
            ).add_to(m)

    # Add gov clinics (orange)
    for g in govs:
        link = google_maps_link(origin, g)
        popup_html = (
            f"<b>Gov Clinic</b><br>{g[0]}, {g[1]}<br>"
            f"<a href='{link}' target='_blank'>Open in Google Maps</a>"
        )
        folium.Marker(
            location=g,
            icon=folium.Icon(color="orange", icon="plus"),
            popup=folium.Popup(IFrame(popup_html, width=250, height=100), max_width=250),
        ).add_to(m)
        coords_g, dist_g, dur_g = get_osrm_route(origin, g)
        if coords_g:
            folium.PolyLine(coords_g, color="orange", weight=4, opacity=0.7).add_to(m)

    html(m._repr_html_(), height=720)
else:
    st.info("Enter coordinates and click **Generate Map** to visualize routes.")
