"""
Streamlit front-end for the wind-adjusted diversion ring tool.

This is the same pipeline as main.py (geo.py / wind.py / rings.py /
coverage.py / map_view.py) — nothing about the underlying math changes.
This file just gives it a small web UI so it can be deployed as a live
app (e.g. on Streamlit Community Cloud) instead of only producing a
static HTML file.

Run locally with:
    pip install streamlit
    streamlit run app.py
"""

import json
import os

import streamlit as st
import streamlit.components.v1 as components

from rings import build_ring, ring_to_geojson_feature
from coverage import check_route_coverage
from map_view import render_map

st.set_page_config(page_title="Wind-Adjusted Diversion Rings", layout="wide")

DATA_DIR = "data"


def load_default(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


st.title("Wind-Adjusted Diversion Range Rings")
st.caption(
    "Computes 180-minute diversion range rings around candidate airports, "
    "adjusted for time-varying wind, and checks whether a flight route stays "
    "covered at every point along the way."
)

with st.sidebar:
    st.header("Inputs")
    st.write("Using the bundled sample data by default. You can swap in your own "
             "files below (same JSON shape as the sample files).")

    airports_file = st.file_uploader("Airports JSON", type="json")
    aircraft_file = st.file_uploader("Aircraft JSON", type="json")
    wind_file = st.file_uploader("Wind grid JSON", type="json")
    route_file = st.file_uploader("Route JSON", type="json")

    airports = json.load(airports_file) if airports_file else load_default("sample_airports.json")
    aircraft = json.load(aircraft_file) if aircraft_file else load_default("sample_aircraft.json")
    wind_grid = json.load(wind_file) if wind_file else load_default("sample_wind_grid.json")
    route = json.load(route_file) if route_file else load_default("sample_route.json")

    st.divider()
    st.write(f"**Aircraft:** {aircraft['aircraft']}")
    st.write(f"**Diversion speed:** {aircraft['diversion_speed_kt']} kt")
    st.write(f"**Rating:** {aircraft['rating_minutes']} min")
    st.write(f"**Airports:** {len(airports)}  |  **Wind snapshots:** {len(wind_grid)}")


@st.cache_data(show_spinner=False)
def compute(airports, aircraft, wind_grid, route):
    all_rings = []
    rings_by_snapshot = {}
    for airport in airports:
        for snapshot in wind_grid:
            ring = build_ring(airport, snapshot, aircraft)
            all_rings.append(ring)
            rings_by_snapshot.setdefault(snapshot["timestamp"], []).append(ring)

    features = [ring_to_geojson_feature(r, aircraft["aircraft"]) for r in all_rings]
    geojson = {"type": "FeatureCollection", "features": features}

    coverage = check_route_coverage(route, rings_by_snapshot)
    return rings_by_snapshot, geojson, coverage


with st.spinner("Computing rings and checking coverage..."):
    rings_by_snapshot, geojson, coverage = compute(airports, aircraft, wind_grid, route)

col1, col2, col3 = st.columns(3)
col1.metric("Route fully covered?", "Yes" if coverage["fully_covered"] else "No")
col2.metric("Coverage gaps", coverage["gap_count"])
col3.metric("Rings computed", len(geojson["features"]))

# Build the map to a temp file, then embed it
map_path = "/tmp/coverage_map.html"
render_map(airports, route, coverage, rings_by_snapshot, aircraft, map_path)
with open(map_path) as f:
    map_html = f.read()

components.html(map_html, height=650, scrolling=False)

st.subheader("Per-waypoint coverage")
st.dataframe(coverage["waypoints"], use_container_width=True)

dl1, dl2 = st.columns(2)
dl1.download_button(
    "Download rings.geojson",
    data=json.dumps(geojson, indent=2),
    file_name="rings.geojson",
    mime="application/geo+json",
)
dl2.download_button(
    "Download coverage_report.json",
    data=json.dumps(coverage, indent=2),
    file_name="coverage_report.json",
    mime="application/json",
)

st.caption(
    "No aviation background needed to read this: green waypoints are inside at least one "
    "airport's wind-adjusted diversion ring at their own arrival time; red waypoints aren't. "
    "Rings are recomputed live from whatever airports/aircraft/wind/route JSON is loaded."
)
