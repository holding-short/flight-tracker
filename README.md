# Boston 3D Flight Tracker

A simple Streamlit app that uses `fr24sdk` to fetch live flights around Boston and display them on a 3D map.

## Features

- Pulls current flights inside a configurable Boston-area bounding box
- Renders aircraft in 3D (longitude, latitude, altitude)
- Color-codes points by speed and scales by altitude
- Manual refresh button for quick updates
- Demo mode with synthetic flights if live data is unavailable

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown by Streamlit (usually `http://localhost:8501`).

## Notes

- Live data depends on network availability and API behavior.
- If live fetch fails, enable **Demo mode** in the sidebar to visualize the experience.
