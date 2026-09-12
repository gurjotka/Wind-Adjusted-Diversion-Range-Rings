# Wind-Adjusted Diversion Range Rings

**Live app:**[Open the deployed app]
https://wind-adjusted-diversion-range-rings-uecy2app6qdtgebnjgurdmq.streamlit.app/

## What's here

- `geo.py` — great-circle distance & destination-point math (no GIS library needed).
- `wind.py` — the two-step nearest-neighbor wind lookup (nearest snapshot in time, then nearest grid point in space).
- `rings.py` — Part A: builds the 72-point wind-adjusted "egg" ring for one airport at one wind snapshot.
- `coverage.py` — Part B: ray-casting point-in-polygon test + per-waypoint coverage check.
- `map_view.py` — builds the interactive Leaflet map (`output/coverage_map.html`).
- `main.py` — runs the whole pipeline end to end.
- `app.py` — a small Streamlit wrapper around the same pipeline, for the live/deployed version.

## Run it

```bash
python3 main.py
```

Produces, in `output/`:
- `rings.geojson` — all 25 ring polygons (5 airports × 5 wind snapshots), GeoJSON `[lon, lat]` order.
- `coverage_report.json` — per-waypoint coverage result + overall summary.
- `coverage_map.html` — standalone interactive map (open directly in a browser, no server needed).

Or run the interactive version:

```bash
pip install streamlit
streamlit run app.py
```

## Assumptions / judgment calls

- **Nearest-neighbor only, no interpolation** (spatial or temporal), as the spec explicitly allows.
  Ties in the nearest-snapshot lookup are broken by whichever timestamp appears first in the input
  list — doesn't come up in the sample data (05:00Z is nearer 06:00Z than 00:00Z either way), but
  it's a defined behavior rather than undefined.
- **The nearest wind grid point is looked up once per (airport, snapshot)**, not once per bearing.
  The spec's Step 1 nearest-neighbor search depends only on the airport's fixed lat/lon, not on the
  bearing being evaluated, so this is exact, not an approximation — it also avoids doing the same
  416-point nearest-neighbor search 72 times over.
- **Point-in-polygon uses (lon, lat) as a flat (x, y) plane** rather than a geodesic containment
  test. For ring sizes on the order of ~1,000 nm this is the standard simplification and is what
  the spec's own suggestion (shapely, or hand-rolled ray-casting) does too.
- **Map rendered as hand-written Leaflet HTML instead of folium.** Same idea (open one HTML file,
  see the map), just without adding the folium dependency. It still requires internet access when
  *opened*, to load the Leaflet library and map tiles from public CDNs — the computation itself is
  fully offline.
- **Only the wind snapshots the route actually uses are shown by default** on the map, per the
  spec's suggestion, to avoid clutter — with a time slider (bonus) to step through all 5 snapshots
  and watch the rings visibly grow/shift with the wind, including snapshots the route never touches.
- **Polygon closure**: each ring repeats its first point at the end (73 coordinates for 72 bearings),
  which is what GeoJSON's Polygon spec expects for a closed ring.
- Verified against `worked_example.pdf` before running the full loop: the nearest-snapshot pick,
  nearest-grid-point pick, all four cardinal-bearing distances, and the 5-snapshot time-drift check
  all match exactly. The zero-wind case also produces an exact 1290.0 nm circle at every bearing.
