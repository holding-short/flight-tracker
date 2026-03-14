from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd
import pydeck as pdk
import streamlit as st

try:
    from FlightRadar24.api import FlightRadar24API
except Exception:  # keep app usable for demo mode even if dependency is missing at runtime
    FlightRadar24API = None  # type: ignore[assignment]


DEFAULT_BOUNDS = {
    "north": 42.75,
    "south": 41.80,
    "west": -71.55,
    "east": -70.50,
}


@dataclass
class FlightPoint:
    callsign: str
    latitude: float
    longitude: float
    altitude_ft: float
    speed_kts: float
    heading: float


@st.cache_data(ttl=15, show_spinner=False)
def fetch_flights(bounds: dict[str, float]) -> list[FlightPoint]:
    if FlightRadar24API is None:
        raise RuntimeError("fr24sdk is not available in this environment")

    api = FlightRadar24API()
    flights: Iterable[Any] = api.get_flights(bounds=bounds)

    points: list[FlightPoint] = []
    for flight in flights:
        points.append(
            FlightPoint(
                callsign=(getattr(flight, "callsign", "") or getattr(flight, "id", "UNKNOWN")).strip() or "UNKNOWN",
                latitude=float(getattr(flight, "latitude", 0.0)),
                longitude=float(getattr(flight, "longitude", 0.0)),
                altitude_ft=float(getattr(flight, "altitude", 0.0) or 0.0),
                speed_kts=float(getattr(flight, "ground_speed", 0.0) or 0.0),
                heading=float(getattr(flight, "heading", 0.0) or 0.0),
            )
        )
    return points


def demo_flights(bounds: dict[str, float], n: int = 35) -> list[FlightPoint]:
    random.seed(7)
    points: list[FlightPoint] = []
    for i in range(n):
        latitude = random.uniform(bounds["south"], bounds["north"])
        longitude = random.uniform(bounds["west"], bounds["east"])
        altitude_ft = random.uniform(2000, 39000)
        speed_kts = random.uniform(130, 520)
        heading = random.uniform(0, 359)
        points.append(
            FlightPoint(
                callsign=f"DEMO{i:03d}",
                latitude=latitude,
                longitude=longitude,
                altitude_ft=altitude_ft,
                speed_kts=speed_kts,
                heading=heading,
            )
        )
    return points


def to_dataframe(points: list[FlightPoint]) -> pd.DataFrame:
    rows = []
    for p in points:
        altitude_m = p.altitude_ft * 0.3048
        # blue -> red by speed
        speed_norm = min(max((p.speed_kts - 100) / 450, 0), 1)
        color = [int(40 + 215 * speed_norm), 80, int(255 - 180 * speed_norm), 200]
        radius = 120 + int(math.sqrt(max(altitude_m, 0)) * 2)
        rows.append(
            {
                "callsign": p.callsign,
                "lat": p.latitude,
                "lon": p.longitude,
                "alt_m": altitude_m,
                "speed_kts": p.speed_kts,
                "heading": p.heading,
                "color": color,
                "radius": radius,
            }
        )
    return pd.DataFrame(rows)


def build_map(df: pd.DataFrame, center_lat: float, center_lon: float) -> pdk.Deck:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat, alt_m]",
        get_fill_color="color",
        get_radius="radius",
        radius_units="meters",
        pickable=True,
        extruded=False,
    )

    return pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v11",
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=7,
            pitch=55,
            bearing=0,
        ),
        tooltip={
            "html": "<b>{callsign}</b><br/>Alt: {alt_m} m<br/>Speed: {speed_kts} kts<br/>Heading: {heading}°",
            "style": {"backgroundColor": "#1b1f2a", "color": "white"},
        },
        layers=[layer],
    )


def app() -> None:
    st.set_page_config(page_title="Boston 3D Flight Tracker", layout="wide")
    st.title("✈️ Boston 3D Flight Tracker")
    st.caption("Live regional flight activity rendered in 3D.")

    with st.sidebar:
        st.header("Settings")
        north = st.number_input("North", value=DEFAULT_BOUNDS["north"], format="%.4f")
        south = st.number_input("South", value=DEFAULT_BOUNDS["south"], format="%.4f")
        west = st.number_input("West", value=DEFAULT_BOUNDS["west"], format="%.4f")
        east = st.number_input("East", value=DEFAULT_BOUNDS["east"], format="%.4f")
        demo_mode = st.toggle("Demo mode", value=False)
        refresh_now = st.button("Refresh now")

    bounds = {"north": north, "south": south, "west": west, "east": east}

    try:
        points = demo_flights(bounds) if demo_mode else fetch_flights(bounds)
        error_message = None
    except Exception as exc:
        points = demo_flights(bounds)
        error_message = str(exc)

    if error_message:
        st.warning(f"Live fetch failed ({error_message}). Showing demo data.")

    df = to_dataframe(points)

    if df.empty:
        st.info("No flights in this region right now.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Flights", len(df))
    c2.metric("Avg Altitude (m)", f"{df['alt_m'].mean():,.0f}")
    c3.metric("Avg Speed (kts)", f"{df['speed_kts'].mean():,.0f}")

    st.pydeck_chart(build_map(df, center_lat=(north + south) / 2, center_lon=(west + east) / 2), use_container_width=True)

    st.subheader("Flight Table")
    st.dataframe(
        df[["callsign", "lat", "lon", "alt_m", "speed_kts", "heading"]]
        .sort_values("alt_m", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
    )

    st.caption(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} (UTC)")

    if refresh_now:
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    app()
