# AI acknowledgement: this file was drafted with an AI assistant (Claude, Anthropic)
# and reviewed and edited by team Signal2Decision. See README "Use of AI".
"""Print calibration diagnostics on the real NASA POWER data.

Usage:  python diagnose.py            (Khushab and Sargodha)
        python diagnose.py multan
Output is also saved to diagnose.txt
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from crops import CROPS, DISTRICTS
from engine import Replayer, Weather, fail_days, phenology_check, simulate

names = sys.argv[1:] or ["khushab", "sargodha"]
out = []
for n in names:
    df = pd.read_csv(Path(__file__).parent / "data" / f"{n.lower()}.csv", index_col="date", parse_dates=True)
    lat = {k.lower(): v for k, v in DISTRICTS.items()}[n.lower()][0]
    out.append(f"\n===== {n.upper()}  {df.index[0].date()} to {df.index[-1].date()}  rows={len(df)}  missing={int(df.isna().sum().sum())}")
    m = df.groupby(df.index.month).agg(tmax=("tmax", "mean"), tmin=("tmin", "mean"))
    m["rain_mm"] = df["prcp"].groupby([df.index.year, df.index.month]).sum().groupby(level=1).mean()
    out.append("Monthly climate (mean Tmax, Tmin, rain):\n" + m.round(1).T.to_string())
    rp = Replayer(Weather(df, lat))
    out.append("\nCrop calendar:\n" + phenology_check(rp).to_string(index=False))
    rows = []
    for key, c in CROPS.items():
        gf, gm = rp.targets[key]
        res = []
        for y in range(rp.wx.first_year, rp.wx.last_year + 1):
            r = simulate(rp.wx, c, rp.wx.idx(dt.date(y, c.sow_month, c.sow_day)), gf, gm, "Loam", "Full (canal + tubewell)", 0.0, rp.heat_thr[key])
            if r:
                res.append(r)
        h = np.array([r["heat_days"] for r in res])
        rows.append({"crop": key, "thr": c.heat_thr, "local_thr": round(rp.heat_thr[key], 1), "fail_days": fail_days(c), "n": len(res),
                     "heat_min": h.min(), "heat_med": np.median(h), "heat_p75": np.percentile(h, 75),
                     "heat_p90": np.percentile(h, 90), "heat_max": h.max(),
                     "frost_seasons": sum(r["frost_days"] > 0 for r in res),
                     "harvest_rain_seasons": sum(r["harvest_rain_mm"] > c.harvest_rain_mm for r in res),
                     "immature": sum(r["immature"] for r in res),
                     "stressed": sum(r["stress"] >= 0.5 for r in res),
                     "irrig_mm": round(np.mean([r["irrigation_mm"] for r in res]))})
    out.append("\nPer-crop stress at nominal sowing (full irrigation, loam):\n" + pd.DataFrame(rows).to_string(index=False))
    rw = rp.replay("rice", "wheat")
    out.append("\nRice -> wheat, wheat heat days by season:\n" + ", ".join(f"{r.label}:{r.r_heat_days}" for r in rw.itertuples()))
    out.append("Rice heat days by season:\n" + ", ".join(f"{r.year}:{r.k_heat_days}" for r in rw.itertuples()))
text = "\n".join(out)
print(text)
Path("diagnose.txt").write_text(text, encoding="utf-8")
