"""
Geometry helpers.

Two functions, both using the standard spherical-Earth model:

1. haversine_nm(lat1, lon1, lat2, lon2)
   -> great-circle distance between two points, in nautical miles.
   Used only for "which wind grid point is closest to this airport?" —
   a nearest-neighbor search, so it doesn't need to be perfectly precise.

2. destination_point(lat, lon, bearing_deg, distance_nm)
   -> the lat/lon you end up at if you start at (lat, lon) and travel
   `distance_nm` nautical miles along `bearing_deg` (0=N, 90=E, clockwise).
   This is the one that turns each (bearing, distance) pair from the
   ring calculation into an actual point we can plot.

Both use the standard spherical destination-point / haversine formulas.
No third-party geo library is required.
"""

import math

# Mean Earth radius in nautical miles (1 nm was originally defined as
# 1 arc-minute of latitude, so this constant is the same one that
# makes "60 nm per degree" work out).
EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_NM * c


def destination_point(lat, lon, bearing_deg, distance_nm):
    """
    Given a start point, a bearing (degrees, clockwise from true north),
    and a distance (nautical miles), return the (lat, lon) you arrive at,
    following a great-circle path.
    """
    delta = distance_nm / EARTH_RADIUS_NM  # angular distance, radians
    theta = math.radians(bearing_deg)

    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )

    # normalize longitude back into [-180, 180]
    lon2 = (math.degrees(lambda2) + 540) % 360 - 180
    lat2 = math.degrees(phi2)
    return lat2, lon2
