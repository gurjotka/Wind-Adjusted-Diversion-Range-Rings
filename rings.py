"""
Part A — the wind-adjusted "egg" ring for one airport, at one wind snapshot.

The idea: instead of "how far can the plane get in 180 minutes" being a
single number (which would draw a circle), we compute that answer
separately for 72 different compass directions (every 5 degrees), because
wind helps in some directions and hurts in others. Connecting those 72
points gives an egg-shaped polygon instead of a circle.
"""

import math
from geo import destination_point
from wind import nearest_grid_point

BEARINGS_DEG = list(range(0, 360, 5))  # 0, 5, 10, ..., 355  -> 72 directions


def wind_component_kt(u, v, bearing_deg):
    """
    Projects the wind vector (u=eastward, v=northward) onto a travel
    bearing. Positive result = tailwind (helping), negative = headwind.
    """
    bearing_rad = math.radians(bearing_deg)
    return u * math.sin(bearing_rad) + v * math.cos(bearing_rad)


def build_ring(airport, snapshot, aircraft):
    """
    airport: {"icao", "name", "lat", "lon"}
    snapshot: one wind snapshot dict {"timestamp", "grid": [...]}
    aircraft: {"diversion_speed_kt", "rating_minutes", ...}

    Returns a dict: {
        "icao": ..., "timestamp": ..., "points_latlon": [(lat, lon), ...]
    }
    points_latlon is the closed 72-point polygon ring (first point
    repeated at the end to close it).
    """
    lat, lon = airport["lat"], airport["lon"]

    # The nearest wind grid point doesn't depend on bearing — it only
    # depends on where the airport is and which snapshot we're in — so
    # we look it up once and reuse it for all 72 bearings.
    grid_point = nearest_grid_point(snapshot["grid"], lat, lon)
    u, v = grid_point["u"], grid_point["v"]

    hours = aircraft["rating_minutes"] / 60.0
    points = []
    for bearing in BEARINGS_DEG:
        wc = wind_component_kt(u, v, bearing)
        groundspeed_kt = aircraft["diversion_speed_kt"] + wc
        distance_nm = groundspeed_kt * hours
        dest_lat, dest_lon = destination_point(lat, lon, bearing, distance_nm)
        points.append((dest_lat, dest_lon))

    points.append(points[0])  # close the polygon

    return {
        "icao": airport["icao"],
        "name": airport.get("name", airport["icao"]),
        "timestamp": snapshot["timestamp"],
        "points_latlon": points,
        "wind_used": {"lat": grid_point["lat"], "lon": grid_point["lon"], "u": u, "v": v},
    }


def ring_to_geojson_feature(ring, aircraft_name):
    """Convert one build_ring() result into a GeoJSON Polygon Feature (lon, lat order)."""
    coords = [[lon, lat] for (lat, lon) in ring["points_latlon"]]
    return {
        "type": "Feature",
        "properties": {
            "icao": ring["icao"],
            "name": ring["name"],
            "aircraft": aircraft_name,
            "timestamp": ring["timestamp"],
        },
        "geometry": {"type": "Polygon", "coordinates": [coords]},
    }
