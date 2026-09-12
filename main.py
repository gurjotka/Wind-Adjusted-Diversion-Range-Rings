"""
Orchestrates the whole pipeline:
  1. Load airports, aircraft, wind grid, route.
  2. Part A: build a ring for every (airport, snapshot) pair.
  3. Write all rings out as one GeoJSON FeatureCollection.
  4. Part B: for each route waypoint, find its nearest snapshot and test
     containment against that snapshot's rings.
  5. Write the coverage report as JSON.
  6. Render everything onto an interactive map (see map_view.py).

Run with:  python3 main.py
"""

import json
import os

from rings import build_ring, ring_to_geojson_feature
from coverage import check_route_coverage
from map_view import render_map

DATA_DIR = "data"
OUT_DIR = "output"


def load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


def main():
    airports = load_json("sample_airports.json")
    aircraft = load_json("sample_aircraft.json")
    wind_grid = load_json("sample_wind_grid.json")
    route = load_json("sample_route.json")

    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- Part A: build every (airport, snapshot) ring ----
    all_rings = []  # flat list, for GeoJSON output
    rings_by_snapshot = {}  # {timestamp: [ring, ring, ...]}, for coverage lookups

    for airport in airports:
        for snapshot in wind_grid:
            ring = build_ring(airport, snapshot, aircraft)
            all_rings.append(ring)
            rings_by_snapshot.setdefault(snapshot["timestamp"], []).append(ring)

    print(f"Built {len(all_rings)} rings "
          f"({len(airports)} airports x {len(wind_grid)} snapshots)")

    # ---- Write GeoJSON of all rings ----
    features = [ring_to_geojson_feature(r, aircraft["aircraft"]) for r in all_rings]
    geojson = {"type": "FeatureCollection", "features": features}
    geojson_path = os.path.join(OUT_DIR, "rings.geojson")
    with open(geojson_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"Wrote {geojson_path}")

    # ---- Part B: coverage check ----
    coverage = check_route_coverage(route, rings_by_snapshot)
    coverage_path = os.path.join(OUT_DIR, "coverage_report.json")
    with open(coverage_path, "w") as f:
        json.dump(coverage, f, indent=2)
    print(f"Wrote {coverage_path}")
    print(f"Route fully covered: {coverage['fully_covered']}  "
          f"(gaps: {coverage['gap_count']})")
    for wp in coverage["waypoints"]:
        status = "COVERED" if wp["covered"] else "GAP"
        via = wp["covering_icao"] or "-"
        print(f"  lat={wp['lat']:>7} lon={wp['lon']:>8}  eta={wp['eta']}  "
              f"snapshot={wp['snapshot_used']}  [{status:7}] via={via}")

    # ---- Map ----
    map_path = os.path.join(OUT_DIR, "coverage_map.html")
    render_map(airports, route, coverage, rings_by_snapshot, aircraft, map_path)
    print(f"Wrote {map_path}")


if __name__ == "__main__":
    main()
