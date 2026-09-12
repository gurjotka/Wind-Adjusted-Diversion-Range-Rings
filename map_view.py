"""
Builds the required map deliverable.

We hand-roll a small Leaflet.js page instead of using folium, because
folium isn't available in this environment — but the output is the same
kind of thing: a single standalone HTML file, using Leaflet from a CDN,
that opens directly in a browser. No server needed.

What it shows, ON LOAD, with no interaction required:
  - All candidate diversion airports (markers).
  - Every ring that was actually used by the coverage check — i.e. every
    airport's ring, for every wind snapshot that at least one waypoint's
    eta resolved to. (If the route only ever resolves to one snapshot,
    that's just that snapshot's 5 rings; here it's two snapshots, so
    it's the union of both.) Rings from different snapshots are drawn
    with different line styles (solid / dashed / dotted) so overlapping
    ones stay distinguishable.
  - The route as a line, with each waypoint colored green (covered) or
    red (gap).
  - BONUS: a dropdown to instead isolate any single one of the 5 wind
    snapshots (including ones the route never used), so you can watch
    the rings shift/grow with the wind and confirm it's genuinely
    time-varying, not just re-showing the same grid.
"""

import json


def render_map(airports, route, coverage, rings_by_snapshot, aircraft, out_path):
    snapshot_timestamps = sorted(rings_by_snapshot.keys())

    # Which snapshots did the route actually use? (for the default view / labeling)
    used_snapshots = sorted({wp["snapshot_used"] for wp in coverage["waypoints"]})

    # Airports, for the always-visible marker layer
    airport_data = [
        {"icao": a["icao"], "name": a.get("name", a["icao"]), "lat": a["lat"], "lon": a["lon"]}
        for a in airports
    ]

    # Rings, grouped by snapshot -> list of {icao, name, points: [[lat,lon],...]}
    rings_data = {}
    for ts in snapshot_timestamps:
        rings_data[ts] = [
            {
                "icao": r["icao"],
                "name": r["name"],
                "points": [[lat, lon] for lat, lon in r["points_latlon"]],
            }
            for r in rings_by_snapshot[ts]
        ]

    # Route waypoints with coverage status
    waypoints_data = coverage["waypoints"]

    route_line = [[wp["lat"], wp["lon"]] for wp in waypoints_data]

    # Center map roughly on the route
    center_lat = sum(wp["lat"] for wp in waypoints_data) / len(waypoints_data)
    center_lon = sum(wp["lon"] for wp in waypoints_data) / len(waypoints_data)

    data_blob = {
        "airports": airport_data,
        "rings_by_snapshot": rings_data,
        "snapshot_timestamps": snapshot_timestamps,
        "used_snapshots": used_snapshots,
        "route_line": route_line,
        "waypoints": waypoints_data,
        "aircraft": aircraft.get("aircraft", ""),
        "rating_minutes": aircraft.get("rating_minutes"),
        "center": [center_lat, center_lon],
        "fully_covered": coverage["fully_covered"],
        "gap_count": coverage["gap_count"],
    }

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data_blob))
    with open(out_path, "w") as f:
        f.write(html)


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Wind-Adjusted Diversion Coverage</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body { margin: 0; font-family: -apple-system, Segoe UI, Roboto, sans-serif; }
  #header { background: #0b1f3a; color: white; padding: 14px 20px; }
  #header h1 { margin: 0; font-size: 18px; }
  #header p { margin: 4px 0 0; font-size: 13px; color: #b9c6db; }
  #map { height: calc(100vh - 150px); width: 100%; }
  #controls { padding: 10px 20px; background: #f4f6fa; border-bottom: 1px solid #dde3ee; font-size: 13px; }
  #controls label { font-weight: 600; margin-right: 8px; }
  #snapshotLabel { font-weight: 600; color: #0b1f3a; }
  .legend { background: white; padding: 10px 12px; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-size: 12px; line-height: 1.7; }
  .legend div { display: flex; align-items: center; gap: 6px; }
  .swatch { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
  .badge.ok { background: #dcf5df; color: #1e7d34; }
  .badge.gap { background: #fde2e2; color: #b3261e; }
  select { font-size: 13px; padding: 3px 6px; }
</style>
</head>
<body>
<div id="header">
  <h1>Wind-Adjusted Diversion Coverage</h1>
  <p id="subtitle"></p>
</div>
<div id="controls">
  <label for="viewSelect">View:</label>
  <select id="viewSelect"></select>
  <span id="snapshotLabel" style="margin-left:10px; color:#555;"></span>
</div>
<div id="map"></div>
<script>
const DATA = __DATA__;

const map = L.map('map').setView(DATA.center, 4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

document.getElementById('subtitle').textContent =
  `Aircraft ${DATA.aircraft} | ${DATA.rating_minutes}-min diversion rings | ` +
  (DATA.fully_covered ? 'Route fully covered' : `${DATA.gap_count} coverage gap(s) found`);

// --- airports (always visible) ---
DATA.airports.forEach(a => {
  L.circleMarker([a.lat, a.lon], {
    radius: 5, color: '#0b1f3a', fillColor: '#0b1f3a', fillOpacity: 1, weight: 1
  }).addTo(map).bindTooltip(`${a.icao} — ${a.name}`);
});

// --- route line ---
L.polyline(DATA.route_line, { color: '#555', weight: 2, dashArray: '6,6' }).addTo(map);

// --- waypoints, color-coded by coverage ---
DATA.waypoints.forEach(wp => {
  const color = wp.covered ? '#1e7d34' : '#b3261e';
  const via = wp.covering_icao ? `covered by ${wp.covering_icao}` : 'no ring covers this point';
  L.circleMarker([wp.lat, wp.lon], {
    radius: 6, color: color, fillColor: color, fillOpacity: 0.9, weight: 1
  }).addTo(map).bindTooltip(
    `eta ${wp.eta}<br>snapshot used: ${wp.snapshot_used}<br>${via}`,
    { sticky: true }
  );
});

// --- ring layer ---
// Color = which airport (fixed per airport, consistent across snapshots).
// Dash style = which snapshot (so overlapping rings from different
// snapshots for the same airport stay visually distinguishable).
let ringLayer = L.layerGroup().addTo(map);

const airportColors = {};
const palette = ['#3388ff', '#ff8833', '#33cc88', '#cc33ff', '#e6b800', '#00b3b3', '#e64d8a'];
DATA.airports.forEach((a, i) => { airportColors[a.icao] = palette[i % palette.length]; });

const dashPatterns = [null, '8,6', '2,6', '10,3,2,3', '1,4'];
const dashByTimestamp = {};
DATA.snapshot_timestamps.forEach((ts, i) => { dashByTimestamp[ts] = dashPatterns[i % dashPatterns.length]; });

function drawRingsForTimestamps(timestamps) {
  ringLayer.clearLayers();
  timestamps.forEach(ts => {
    const rings = DATA.rings_by_snapshot[ts] || [];
    rings.forEach(ring => {
      const opts = {
        color: airportColors[ring.icao], weight: 2, fill: true, fillOpacity: 0.10
      };
      if (dashByTimestamp[ts]) opts.dashArray = dashByTimestamp[ts];
      L.polygon(ring.points, opts).addTo(ringLayer)
        .bindTooltip(`${ring.icao} — ${ring.name}<br>snapshot: ${ts}`);
    });
  });
}

const viewSelect = document.getElementById('viewSelect');
const snapshotLabel = document.getElementById('snapshotLabel');

// Build dropdown options: default = union of every snapshot the route
// actually used (this is what's shown immediately, no click required),
// then one option per individual snapshot to explore any of the 5.
const usedOption = document.createElement('option');
usedOption.value = 'used';
usedOption.textContent = `Rings used by the route (${DATA.used_snapshots.length} snapshot(s)) — default`;
viewSelect.appendChild(usedOption);

DATA.snapshot_timestamps.forEach(ts => {
  const opt = document.createElement('option');
  opt.value = ts;
  const usedTag = DATA.used_snapshots.includes(ts) ? ' [used by route]' : ' [not used by route]';
  opt.textContent = `Only: ${ts}${usedTag}`;
  viewSelect.appendChild(opt);
});

function applyView() {
  const val = viewSelect.value;
  if (val === 'used') {
    drawRingsForTimestamps(DATA.used_snapshots);
    snapshotLabel.textContent =
      `Showing every ring actually used to check this route's coverage ` +
      `(${DATA.used_snapshots.join(', ')})`;
  } else {
    drawRingsForTimestamps([val]);
    snapshotLabel.textContent = `Showing all airports' rings at ${val} only`;
  }
}

viewSelect.onchange = applyView;
applyView();

// --- legend ---
const legend = L.control({ position: 'bottomright' });
legend.onAdd = function () {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML =
    '<div><span class="swatch" style="background:#1e7d34"></span> Covered waypoint</div>' +
    '<div><span class="swatch" style="background:#b3261e"></span> Coverage gap</div>' +
    '<div><span class="swatch" style="background:#0b1f3a"></span> Diversion airport</div>' +
    '<div>Ring color = airport &nbsp;|&nbsp; line style = which wind snapshot</div>';
  return div;
};
legend.addTo(map);
</script>
</body>
</html>
"""
