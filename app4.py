# import streamlit as st
# import folium
# from folium import Popup
# import requests
# import math
# from streamlit.components.v1 import html

# # ---------- CONFIG ----------
# OSRM_SERVER = "https://router.project-osrm.org"
# TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
# ATTR = "© OpenStreetMap contributors"
# # ----------------------------

# st.set_page_config(page_title="Route Visualizer", layout="wide")
# st.title("🗺️ Multi-Route Visualizer (OSM + Streamlit)")

# st.markdown("""
# Enter coordinates below:
# - **Origin** (1 location)
# - **Destinations** (up to 5)
# - **Government Clinics** (up to 2)

# Each line you enter will be mapped as routes using OpenStreetMap and OSRM.
# No API key needed.
# """)

# # ========== UI Inputs ==========
# st.sidebar.header("Enter Coordinates")

# # origin
# origin_lat = st.sidebar.number_input("Origin Latitude", value=12.9716, format="%.6f")
# origin_lon = st.sidebar.number_input("Origin Longitude", value=77.5946, format="%.6f")

# # destinations
# st.sidebar.subheader("Destination Coordinates (up to 5)")
# destinations = []
# for i in range(1, 6):
#     lat = st.sidebar.text_input(f"Destination {i} Latitude", "")
#     lon = st.sidebar.text_input(f"Destination {i} Longitude", "")
#     if lat and lon:
#         try:
#             destinations.append((float(lat), float(lon)))
#         except ValueError:
#             st.sidebar.warning(f"Invalid lat/lon for Destination {i}")

# # government clinics
# st.sidebar.subheader("Government Clinics (up to 2)")
# gov_locations = []
# for i in range(1, 3):
#     lat = st.sidebar.text_input(f"Gov Clinic {i} Latitude", "")
#     lon = st.sidebar.text_input(f"Gov Clinic {i} Longitude", "")
#     if lat and lon:
#         try:
#             gov_locations.append((float(lat), float(lon)))
#         except ValueError:
#             st.sidebar.warning(f"Invalid lat/lon for Gov Clinic {i}")

# # choose color
# main_color = st.sidebar.color_picker("Choose Base Color for Routes", "#3388ff")

# # convert all inputs into dict
# route_dict = {main_color: [(origin_lat, origin_lon)] + destinations}
# if gov_locations:
#     route_dict["orange"] = gov_locations

# st.sidebar.markdown("### Dictionary to be used:")
# st.sidebar.write(route_dict)

# # ========== Helper Functions ==========
# def haversine_m(lat1, lon1, lat2, lon2):
#     R = 6371000
#     phi1, phi2 = math.radians(lat1), math.radians(lat2)
#     dphi = math.radians(lat2 - lat1)
#     dlambda = math.radians(lon2 - lon1)
#     a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
#     return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# def get_osrm_route(src, dst):
#     url = f"{OSRM_SERVER}/route/v1/driving/{src[1]},{src[0]};{dst[1]},{dst[0]}?overview=full&geometries=geojson"
#     r = requests.get(url, timeout=20)
#     r.raise_for_status()
#     data = r.json()
#     if data.get("code") == "Ok" and data["routes"]:
#         route = data["routes"][0]
#         coords = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]
#         dist = route["distance"]
#         dur = route["duration"]
#         return coords, dist, dur
#     return None, None, None

# def google_maps_link(src, dst):
#     return f"https://www.google.com/maps/dir/?api=1&origin={src[0]},{src[1]}&destination={dst[0]},{dst[1]}"

# # ========== Route Plotting ==========
# if st.button("Generate Map"):
#     if not destinations:
#         st.error("Please enter at least one destination.")
#         st.stop()

#     origin = (origin_lat, origin_lon)
#     m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

#     # markers for origin
#     folium.Marker(origin, tooltip="Origin", icon=folium.Icon(color="blue")).add_to(m)

#     # calculate all route distances
#     routes_data = []
#     for dest in destinations:
#         coords, dist, dur = get_osrm_route(origin, dest)
#         if coords:
#             routes_data.append({"dest": dest, "coords": coords, "distance": dist, "duration": dur})

#     if not routes_data:
#         st.warning("No valid routes found.")
#         st.stop()

#     # sort routes by distance
#     routes_data.sort(key=lambda x: x["distance"])

#     # assign colors: shortest=green, others shades of yellow
#     yellow_shades = ["#FFD700", "#FFE135", "#FFF380", "#FFFF99"]
#     for i, route in enumerate(routes_data):
#         if i == 0:
#             color = "green"
#         else:
#             color = yellow_shades[min(i - 1, len(yellow_shades) - 1)]
#         dst = route["dest"]
#         popup_html = f"""
#         <b>Route to:</b> {dst}<br>
#         Distance: {int(route['distance']/1000)} km<br>
#         Duration: {int(route['duration']/60)} min<br>
#         <a href="{google_maps_link(origin, dst)}" target="_blank">Open in Google Maps</a>
#         """
#         folium.PolyLine(route["coords"], color=color, weight=6, opacity=0.9, popup=Popup(popup_html, max_width=300)).add_to(m)
#         folium.Marker(dst, tooltip=f"Destination ({int(route['distance']/1000)} km)", icon=folium.Icon(color="red")).add_to(m)

#     # government clinics (orange)
#     for g in gov_locations:
#         folium.Marker(g, tooltip="Gov Clinic", icon=folium.Icon(color="orange")).add_to(m)
#         try:
#             coords, dist, dur = get_osrm_route(origin, g)
#             if coords:
#                 folium.PolyLine(coords, color="orange", weight=4, opacity=0.7).add_to(m)
#         except Exception:
#             continue

#     html(m._repr_html_(), height=700)

# else:
#     st.info("Enter coordinates and click **Generate Map** to visualize routes.")


# app.py
"""
Streamlit app: Multi-route visualizer (OSM + OSRM)
Fixes:
 - Google Maps direction links reliably open with origin/destination
 - Draw order: draw yellow (other) routes first, then draw the green (shortest) route last so green is on top
 - Pinpoint markers precisely and include map popups with a working Google Maps link
Notes: Uses public OSRM (rate-limited). For heavy use self-host OSRM.
"""
import streamlit as st
import folium
from folium import Popup
import requests
import math
from streamlit.components.v1 import html
from urllib.parse import urlencode, quote_plus

# ---------- CONFIG ----------
OSRM_SERVER = "https://router.project-osrm.org"
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTR = "© OpenStreetMap contributors"
# Yellow shades from darker to lighter (for non-shortest routes)
YELLOW_SHADES = ["#E0A800", "#FFD43B", "#FFEB99", "#FFF3BF"]
# ----------------------------

st.set_page_config(page_title="Route Visualizer (fixed)", layout="wide")
st.title("🗺️ Multi-Route Visualizer (OSM + OSRM) — Fixed")

st.markdown("""
Enter coordinates:
- **Origin** (lat,lon)
- **Up to 5 destinations** (lat,lon)
- **Up to 2 government clinics** (lat,lon)

Click **Generate Map**. Each route popup contains a working **Google Maps Directions** link.
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

    st.markdown("---")
    st.info("Public OSRM endpoint is rate-limited. If routes fail, reduce destination count or self-host OSRM.")

# ===== helpers =====
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_osrm_route(src, dst, profile="driving"):
    """
    src, dst are tuples (lat, lon)
    Returns (coords_list_of_[lat,lon], distance_m, duration_s) or (None, None, None) on failure.
    """
    # format lon,lat for OSRM
    coords_str = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        coords_lonlat = route["geometry"]["coordinates"]  # [lon,lat] pairs
        coords_latlon = [[pt[1], pt[0]] for pt in coords_lonlat]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception as e:
        # don't crash; return failure
        return None, None, None

def google_maps_directions_link(origin, dest, travelmode="driving"):
    """
    origin/dest tuples are (lat, lon).
    Returns a safe Google Maps Directions URL using the Maps URLs format.
    """
    params = {
        "api": "1",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest[0]},{dest[1]}",
        "travelmode": travelmode
    }
    # urlencode but keep commas
    # build manually but quote_plus values
    url = "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
    return url

# ===== build map on button =====
if st.button("Generate Map"):
    origin = (origin_lat, origin_lon)
    if not destinations:
        st.error("Please provide at least one destination.")
        st.stop()

    # Precise markers & base map
    m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

    # origin marker (distinct)
    folium.CircleMarker(location=origin, radius=7, color="blue", fill=True, fill_color="blue",
                        popup=Popup(f"<b>Origin</b><br>{origin[0]:.7f}, {origin[1]:.7f}<br>"
                                    f"<a href='{google_maps_directions_link(origin, origin)}' target='_blank'>Open origin in Google Maps</a>",
                                    max_width=300, parse_html=True)).add_to(m)

    # compute routes data (distance) for all destinations
    routes = []
    for dst in destinations:
        coords, dist, dur = get_osrm_route(origin, dst)
        # even if routing fails, still add marker, but route may be None
        routes.append({"dest": dst, "coords": coords, "distance": dist if dist else float("inf"), "duration": dur})

    # sort by distance (smallest first). If OSRM failed (inf), they'll go last.
    routes.sort(key=lambda x: x["distance"])

    # Draw non-shortest routes (yellow shades) FIRST so they are underlay
    if len(routes) > 1:
        for idx in range(1, len(routes)):
            r = routes[idx]
            dst = r["dest"]
            # marker for destination
            folium.CircleMarker(location=dst, radius=5, color="red", fill=True, fill_color="red",
                                popup=Popup(f"<b>Destination</b><br>{dst[0]:.7f}, {dst[1]:.7f}<br>"
                                            f"<a href='{google_maps_directions_link(origin, dst)}' target='_blank'>Open directions in Google Maps</a>",
                                            max_width=300, parse_html=True)).add_to(m)
            # draw route if available
            if r["coords"]:
                # choose yellow shade based on index (closer = darker)
                shade = YELLOW_SHADES[min(idx - 1, len(YELLOW_SHADES) - 1)]
                folium.PolyLine(locations=r["coords"], color=shade, weight=5, opacity=0.8,
                                tooltip=f"Route to {dst} — {int(r['distance'])//1000} km").add_to(m)

    # Draw the shortest route LAST so it is on top (green, thicker)
    shortest = routes[0]
    dst0 = shortest["dest"]
    folium.CircleMarker(location=dst0, radius=6, color="darkgreen", fill=True, fill_color="green",
                        popup=Popup(f"<b>Shortest Destination</b><br>{dst0[0]:.7f}, {dst0[1]:.7f}<br>"
                                    f"<a href='{google_maps_directions_link(origin, dst0)}' target='_blank'>Open directions in Google Maps</a>",
                                    max_width=300, parse_html=True)).add_to(m)
    if shortest["coords"]:
        # draw green on top with thicker weight
        folium.PolyLine(locations=shortest["coords"], color="green", weight=7, opacity=0.95,
                        tooltip=f"Shortest route — {int(shortest['distance'])//1000} km").add_to(m)

    # Government clinics: always orange markers and orange (thin) routes underneath/alongside
    for g in govs:
        folium.Marker(location=g, icon=folium.Icon(color="orange", icon="plus"), 
                      popup=Popup(f"<b>Gov Clinic</b><br>{g[0]:.7f}, {g[1]:.7f}<br>"
                                  f"<a href='{google_maps_directions_link(origin, g)}' target='_blank'>Open directions in Google Maps</a>",
                                  max_width=300, parse_html=True)).add_to(m)
        # try route for gov
        coords_g, dist_g, dur_g = get_osrm_route(origin, g)
        if coords_g:
            folium.PolyLine(locations=coords_g, color="orange", weight=4, opacity=0.7,
                            tooltip=f"Gov clinic route — {int(dist_g)//1000} km").add_to(m)

    # final rendering
    st.markdown("**Map**")
    st.markdown("- Green = shortest route (drawn on top).")
    st.markdown("- Yellow shades = other routes (darker = closer).")
    st.markdown("- Orange = government clinics.")
    html(m._repr_html_(), height=720)

else:
    st.info("Fill inputs at the left and click **Generate Map**.")
