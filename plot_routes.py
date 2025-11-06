# plot_routes.py
"""
Helper functions for routing & plotting
- get_osrm_route: get route geometry and summary from OSRM
- parse_coord: parse "lat, lon" single-line string
- google_maps_link: create maps direction URL
- compute_billing: billing slab
- draw_popup_iframe: safe html popup builder (IFrame)
"""

import requests, math
from urllib.parse import quote_plus
from folium import IFrame

OSRM_SERVER = "https://router.project-osrm.org"

def parse_coord(text: str):
    """Parse 'lat, lon' -> (lat, lon) or raise ValueError"""
    if not isinstance(text, str):
        raise ValueError("Coordinate text must be string 'lat, lon'")
    parts = text.split(",")
    if len(parts) < 2:
        raise ValueError("Coordinate must be in 'lat, lon' format")
    lat = float(parts[0].strip())
    lon = float(parts[1].strip())
    return (lat, lon)

def get_osrm_route(src: tuple, dst: tuple, profile: str = "driving"):
    """
    src/dst as (lat, lon)
    returns (coords_list[[lat,lon],...], distance_m, duration_s) or (None, None, None) on fail
    """
    coords = f"{src[1]},{src[0]};{dst[1]},{dst[0]}"
    url = f"{OSRM_SERVER}/route/v1/{profile}/{coords}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != "Ok" or not j.get("routes"):
            return None, None, None
        route = j["routes"][0]
        geom = route["geometry"]["coordinates"]  # [lon,lat] pairs
        coords_latlon = [[p[1], p[0]] for p in geom]
        return coords_latlon, route.get("distance"), route.get("duration")
    except Exception:
        return None, None, None

def google_maps_link(origin: tuple, dest: tuple, travelmode="driving"):
    """Build google maps directions link (origin/dest are (lat,lon))."""
    params = {
        "api": "1",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{dest[0]},{dest[1]}",
        "travelmode": travelmode
    }
    link = "https://www.google.com/maps/dir/?" + "&".join(f"{k}={quote_plus(str(v))}" for k,v in params.items())
    return link

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def compute_billing(distance_meters: float):
    """
    Billing slabs (cumulative interpretation):
      - <= 5 km: Rs. 20
      - >5 and <=10 km: Rs. 20 + 10 = Rs. 30
      - >10 km: Rs. 20 + 10 + 20 = Rs. 50
    Returns (total_distance_km, charge_rs)
    """
    if distance_meters is None:
        return None, None
    km = distance_meters / 1000.0
    charge = 0
    if km <= 5.0:
        charge = 20
    elif km <= 10.0:
        charge = 20 + 10
    else:
        charge = 20 + 10 + 20
    return round(km, 3), int(charge)

def make_popup_html(title: str, latlon: tuple, distance_m=None, duration_s=None, gm_link: str=None):
    """
    Returns an IFrame-wrapped HTML for Folium popup (so HTML renders and links work).
    """
    rows = []
    rows.append(f"<b>{title}</b>")
    rows.append(f"{latlon[0]:.6f}, {latlon[1]:.6f}")
    if distance_m:
        rows.append(f"Distance: {distance_m/1000.0:.2f} km")
    if duration_s:
        rows.append(f"ETA: {int(duration_s/60)} min")
    if gm_link:
        rows.append(f"<a href='{gm_link}' target='_blank'>Open in Google Maps</a>")
    html = "<br>".join(rows)
    # IFrame sized to roughly fit
    return IFrame(html, width=260, height=110)
