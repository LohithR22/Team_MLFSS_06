# app.py
"""
Streamlit app implementing:
- origin (blue)
- 2 green stores, 3 yellow stores, 2 red stores (entered as one-line "lat, lon")
- government clinics (orange)
- hidden delivery agents (purple) loaded from st.secrets or local file
- select a particular route; assign a random purple agent; compute agent->store + store->origin route and billing
- modular: plotting/routing helpers in plot_routes.py
"""

import streamlit as st
import folium
from folium import Popup
from folium import IFrame
from streamlit.components.v1 import html
import json, random, os

from plot_routes import (
    parse_coord,
    get_osrm_route,
    google_maps_link,
    compute_billing,
    make_popup_html
)

st.set_page_config(page_title="Delivery Route Simulator", layout="wide")
st.title("Delivery Route Simulator — color-coded")

st.markdown("""
**Workflow**
1. Enter origin (blue) as `lat, lon`.
2. Enter: 2 green stores, 3 yellow stores, 2 red stores (each as `lat, lon` on one line).
3. Optionally enter government clinics (orange).
4. Click *Generate Map* to view routes.
5. Click a route row in the table and then click **Assign Delivery Agent** to randomly choose a purple agent (hidden list) that will go to the chosen store then to the origin. Billing displayed below.
""")

# -------------------------
# Sidebar inputs (one-line)
# -------------------------
with st.sidebar:
    st.header("Inputs (one-line coords 'lat, lon')")

    origin_text = st.text_input("Origin (blue)", value="12.9716, 77.5946")

    st.markdown("**Green stores (2)**")
    green1 = st.text_input("Green 1", "")
    green2 = st.text_input("Green 2", "")

    st.markdown("**Yellow stores (3)**")
    yellow1 = st.text_input("Yellow 1", "")
    yellow2 = st.text_input("Yellow 2", "")
    yellow3 = st.text_input("Yellow 3", "")

    st.markdown("**Red stores (2)**")
    red1 = st.text_input("Red 1", "")
    red2 = st.text_input("Red 2", "")

    st.markdown("**Government clinics (orange) - optional**")
    gov1 = st.text_input("Gov 1", "")
    gov2 = st.text_input("Gov 2", "")

    st.markdown("---")
    st.info("Delivery agent (purple) locations are loaded from secrets or a local file and not shown here.")

# -------------------------
# Load hidden delivery agents (purple)
# -------------------------
def load_hidden_agents():
    # 1) try streamlit secrets: set st.secrets['delivery_agents'] as JSON array of "lat, lon" strings
    try:
        s = st.secrets.get("delivery_agents")
        if s:
            # if it's a list already
            if isinstance(s, list):
                parsed = [parse_coord(x) if isinstance(x,str) else tuple(x) for x in s]
                return parsed
            # if it's a json string
            try:
                arr = json.loads(s)
                parsed = [parse_coord(x) if isinstance(x,str) else tuple(x) for x in arr]
                return parsed
            except Exception:
                pass
    except Exception:
        pass

    # 2) try local file delivery_agents.json with array of strings or arrays
    try:
        if os.path.exists("delivery_agents.json"):
            with open("delivery_agents.json","r") as f:
                arr = json.load(f)
            parsed = [parse_coord(x) if isinstance(x,str) else tuple(x) for x in arr]
            return parsed
    except Exception:
        pass

    # 3) fallback hidden default list (used only if no secret/file is found)
    # NOTE: This is still "hidden" because we don't show it on UI
    fallback = [
        (12.9650, 77.6000),
        (12.9800, 77.5900),
        (12.9550, 77.6050),
        (12.9750, 77.6100),
        (12.9900, 77.5800)
    ]
    return fallback

hidden_agents = load_hidden_agents()

# -------------------------
# Parse inputs into lists
# -------------------------
def collect_list(*items):
    out=[]
    for it in items:
        if it and isinstance(it,str) and it.strip():
            try:
                out.append(parse_coord(it))
            except Exception:
                st.sidebar.error(f"Invalid coord: {it}")
    return out

try:
    origin = parse_coord(origin_text)
except Exception:
    st.sidebar.error("Invalid origin format. Use: lat, lon")
    st.stop()

greens = collect_list(green1, green2)
yellows = collect_list(yellow1, yellow2, yellow3)
reds = collect_list(red1, red2)
govs = collect_list(gov1, gov2)

# Build dictionary mapping colors to coordinate lists (as you asked)
# color keys: 'blue' (origin only), 'green', 'yellow', 'red', 'purple' (hidden agents)
color_dict = {
    "blue": [origin],
    "green": greens,
    "yellow": yellows,
    "red": reds,
    "purple": hidden_agents  # hidden; not in UI
}

# -------------------------
# Validate counts
# -------------------------
if len(color_dict["green"]) != 2:
    st.sidebar.warning("Please enter exactly 2 green coordinates (or leave empty to skip).")

if len(color_dict["yellow"]) != 3:
    st.sidebar.warning("Please enter exactly 3 yellow coordinates (or leave empty to skip).")

if len(color_dict["red"]) != 2:
    st.sidebar.warning("Please enter exactly 2 red coordinates (or leave empty to skip).")

# -------------------------
# Generate map (base)
# -------------------------
if st.button("Generate Map"):
    # create folium map
    m = folium.Map(location=origin, zoom_start=13, tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", attr="© OpenStreetMap contributors")

    # place blue origin marker
    origin_link = google_maps_link(origin, origin)
    iframe = make_popup_html("Origin (blue)", origin, gm_link=origin_link)
    folium.Marker(location=origin, icon=folium.Icon(color="blue", icon="home"), popup=Popup(iframe, max_width=300)).add_to(m)

    # helper to draw lists with given marker color
    def place_markers(coord_list, marker_color, title_prefix):
        for idx, c in enumerate(coord_list):
            gm = google_maps_link(origin, c)
            iframe = make_popup_html(f"{title_prefix} {idx+1}", c, gm_link=gm)
            folium.Marker(location=c, icon=folium.Icon(color=marker_color), popup=Popup(iframe, max_width=300)).add_to(m)

    # place green/yellow/red/gov markers
    place_markers(color_dict["green"], "green", "Green store")
    place_markers(color_dict["yellow"], "red", "Yellow store")  # use red icon for yellow stores so they show clearly; polyline color will be yellow
    place_markers(color_dict["red"], "darkred", "Red store")
    place_markers(govs, "orange", "Gov Clinic")

    # draw simple polylines from origin to each store (color-coded), but NOT the delivery agent yet
    # For visibility: draw red and others first, then yellow and green on top in chosen stacking order
    # We'll draw non-chosen store routes with thin lines
    poly_order = []
    # add red stores first
    for r in color_dict["red"]:
        coords, dist, dur = get_osrm_route(origin, r)
        color = "red"
        if coords:
            folium.PolyLine(coords, color=color, weight=4, opacity=0.6, tooltip=f"Red store {r}").add_to(m)
    # add yellow stores next (yellow shade)
    yellow_shades = ["#E0A800", "#FFD43B", "#FFEB99"]
    for idx, y in enumerate(color_dict["yellow"]):
        coords, dist, dur = get_osrm_route(origin, y)
        color = yellow_shades[min(idx, len(yellow_shades)-1)]
        if coords:
            folium.PolyLine(coords, color=color, weight=5, opacity=0.6, tooltip=f"Yellow store {y}").add_to(m)
    # add green stores on top of those
    for g in color_dict["green"]:
        coords, dist, dur = get_osrm_route(origin, g)
        if coords:
            folium.PolyLine(coords, color="green", weight=6, opacity=0.7, tooltip=f"Green store {g}").add_to(m)

    # show hidden purple agent locations (do not show coordinates in UI) as small purple markers on map? 
    # You asked hidden; I won't render them by default. But for debugging you can uncomment the following:
    # for a in hidden_agents: folium.CircleMarker(location=a, color="purple", radius=3, fill=True, fill_color="purple").add_to(m)

    # Render map
    st.subheader("Map (click store marker for Google Maps link)")
    html(m._repr_html_(), height=720)

    # Prepare a flat list of all stores (green + yellow + red) for selection in a table
    stores = []
    for color in ["green","yellow","red"]:
        for idx, c in enumerate(color_dict[color]):
            stores.append({"color": color, "index": idx, "coord": c})

    # show stores table for selection
    st.subheader("Stores (select one to assign a delivery agent)")
    rows = []
    for i, s in enumerate(stores):
        rows.append(f"{i+1}. [{s['color'].upper()}] {s['coord'][0]:.6f}, {s['coord'][1]:.6f}")
    selected_store_idx = st.selectbox("Choose store (by row)", options=list(range(len(rows))), format_func=lambda i: rows[i] if rows else "No stores")
    st.write("Selected:", rows[selected_store_idx] if rows else "None")

    # Button to assign delivery agent (purple) to the selected store
    if st.button("Assign Delivery Agent to Selected Store"):
        # pick a random purple agent from hidden list
        agent = random.choice(hidden_agents)
        st.success(f"Assigned agent at (hidden) location (lat,lon): {agent[0]:.6f}, {agent[1]:.6f}")

        # compute route agent -> store, then store -> origin
        store = stores[selected_store_idx]["coord"]
        coords1, dist1, dur1 = get_osrm_route(agent, store)
        coords2, dist2, dur2 = get_osrm_route(store, origin)

        total_dist = None
        total_dur = None
        if dist1 is not None and dist2 is not None:
            total_dist = dist1 + dist2
            total_dur = (dur1 or 0) + (dur2 or 0)

        # draw a fresh map to show agent route (agent marker visible now)
        m2 = folium.Map(location=origin, zoom_start=13, tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", attr="© OpenStreetMap contributors")
        # origin
        iframe_o = make_popup_html("Origin", origin, gm_link=google_maps_link(origin, origin))
        folium.Marker(location=origin, icon=folium.Icon(color="blue", icon="home"), popup=Popup(iframe_o, max_width=300)).add_to(m2)
        # store marker
        iframe_s = make_popup_html("Selected Store", store, gm_link=google_maps_link(origin, store))
        folium.Marker(location=store, icon=folium.Icon(color="green" if stores[selected_store_idx]['color']=="green" else "red"), popup=Popup(iframe_s, max_width=300)).add_to(m2)
        # government clinics
        for g in govs:
            iframe_g = make_popup_html("Gov Clinic", g, gm_link=google_maps_link(origin, g))
            folium.Marker(location=g, icon=folium.Icon(color="orange"), popup=Popup(iframe_g, max_width=300)).add_to(m2)

        # draw previously drawn non-agent routes (thin, just for context)
        # red stores
        for r in color_dict["red"]:
            coords_r, d_r, _ = get_osrm_route(origin, r)
            if coords_r:
                folium.PolyLine(coords_r, color="red", weight=3, opacity=0.45).add_to(m2)
        # yellow
        y_shades = ["#E0A800", "#FFD43B", "#FFEB99"]
        for idx, y in enumerate(color_dict["yellow"]):
            coords_y, d_y, _ = get_osrm_route(origin, y)
            if coords_y:
                folium.PolyLine(coords_y, color=y_shades[min(idx, len(y_shades)-1)], weight=4, opacity=0.45).add_to(m2)
        # green
        for g in color_dict["green"]:
            coords_gf, dg, _ = get_osrm_route(origin, g)
            if coords_gf:
                folium.PolyLine(coords_gf, color="green", weight=5, opacity=0.55).add_to(m2)

        # now draw agent->store (purple) then store->origin (purple or thick highlight)
        if coords1:
            folium.PolyLine(coords1, color="purple", weight=5, opacity=0.9, tooltip="Agent -> Store").add_to(m2)
        if coords2:
            folium.PolyLine(coords2, color="purple", weight=7, opacity=0.95, tooltip="Store -> Origin").add_to(m2)

        # show agent marker (purple) with Google Maps link from agent -> store
        iframe_a = make_popup_html("Delivery Agent (assigned)", agent, None, None, gm_link=google_maps_link(agent, store))
        folium.Marker(location=agent, icon=folium.Icon(color="purple"), popup=Popup(iframe_a, max_width=300)).add_to(m2)

        # show totals & billing
        if total_dist is not None:
            km, charge = compute_billing(total_dist)
            st.subheader("Delivery summary")
            st.write(f"Agent at (hidden): {agent[0]:.6f}, {agent[1]:.6f}")
            st.write(f"Store: {store[0]:.6f}, {store[1]:.6f}")
            st.write(f"Total route distance: {km:.3f} km")
            st.write(f"Estimated charge: Rs. {charge}")
            # show breakdown
            st.write(f"Breakdown: leg1 {dist1/1000.0 if dist1 else 'N/A'} km, leg2 {dist2/1000.0 if dist2 else 'N/A'} km")
        else:
            st.warning("Could not compute full OSRM routes for agent->store->origin. Billing unavailable.")

        # render map with agent route
        html(m2._repr_html_(), height=720)

    else:
        st.info("Pick a store row and click 'Assign Delivery Agent to Selected Store'.")

else:
    st.info("Fill inputs in the sidebar and click 'Generate Map' to start.")
