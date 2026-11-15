"""Download and cache NASA POWER daily agroclimatology data (no API key needed).

Usage:
    python fetch_power.py                 # all demo districts -> data/*.csv
    python fetch_power.py 31.5 74.3 Lahore

Source: NASA POWER Project, https://power.larc.nasa.gov (community=AG)
Parameters: T2M_MAX, T2M_MIN (deg C), PRECTOTCORR (mm/day)
"""
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

from crops import DISTRICTS

URL = ("https://power.larc.nasa.gov/api/temporal/daily/point"
       "?parameters=T2M_MAX,T2M_MIN,PRECTOTCORR&community=AG"
       "&longitude={lon}&latitude={lat}&start={start}&end={end}&format=JSON")
DATA_DIR = Path(__file__).parent / "data"


def _get(lat, lon, start, end):
    url = URL.format(lat=lat, lon=lon, start=start, end=end)
    with urllib.request.urlopen(url, timeout=180) as r:
        p = json.load(r)["properties"]["parameter"]
    df = pd.DataFrame({"tmax": p["T2M_MAX"], "tmin": p["T2M_MIN"],
                       "prcp": p["PRECTOTCORR"]})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    return df


def fetch(lat, lon, start="19810101", end="20260630"):
    """Return a daily DataFrame (tmax, tmin, prcp) indexed by date."""
    try:
        df = _get(lat, lon, start, end)
    except Exception:
        # fall back to 10-year chunks if one long request is refused
        parts, y0, y1 = [], int(start[:4]), int(end[:4])
        for y in range(y0, y1 + 1, 10):
            s = start if y == y0 else f"{y}0101"
            e = end if y + 9 >= y1 else f"{y + 9}1231"
            parts.append(_get(lat, lon, s, e))
        df = pd.concat(parts)
    df = df.where(df > -900)          # POWER fill value is -999
    df.index.name = "date"
    return df.dropna(how="all")


def slug(name):
    return name.lower().replace(" ", "_")


if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    if len(sys.argv) == 4:
        jobs = {sys.argv[3]: (float(sys.argv[1]), float(sys.argv[2]))}
    else:
        jobs = DISTRICTS
    for name, (lat, lon) in jobs.items():
        print(f"Fetching {name} ({lat}, {lon}) ...", flush=True)
        df = fetch(lat, lon)
        out = DATA_DIR / f"{slug(name)}.csv"
        df.round(2).to_csv(out)
        print(f"  saved {len(df)} days -> {out}")
