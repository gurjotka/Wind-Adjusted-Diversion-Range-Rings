"""
Part B — route coverage check.

For each route waypoint:
  1. Find the wind snapshot closest to that waypoint's eta (same
     nearest-snapshot logic as Part A, just driven by the waypoint's
     own time instead of the airport's).
  2. Check whether the waypoint sits inside at least one airport's ring
     *for that specific snapshot* (rings from other snapshots don't count).

Point-in-polygon is done with the classic ray-casting algorithm, so we
don't need any GIS library — it's ~15 lines and easy to reason about.
"""

from wind import nearest_snapshot


def point_in_polygon(lat, lon, points_latlon):
    """
    Ray-casting point-in-polygon test.
    points_latlon: closed polygon as a list of (lat, lon) tuples
    (first point repeated at the end — that's fine, doesn't affect the result).

    We treat (lon, lat) as plain (x, y) coordinates for this test. That's
    a standard simplification for ring sizes like these (hundreds of nm,
    not spanning the whole globe) and matches what the spec expects
    ("shapely is fine, or implement ray-casting yourself").
    """
    inside = False
    n = len(points_latlon)
    x, y = lon, lat
    for i in range(n - 1):
        y1, x1 = points_latlon[i]
        y2, x2 = points_latlon[i + 1]
        # does the edge (x1,y1)-(x2,y2) straddle the horizontal ray from (x,y)?
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1) + x1
        )
        if intersects:
            inside = not inside
    return inside


def check_route_coverage(route, rings_by_snapshot):
    """
    route: the parsed sample_route.json dict (has "waypoints", each with lat/lon/eta)
    rings_by_snapshot: dict {timestamp_str: [ring_dict, ring_dict, ...]}
                        i.e. all airport rings that belong to that snapshot

    Returns the Part B result dict: {"waypoints": [...], "fully_covered": bool, "gap_count": int}
    """
    snapshot_timestamps = list(rings_by_snapshot.keys())
    # We reuse nearest_snapshot() by faking a "wind_grid"-shaped list so the
    # same nearest-timestamp logic is used in both Part A and Part B.
    fake_snapshots = [{"timestamp": ts} for ts in snapshot_timestamps]

    results = []
    gap_count = 0
    for wp in route["waypoints"]:
        chosen = nearest_snapshot(fake_snapshots, wp["eta"])
        snapshot_ts = chosen["timestamp"]
        rings_here = rings_by_snapshot[snapshot_ts]

        covered = False
        covering_icao = None
        for ring in rings_here:
            if point_in_polygon(wp["lat"], wp["lon"], ring["points_latlon"]):
                covered = True
                covering_icao = ring["icao"]
                break

        if not covered:
            gap_count += 1

        results.append(
            {
                "lat": wp["lat"],
                "lon": wp["lon"],
                "eta": wp["eta"],
                "snapshot_used": snapshot_ts,
                "covered": covered,
                "covering_icao": covering_icao,
            }
        )

    return {
        "waypoints": results,
        "fully_covered": gap_count == 0,
        "gap_count": gap_count,
    }
