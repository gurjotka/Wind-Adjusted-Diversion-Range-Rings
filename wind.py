"""
Wind lookup — the "two-step nearest-neighbor problem" from the spec.

Step 1: given a target time, pick whichever wind snapshot's timestamp
        is closest to it (there are 5 snapshots, 6 hours apart).
Step 2: within that one snapshot's grid, pick whichever grid point is
        closest (in distance) to the lat/lon we care about.

No interpolation, as the spec says that's fine.
"""

from datetime import datetime
from geo import haversine_nm


def parse_iso(ts):
    """Parse an ISO timestamp like '2026-07-25T06:00:00Z' into a datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def nearest_snapshot(wind_grid, target_time_iso):
    """
    wind_grid: the full list of {"timestamp": ..., "grid": [...]} snapshots.
    target_time_iso: an ISO timestamp string, e.g. a waypoint's eta.

    Returns the single snapshot dict whose timestamp is closest to the
    target time (ties broken by whichever comes first in the list).
    """
    target = parse_iso(target_time_iso)
    best_snapshot = None
    best_diff = None
    for snapshot in wind_grid:
        snap_time = parse_iso(snapshot["timestamp"])
        diff = abs((snap_time - target).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_snapshot = snapshot
    return best_snapshot


def nearest_grid_point(grid, lat, lon):
    """
    grid: a single snapshot's list of {"lat", "lon", "u", "v"} points.
    Returns the one physically closest to (lat, lon).
    """
    best_point = None
    best_dist = None
    for point in grid:
        dist = haversine_nm(lat, lon, point["lat"], point["lon"])
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_point = point
    return best_point
