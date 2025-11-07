"""
Delivery Map — Core Python Functions
Pure Python implementation without Streamlit dependencies.
All functionality extracted into callable functions for backend use.
"""

import folium
from folium import IFrame, Popup
from branca.element import Element
import requests
import random
import json
import math
from urllib.parse import quote_plus

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

# ------------------ Known shop DB ------------------
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

# Hardcoded GOV initiatives with full addresses
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

# -------------- Helper Functions ----------------
def parse_coord(txt: str):
    """Parse coordinate string 'lat, lon' into tuple (lat, lon)"""
    parts = [p.strip() for p in txt.split(",")]
    return (float(parts[0]), float(parts[1]))

def haversine_m(p1, p2):
    """Calculate haversine distance between two points in meters"""
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
            return {"name": shop["name"], "latlon": shop["latlon"], "distance_m": d}
    return None

def google_maps_link(origin, dest):
    """Generate Google Maps directions link"""
    params = {
        "api": "1",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest[0]},{dest[1]}",
        "travelmode": "driving"
    }
    return "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())

def get_osrm_route(src, dst, profile="driving"):
    """Get route from OSRM server. Returns (coords_list, distance_m, duration_s) or (None, None, None)"""
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
    """Compute billing charge from total distance in meters"""
    if total_m is None:
        return None
    km = total_m/1000.0
    if km <= 5.0:
        return 20
    elif km <= 10.0:
        return 30
    else:
        return 50

def make_popup_html(title, point, dist_m=None, dur_s=None, gm_link=None, extra_html="", route_id=None):
    """Create HTML popup content for Folium markers"""
    lines = [f"<b>{title}</b>", f"{point[0]:.6f}, {point[1]:.6f}"]
    if dist_m is not None:
        lines.append(f"Distance: {dist_m/1000.0:.2f} km")
    if dur_s is not None:
        lines.append(f"ETA: {int(dur_s/60)} min")
    if gm_link:
        lines.append(f"<a href='{gm_link}' target='_blank' rel='noopener noreferrer'>Open in Google Maps</a>")
    if extra_html:
        lines.append(extra_html)
    # Add route_id as data attribute for JavaScript
    route_attr = f' data-route-id="{route_id}"' if route_id else ''
    html = f'<div{route_attr}>' + "<br>".join(lines) + '</div>'
    return IFrame(html, width=340, height=160)

def build_map_html(origin, stores_flat, gov_items, assignments):
    """
    Build Folium map with all markers and routes.
    Routes are hidden initially and shown when marker is clicked.
    Returns the HTML string representation of the map.
    """
    m = folium.Map(location=origin, zoom_start=13, tiles=TILE_URL, attr=ATTR)

    # origin marker
    folium.Marker(
        location=origin,
        icon=folium.Icon(color="blue", icon="home"),
        popup=Popup(make_popup_html("Origin", origin, gm_link=google_maps_link(origin, origin)), max_width=300)
    ).add_to(m)

    # Store route data for JavaScript interaction
    store_routes_data = []
    route_id_counter = 0

    # red -> yellow -> green -> blue stacking
    for s in [s for s in stores_flat if s["color"] == "red"]:
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "Some Missing"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        
        # Get route
        coords, dist, dur = get_osrm_route(origin, coord)
        route_id = f"route_red_{route_id_counter}"
        route_id_counter += 1
        
        # Create marker with click handler
        marker = folium.Marker(
            location=coord,
            icon=folium.Icon(color="red", icon="info-sign"),
            popup=Popup(make_popup_html(title, coord, dist_m=dist, dur_s=dur, gm_link=gm, extra_html=extra, route_id=route_id), max_width=360)
        )
        marker.add_to(m)
        
        # Create route and show it (opacity 0.6 for red routes)
        if coords:
            polyline = folium.PolyLine(coords, color="red", weight=4, opacity=0.6, name=route_id).add_to(m)
        else:
            polyline = folium.PolyLine([origin, coord], color="red", weight=3, opacity=0.4, dash_array="5,5", name=route_id).add_to(m)
        
        store_routes_data.append({
            "route_id": route_id,
            "marker_id": f"marker_{route_id_counter}",
            "coords": coords if coords else [origin, coord],
            "color": "red",
            "distance": dist,
            "duration": dur
        })

    yellow_shades = YELLOW_SHADES
    yellow_list = [s for s in stores_flat if s["color"] == "yellow"]
    for idx, s in enumerate(yellow_list):
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "Has Alternatives"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        
        # Get route
        coords, dist, dur = get_osrm_route(origin, coord)
        route_id = f"route_yellow_{route_id_counter}"
        route_id_counter += 1
        color = yellow_shades[min(idx, len(yellow_shades) - 1)]
        
        # Create marker with orange color for alternatives (yellow not supported by Folium)
        marker = folium.Marker(
            location=coord,
            icon=folium.Icon(color="orange", icon="info-sign"),
            popup=Popup(make_popup_html(title, coord, dist_m=dist, dur_s=dur, gm_link=gm, extra_html=extra, route_id=route_id), max_width=360)
        )
        marker.add_to(m)
        
        # Create route and show it (use orange color for route to match marker)
        route_color = "orange"
        if coords:
            polyline = folium.PolyLine(coords, color=route_color, weight=4, opacity=0.6, name=route_id).add_to(m)
        else:
            polyline = folium.PolyLine([origin, coord], color=route_color, weight=3, opacity=0.4, dash_array="5,5", name=route_id).add_to(m)
        
        store_routes_data.append({
            "route_id": route_id,
            "marker_id": f"marker_{route_id_counter}",
            "coords": coords if coords else [origin, coord],
            "color": route_color,
            "distance": dist,
            "duration": dur
        })

    for s in [s for s in stores_flat if s["color"] == "green"]:
        coord = s["coord"]
        gm = google_maps_link(origin, coord)
        shop_name = s.get("meta", {}).get("shop_name")
        title = shop_name if shop_name else "All Available"
        extra = f"<small>{shop_name}</small>" if shop_name else ""
        
        # Get route
        coords, dist, dur = get_osrm_route(origin, coord)
        route_id = f"route_green_{route_id_counter}"
        route_id_counter += 1
        
        # Create marker
        marker = folium.Marker(
            location=coord,
            icon=folium.Icon(color="green", icon="info-sign"),
            popup=Popup(make_popup_html(title, coord, dist_m=dist, dur_s=dur, gm_link=gm, extra_html=extra, route_id=route_id), max_width=360)
        )
        marker.add_to(m)
        
        # Create route and show it (green routes for all available)
        if coords:
            polyline = folium.PolyLine(coords, color="green", weight=5, opacity=0.7, name=route_id).add_to(m)
        else:
            polyline = folium.PolyLine([origin, coord], color="green", weight=4, opacity=0.45, dash_array="5,5", name=route_id).add_to(m)
        
        store_routes_data.append({
            "route_id": route_id,
            "marker_id": f"marker_{route_id_counter}",
            "coords": coords if coords else [origin, coord],
            "color": "green",
            "distance": dist,
            "duration": dur
        })

    # blue gov markers
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

    # draw assignments (visible purple) - matching working app.py implementation
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

    # Inject JavaScript to handle marker clicks and show/hide routes
    store_routes_json = json.dumps(store_routes_data)
    gov_routes_json = json.dumps(gov_routes_data)
    
    js_template = """
    <script>
    (function(){
        try {
            const storeRoutes = STORE_ROUTES_JSON;
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
            
            // Store route polylines - routes are already created by Python, we just track them
            let activeRouteId = null;
            
            // Handle marker clicks to highlight routes (all routes are already visible)
            if (Lmap) {
                // Find all existing polylines on the map
                const allPolylines = [];
                Lmap.eachLayer(function(layer) {
                    if (layer instanceof L.Polyline && layer.options && layer.options.name) {
                        allPolylines.push(layer);
                    }
                });
                
                Lmap.on('popupopen', function(e) {
                    // Get route_id from popup content
                    const popup = e.popup;
                    if (!popup || !popup._content) return;
                    
                    let routeId = null;
                    try {
                        // Try to get route_id from iframe content
                        const iframe = popup._content.querySelector ? popup._content.querySelector('iframe') : null;
                        if (iframe && iframe.contentDocument) {
                            const div = iframe.contentDocument.querySelector('[data-route-id]');
                            if (div) {
                                routeId = div.getAttribute('data-route-id');
                            }
                        }
                        // Fallback: try to find in popup container
                        if (!routeId) {
                            const container = popup._container;
                            if (container) {
                                const div = container.querySelector('[data-route-id]');
                                if (div) {
                                    routeId = div.getAttribute('data-route-id');
                                }
                            }
                        }
                    } catch(err) {
                        console.warn('Error reading route_id from popup:', err);
                    }
                    
                    // If we have a route_id, highlight the route
                    if (routeId) {
                        // Reset all routes to normal opacity
                        allPolylines.forEach(function(pl) {
                            if (pl.options && pl.options.name) {
                                const originalColor = pl.options.color || 'gray';
                                const originalWeight = pl.options.weight || 4;
                                if (pl.options.name === routeId) {
                                    // Highlight selected route
                                    pl.setStyle({opacity: 0.9, weight: originalWeight + 1});
                                    pl.bringToFront();
                                } else {
                                    // Dim other routes slightly
                                    pl.setStyle({opacity: 0.3, weight: originalWeight});
                                }
                            }
                        });
                        activeRouteId = routeId;
                    } else {
                        // Fallback: match by coordinates
                        const marker = e.popup._source;
                        if (marker) {
                            const markerLat = marker._latlng.lat;
                            const markerLng = marker._latlng.lng;
                            
                            for (let i = 0; i < storeRoutes.length; i++) {
                                const sr = storeRoutes[i];
                                if (sr.coords && sr.coords.length > 0) {
                                    const lastCoord = sr.coords[sr.coords.length - 1];
                                    const latDiff = Math.abs(lastCoord[0] - markerLat);
                                    const lngDiff = Math.abs(lastCoord[1] - markerLng);
                                    if (latDiff < 0.0001 && lngDiff < 0.0001) {
                                        routeId = sr.route_id;
                                        // Highlight this route
                                        allPolylines.forEach(function(pl) {
                                            if (pl.options && pl.options.name === routeId) {
                                                pl.setStyle({opacity: 0.9, weight: (pl.options.weight || 4) + 1});
                                                pl.bringToFront();
                                            } else if (pl.options && pl.options.name) {
                                                pl.setStyle({opacity: 0.3, weight: pl.options.weight || 4});
                                            }
                                        });
                                        activeRouteId = routeId;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                });
                
                Lmap.on('popupclose', function(e) {
                    // Reset all routes to normal visibility when popup closes
                    allPolylines.forEach(function(pl) {
                        if (pl.options && pl.options.name) {
                            const originalWeight = pl.options.weight || 4;
                            const originalOpacity = pl.options.color === 'green' ? 0.7 : 
                                                   (pl.options.color === 'orange' ? 0.6 : 0.6);
                            pl.setStyle({opacity: originalOpacity, weight: originalWeight});
                        }
                    });
                    activeRouteId = null;
                });
            }
            
            // Gov routes handling (existing code)
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
        } catch(err) { console.error('route-js', err); }
    })();
    </script>
    """
    js_filled = js_template.replace("STORE_ROUTES_JSON", store_routes_json).replace("GOV_ROUTES_JSON", gov_routes_json)
    safe_script = "{% raw %}\n" + js_filled + "\n{% endraw %}"
    m.get_root().html.add_child(Element(safe_script))

    # bounds - include agent coordinates from assignments (matching working app.py)
    all_points = [origin] + [s["coord"] for s in stores_flat] + [g["latlon"] for g in gov_items]
    # Add agent coordinates from assignments
    for a in assignments:
        if a.get("agent_coord"):
            all_points.append(a["agent_coord"])
    # Also include all hidden agents for bounds (as in working code)
    all_points.extend(HIDDEN_AGENTS_COORDS)
    try:
        lats = [p[0] for p in all_points if p]
        lons = [p[1] for p in all_points if p]
        if lats and lons:
            m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20,20))
    except Exception:
        pass

    return m._repr_html_()

def create_assignment(store_coord, store_color, origin, shop_name=None, agent_idx=None):
    """
    Create an assignment for a store to an agent.
    Returns assignment dictionary with route info and billing.
    
    Parameters:
    -----------
    store_coord : tuple
        (lat, lon) coordinates of the store
    store_color : str
        Color category of the store (green/yellow/red/blue)
    origin : tuple
        (lat, lon) coordinates of the origin point
    shop_name : str, optional
        Name of the shop if matched
    agent_idx : int, optional
        Index of agent to assign. If None, randomly selects one.
    
    Returns:
    --------
    dict: Assignment dictionary with route info and billing
    """
    if agent_idx is None:
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
    return assignment

def generate_delivery_map(
    origin,
    green_stores=None,
    yellow_stores=None,
    red_stores=None,
    assignments=None,
    gov_initiatives=None
):
    """
    Main function to generate delivery map.
    
    Parameters:
    -----------
    origin : tuple
        (lat, lon) coordinates of origin point
    green_stores : list of tuples, optional
        List of (lat, lon) coordinates for green stores
    yellow_stores : list of tuples, optional
        List of (lat, lon) coordinates for yellow stores
    red_stores : list of tuples, optional
        List of (lat, lon) coordinates for red stores
    assignments : list of dicts, optional
        List of assignment dictionaries (from create_assignment)
    gov_initiatives : list of dicts, optional
        List of government initiatives. If None, uses default GOV_INITIATIVES
    
    Returns:
    --------
    dict with keys:
        - map_html: HTML string of the generated map
        - stores_flat: List of store dictionaries with matched shop names
        - assignments: List of assignments (if provided or created)
    """
    if green_stores is None:
        green_stores = []
    if yellow_stores is None:
        yellow_stores = []
    if red_stores is None:
        red_stores = []
    if assignments is None:
        assignments = []
    if gov_initiatives is None:
        gov_initiatives = GOV_INITIATIVES

    # Build stores_flat including GOV as selectable "blue" stores
    stores_flat = []
    
    def add_store(coord, color):
        meta = {}
        shop = find_shop_name(coord)
        if shop:
            meta["shop_name"] = shop["name"]
            meta["matched_shop_coord"] = shop["latlon"]
            meta["match_distance_m"] = shop["distance_m"]
        stores_flat.append({"color": color, "coord": coord, "label": color.capitalize(), "meta": meta})

    for c in green_stores:
        add_store(c, "green")
    for c in yellow_stores:
        add_store(c, "yellow")
    for c in red_stores:
        add_store(c, "red")
    
    # append govt initiatives as blue
    for g in gov_initiatives:
        stores_flat.append({"color": "blue", "coord": g["latlon"], "label": "Gov", "meta": {"name": g["name"], "address": g["address"]}})

    # Build map
    map_html = build_map_html(origin, stores_flat, gov_initiatives, assignments)

    return {
        "map_html": map_html,
        "stores_flat": stores_flat,
        "assignments": assignments
    }

# Example usage function
def example_usage():
    """Example of how to use the generate_delivery_map function"""
    origin = (12.9716, 77.5946)
    green_stores = [(12.9260174804538, 77.51873873639585), (12.916062252168635, 77.51315974188867)]
    yellow_stores = [(12.912046585611204, 77.52105616488345), (12.910958998147274, 77.51350306462756), (12.900447828509314, 77.5096368705969)]
    red_stores = [(12.907003244263793, 77.5049541035601), (12.909722477406175, 77.50923833723208)]
    
    result = generate_delivery_map(
        origin=origin,
        green_stores=green_stores,
        yellow_stores=yellow_stores,
        red_stores=red_stores
    )
    
    # Save map HTML to file
    with open("map_output.html", "w", encoding="utf-8") as f:
        f.write(result["map_html"])
    
    print("Map generated and saved to map_output.html")
    print(f"Found {len(result['stores_flat'])} stores")
    
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Accept JSON input from command line
        try:
            import json
            input_data = json.loads(sys.argv[1])
            origin = tuple(input_data.get("origin", [12.9716, 77.5946]))
            green_stores = [tuple(s) for s in input_data.get("green_stores", [])]
            yellow_stores = [tuple(s) for s in input_data.get("yellow_stores", [])]
            red_stores = [tuple(s) for s in input_data.get("red_stores", [])]
            
            assignments = []
            # If delivery is requested, create assignment for best store
            if input_data.get("create_delivery") and input_data.get("best_store"):
                best_store_coord = tuple(input_data.get("best_store"))
                # Find the store color (check if it's in green, yellow, or red)
                store_color = "green"  # Default to green for best store
                # Convert lists to tuples for comparison
                green_tuples = [tuple(s) for s in green_stores]
                yellow_tuples = [tuple(s) for s in yellow_stores]
                red_tuples = [tuple(s) for s in red_stores]
                
                if best_store_coord in green_tuples:
                    store_color = "green"
                elif best_store_coord in yellow_tuples:
                    store_color = "yellow"
                elif best_store_coord in red_tuples:
                    store_color = "red"
                
                # Get agent index (if provided, use it; otherwise random)
                agent_idx = input_data.get("agent_idx")
                # Validate agent_idx is within range
                if agent_idx is not None:
                    if agent_idx < 0 or agent_idx >= len(HIDDEN_AGENTS_COORDS):
                        import sys
                        sys.stderr.write(f"Warning: Invalid agent_idx {agent_idx}, using random selection\n")
                        agent_idx = None
                else:
                    agent_idx = None  # Will be randomly selected in create_assignment
                
                # Create assignment with specified or closest agent
                try:
                    assignment = create_assignment(
                        store_coord=best_store_coord,
                        store_color=store_color,
                        origin=origin,
                        shop_name=None,
                        agent_idx=agent_idx
                    )
                    assignments = [assignment]
                    import sys
                    sys.stderr.write(f"Created assignment: agent_idx={assignment.get('agent_idx')}, agent={assignment.get('agent_profile', {}).get('name', 'Unknown')}\n")
                except Exception as e:
                    import sys
                    sys.stderr.write(f"Error creating assignment: {str(e)}\n")
                    assignments = []
            
            result = generate_delivery_map(
                origin=origin,
                green_stores=green_stores,
                yellow_stores=yellow_stores,
                red_stores=red_stores,
                assignments=assignments
            )
            
            # Output JSON with map HTML
            output = {
                "map_html": result["map_html"],
                "stores_count": len(result["stores_flat"]),
                "stores": result["stores_flat"],
                "assignments": result.get("assignments", [])
            }
            # Convert assignments to JSON-serializable format
            if output["assignments"]:
                serialized_assignments = []
                for a in output["assignments"]:
                    # Convert tuple coordinates to lists
                    agent_coord = a.get("agent_coord")
                    if isinstance(agent_coord, tuple):
                        agent_coord = list(agent_coord)
                    
                    store_coord = a.get("store_coord")
                    if isinstance(store_coord, tuple):
                        store_coord = list(store_coord)
                    
                    # Convert route coordinates (list of tuples) to list of lists
                    coords_agent_store = a.get("coords_agent_store")
                    if coords_agent_store:
                        if isinstance(coords_agent_store[0], tuple):
                            coords_agent_store = [list(c) for c in coords_agent_store]
                    
                    coords_store_origin = a.get("coords_store_origin")
                    if coords_store_origin:
                        if isinstance(coords_store_origin[0], tuple):
                            coords_store_origin = [list(c) for c in coords_store_origin]
                    
                    serialized_a = {
                        "agent_idx": a.get("agent_idx"),
                        "agent_coord": agent_coord,
                        "agent_profile": a.get("agent_profile", {}),
                        "store_coord": store_coord,
                        "store_color": a.get("store_color"),
                        "store_shop_name": a.get("store_shop_name"),
                        "coords_agent_store": coords_agent_store,
                        "dist1_m": a.get("dist1_m"),
                        "coords_store_origin": coords_store_origin,
                        "dist2_m": a.get("dist2_m"),
                        "total_m": a.get("total_m"),
                        "charge": a.get("charge")
                    }
                    serialized_assignments.append(serialized_a)
                output["assignments"] = serialized_assignments
            else:
                output["assignments"] = []
            print(json.dumps(output))
        except Exception as e:
            import sys
            sys.stderr.write(f"Error: {str(e)}\n")
            sys.exit(1)
    else:
        example_usage()



