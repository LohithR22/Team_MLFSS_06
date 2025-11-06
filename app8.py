# app.py
"""
Animated Delivery Assignment — corrected syntax & brace handling.

- Preserves map HTML in st.session_state so it doesn't disappear.
- On assignment: server picks agent & computes routes (agent->store->origin).
- The map shows blinking purple markers, 2s pause, then reveals the chosen agent's route.
- JS/CSS injection is built from a template and substituted safely (avoids f-string brace issues).
"""

import streamlit as st
import folium
from folium import IFrame
import requests, random, json, os
from urllib.parse import quote_plus
from streamlit.components.v1 import html as st_html
from branca.element import Element

# ---------- Config ----------
OSRM_SERVER = "https://router.project-osrm.org"
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTR = "© OpenStreetMap contributors"
YELLOW_SHADES = ["#E0A800", "#FFD43B", "#FFEB99"]
PURPLE_HEX = "#800080"
# ---------------------------

st.set_page_config(page_title="Animated Delivery Assignment (fixed)", layout="wide")
st.title("Animated Delivery Assignment — fixed syntax")

# ---------------- helpers ----------------
def parse_coord(txt: str):
    parts = [p.strip() for p in txt.split(",")]
    return (float(parts[0]), float(parts[1]))

def google_maps_link(origin, dest):
    params = {
        "api": "1",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest[0]},{dest[1]}",
        "travelmode": "driving"
    }
    return "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())

def get_osrm_route(src, dst):
    coords_str = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        geom = route["geometry"]["coordinates"]
        coords_latlon = [[p[1], p[0]] for p in geom]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception:
        return None, None, None

def compute_billing(total_m):
    if total_m is None: return None
    km = total_m/1000.0
    if km <= 5: return 20
    if km <= 10: return 30
    return 50

def make_iframe(title, latlon, dist=None, dur=None, gm=None):
    rows = [f"<b>{title}</b>", f"{latlon[0]:.6f}, {latlon[1]:.6f}"]
    if dist: rows.append(f"Distance: {dist/1000.0:.2f} km")
    if dur: rows.append(f"ETA: {int(dur/60)} min")
    if gm: rows.append(f"<a href='{gm}' target='_blank'>Open in Google Maps</a>")
    html_txt = "<br>".join(rows)
    return IFrame(html_txt, width=260, height=120)

# ------------- hidden agents loader -------------
def load_hidden_agents():
    # try st.secrets
    try:
        s = st.secrets.get("delivery_agents")
        if s:
            if isinstance(s, list):
                parsed = []
                for x in s:
                    if isinstance(x, str):
                        parsed.append(parse_coord(x))
                    elif isinstance(x, (list, tuple)):
                        parsed.append(tuple(x))
                return parsed
            try:
                arr = json.loads(s)
                parsed = [parse_coord(x) if isinstance(x, str) else tuple(x) for x in arr]
                return parsed
            except Exception:
                pass
    except Exception:
        pass
    # try local file
    try:
        if os.path.exists("delivery_agents.json"):
            with open("delivery_agents.json","r") as f:
                arr = json.load(f)
            parsed = [parse_coord(x) if isinstance(x, str) else tuple(x) for x in arr]
            return parsed
    except Exception:
        pass
    # fallback
    return [
        (12.9650, 77.6000),
        (12.9800, 77.5900),
        (12.9550, 77.6050),
        (12.9750, 77.6100),
        (12.9900, 77.5800)
    ]

hidden_agents = load_hidden_agents()

# ------------ session init ---------------
if "map_html" not in st.session_state:
    st.session_state["map_html"] = None
if "assignments" not in st.session_state:
    st.session_state["assignments"] = []  # persistent assignments

# -------------- UI inputs ----------------
with st.sidebar:
    st.header("Inputs (one-line lat,lon)")
    origin_input = st.text_input("Origin (blue)", value="12.9716, 77.5946")
    g1 = st.text_input("Green 1", "")
    g2 = st.text_input("Green 2", "")
    y1 = st.text_input("Yellow 1", "")
    y2 = st.text_input("Yellow 2", "")
    y3 = st.text_input("Yellow 3", "")
    r1 = st.text_input("Red 1", "")
    r2 = st.text_input("Red 2", "")
    gov1 = st.text_input("Gov 1", "")
    gov2 = st.text_input("Gov 2", "")

# parse helpers
def collect_coords(*txts):
    out=[]
    for t in txts:
        if t and t.strip():
            try: out.append(parse_coord(t))
            except: st.sidebar.error(f"Invalid coord: {t}")
    return out

try:
    origin = parse_coord(origin_input)
except Exception:
    st.sidebar.error("Invalid origin format. Use: lat, lon")
    st.stop()

greens = collect_coords(g1, g2)
yellows = collect_coords(y1, y2, y3)
reds = collect_coords(r1, r2)
govs = collect_coords(gov1, gov2)

stores_flat = [("green",c) for c in greens] + [("yellow",c) for c in yellows] + [("red",c) for c in reds]

# ------------- map builder -------------
def build_map_and_store_html(origin, greens, yellows, reds, govs, assignments, chosen_assignment=None):
    """
    Build folium map and put HTML into st.session_state['map_html'].
    If chosen_assignment is provided, we include the animation JS and the chosen route hidden initially.
    """
    m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

    # origin marker
    folium.Marker(location=origin, icon=folium.Icon(color="blue", icon="home"),
                  popup=folium.Popup(make_iframe("Origin", origin, gm=google_maps_link(origin, origin)), max_width=300)).add_to(m)

    # draw stores in order red -> yellow -> green for stacking
    for r in reds:
        folium.Marker(location=r, icon=folium.Icon(color="darkred"),
                      popup=folium.Popup(make_iframe("Red store", r, gm=google_maps_link(origin, r)), max_width=300)).add_to(m)
        coords, d, _ = get_osrm_route(origin, r)
        if coords:
            folium.PolyLine(coords, color="red", weight=3, opacity=0.45).add_to(m)

    for idx,y in enumerate(yellows):
        folium.Marker(location=y, icon=folium.Icon(color="gray"),
                      popup=folium.Popup(make_iframe("Yellow store", y, gm=google_maps_link(origin, y)), max_width=300)).add_to(m)
        coords, d, _ = get_osrm_route(origin, y)
        if coords:
            col = YELLOW_SHADES[min(idx, len(YELLOW_SHADES)-1)]
            folium.PolyLine(coords, color=col, weight=4, opacity=0.45).add_to(m)

    for g in greens:
        folium.Marker(location=g, icon=folium.Icon(color="green"),
                      popup=folium.Popup(make_iframe("Green store", g, gm=google_maps_link(origin, g)), max_width=300)).add_to(m)
        coords, d, _ = get_osrm_route(origin, g)
        if coords:
            folium.PolyLine(coords, color="green", weight=5, opacity=0.55).add_to(m)

    # government clinics
    for gv in govs:
        folium.Marker(location=gv, icon=folium.Icon(color="orange"),
                      popup=folium.Popup(make_iframe("Gov Clinic", gv, gm=google_maps_link(origin, gv)), max_width=300)).add_to(m)
        coords, d, _ = get_osrm_route(origin, gv)
        if coords:
            folium.PolyLine(coords, color="orange", weight=3, opacity=0.5).add_to(m)

    # draw previous assignments (visible)
    for a in assignments:
        folium.Marker(location=a["agent"], icon=folium.Icon(color="purple"),
                      popup=folium.Popup(make_iframe("Agent (assigned)", a["agent"], gm=google_maps_link(a["agent"], a["store"])), max_width=300)).add_to(m)
        if a.get("coords1"):
            folium.PolyLine(a["coords1"], color=PURPLE_HEX, weight=5, opacity=0.9).add_to(m)
        if a.get("coords2"):
            folium.PolyLine(a["coords2"], color=PURPLE_HEX, weight=7, opacity=0.95).add_to(m)
        folium.CircleMarker(location=a["store"], radius=6, color=PURPLE_HEX, fill=True, fill_color=PURPLE_HEX).add_to(m)

    # If we have a new chosen assignment, add DIV markers for all hidden agents and add hidden chosen-route polylines
    if chosen_assignment:
        # add div markers for each hidden agent (identifiable by id agent-<idx>)
        for idx, agent in enumerate(hidden_agents):
            html_icon = (
                "<div id='agent-{idx}' class='purple-marker' data-idx='{idx}' title='Agent {idx}' "
                "style='width:14px;height:14px;border-radius:14px;background:{purple};"
                "border:2px solid white;box-shadow:0 0 6px rgba(128,0,128,0.6)'>"
                "</div>"
            ).format(idx=idx, purple=PURPLE_HEX)
            folium.Marker(location=agent, icon=folium.DivIcon(html=html_icon)).add_to(m)

        # add chosen route polylines but hidden (opacity 0)
        if chosen_assignment.get("coords1"):
            folium.PolyLine(chosen_assignment["coords1"], color=PURPLE_HEX, weight=5, opacity=0.0).add_to(m)
        if chosen_assignment.get("coords2"):
            folium.PolyLine(chosen_assignment["coords2"], color=PURPLE_HEX, weight=7, opacity=0.0).add_to(m)

        # chosen agent visible marker
        chosen_agent = chosen_assignment["agent"]
        chosen_html = (
            "<div id='agent-chosen' class='purple-marker chosen' title='Chosen agent' "
            "style='width:18px;height:18px;border-radius:18px;background:{purple};"
            "border:2px solid yellow;box-shadow:0 0 8px rgba(0,0,0,0.6)'></div>"
        ).format(purple=PURPLE_HEX)
        folium.Marker(location=chosen_agent, icon=folium.DivIcon(html=chosen_html)).add_to(m)

        # invisible store highlight (so JS can detect it if needed)
        folium.CircleMarker(location=chosen_assignment["store"], radius=6, color=PURPLE_HEX,
                            fill=True, fill_color=PURPLE_HEX, opacity=0.0).add_to(m)

        # prepare JS/CSS template and substitute dynamic values
        script_template = """
        <style>
        .purple-marker {{ transition: transform 0.6s ease, opacity 0.6s ease; opacity:1; }}
        .purple-marker.blink {{ transform: scale(1.4); opacity:0.3; }}
        .purple-marker.selected {{ animation: pulse 1s infinite; box-shadow: 0 0 12px rgba(128,0,128,0.9); }}
        @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.25); }} 100% {{ transform: scale(1); }} }}
        </style>
        <script>
        (function(){{
            try {{
                let markers = [];
                const totalAgents = TOTAL_AGENTS;
                for (let i=0;i<totalAgents;i++) {{
                    let el = document.getElementById('agent-'+i);
                    if (el) markers.push(el);
                }}
                let chosenEl = document.getElementById('agent-chosen');
                const cycles = 5;
                const interval_ms = 700;
                let cycle = 0;
                let on = false;
                let blinkCount = 0;
                let blinkInterval = setInterval(function(){{
                    on = !on;
                    markers.forEach(function(m){{ if(on) m.classList.add('blink'); else m.classList.remove('blink'); }});
                    blinkCount += 1;
                    if (blinkCount >= cycles*2) {{
                        clearInterval(blinkInterval);
                        setTimeout(function(){{
                            if (chosenEl) chosenEl.classList.add('selected');
                            // reveal purple polylines (stroke color matching PURPLE_HEX)
                            const svgPaths = document.querySelectorAll('path.leaflet-interactive');
                            svgPaths.forEach(function(p) {{
                                const stroke = p.getAttribute('stroke') || p.style.stroke;
                                if (stroke && (stroke.toLowerCase() === 'PURPLE_HEX' || stroke.toLowerCase() === '{purple_lower}')) {{
                                    p.setAttribute('stroke-opacity', '0.95');
                                    p.style.strokeOpacity = 0.95;
                                    p.style.display = 'block';
                                    if (p.parentNode) p.parentNode.appendChild(p);
                                }}
                            }});
                        }}, 2000);
                    }}
                }}, interval_ms);
            }} catch (e) {{
                console.error('Animation error', e);
            }}
        }})();
        </script>
        """

        script_filled = script_template.replace("TOTAL_AGENTS", str(len(hidden_agents))).replace("PURPLE_HEX", PURPLE_HEX).replace("{purple_lower}", PURPLE_HEX.lower())
        # wrap the script in Jinja "raw" so Jinja doesn't try to parse curly braces inside the JS/CSS
        safe_script = "{% raw %}\n" + script_filled + "\n{% endraw %}"
        m.get_root().html.add_child(Element(safe_script))


    # fit bounds (include hidden agents if chosen_assignment to ensure visibility)
    all_points = [origin] + greens + yellows + reds + govs
    if chosen_assignment:
        all_points += hidden_agents
        all_points.append(chosen_assignment["agent"])
        all_points.append(chosen_assignment["store"])
    else:
        for a in assignments:
            all_points.append(a["agent"])
            all_points.append(a["store"])

    try:
        lats = [p[0] for p in all_points if p]
        lons = [p[1] for p in all_points if p]
        if lats and lons:
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20,20))
    except Exception:
        pass

    st.session_state["map_html"] = m._repr_html_()

# -------------- Buttons and flow --------------
col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("Generate Map (preserve)"):
        build_map_and_store_html(origin, greens, yellows, reds, govs, st.session_state["assignments"], chosen_assignment=None)
        st.success("Map generated and preserved. It will remain visible across interactions.")

with col2:
    if st.button("Assign Delivery Agent (animate + reveal)"):
        if not stores_flat:
            st.warning("Enter stores (green/yellow/red) in the sidebar and press Generate Map first.")
        else:
            pass  # handled with confirm button below

with col3:
    if st.button("Clear Map & Assignments"):
        st.session_state["map_html"] = None
        st.session_state["assignments"] = []
        st.success("Cleared map and assignments.")

# store selection UI
if stores_flat:
    st.subheader("Select a store to assign an agent to")
    labels = [f"{i+1}. [{c[0].upper()}] {c[1][0]:.6f}, {c[1][1]:.6f}" for i,c in enumerate(stores_flat)]
    sel = st.selectbox("Store", options=list(range(len(labels))), format_func=lambda i: labels[i])
    if st.button("Confirm & Animate Assignment"):
        chosen_store = stores_flat[sel][1]
        # pick random hidden agent
        agent = random.choice(hidden_agents)
        coords1, d1, t1 = get_osrm_route(agent, chosen_store)
        coords2, d2, t2 = get_osrm_route(chosen_store, origin)
        total = None
        if d1 is not None and d2 is not None:
            total = d1 + d2
        charge = compute_billing(total) if total is not None else None

        assignment = {
            "agent": agent,
            "store": chosen_store,
            "coords1": coords1,
            "dist1": d1,
            "dur1": t1,
            "coords2": coords2,
            "dist2": d2,
            "dur2": t2,
            "total": total,
            "charge": charge
        }
        # append assignment to persistent list
        st.session_state["assignments"].append(assignment)
        # build map with chosen_assignment set so JS animation & reveal is embedded
        build_map_and_store_html(origin, greens, yellows, reds, govs, st.session_state["assignments"][:-1], chosen_assignment=assignment)
        st.success("Assignment in progress — watch the map animation. Billing shown below.")
        if total is not None:
            st.subheader("Delivery summary")
            st.write(f"Agent (hidden coords): {agent[0]:.6f}, {agent[1]:.6f}")
            st.write(f"Store: {chosen_store[0]:.6f}, {chosen_store[1]:.6f}")
            st.write(f"Total route distance: {total/1000.0:.3f} km")
            st.write(f"Estimated charge: Rs. {charge}")
        else:
            st.warning("OSRM failed to compute one or both legs; billing unavailable.")

# ---------- render preserved map ----------
st.subheader("Map (preserved)")
if st.session_state.get("map_html"):
    st_html(st.session_state["map_html"], height=720)
else:
    st.info("No map generated yet. Click 'Generate Map (preserve)' or assign after entering stores.")
