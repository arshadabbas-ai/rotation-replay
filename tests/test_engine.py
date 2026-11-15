"""Smoke test on SYNTHETIC weather (not NASA data). Run: python tests/test_engine.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Replayer, Weather, trait_gap, phenology_check  # noqa: E402


def synthetic(seed=0):
    rng = np.random.default_rng(seed)
    d = pd.date_range("1981-01-01", "2026-06-30")
    doy = d.dayofyear.to_numpy()
    yr = d.year.to_numpy()
    season = np.cos(2 * np.pi * (doy - 170) / 365)
    trend = 0.03 * (yr - 1981)
    tmax = 30 + 10.5 * season + trend + rng.normal(0, 2.2, len(d))
    tmin = 16.5 + 10.5 * season + trend + rng.normal(0, 1.8, len(d))
    monsoon = np.exp(-((doy - 215) / 30.0) ** 2)
    wet = rng.random(len(d)) < (0.04 + 0.35 * monsoon)
    prcp = np.where(wet, rng.gamma(0.8, 14, len(d)), 0.0)
    hot = (yr == 2022) & (d.month.isin([3, 4]))          # injected heatwave
    tmax = np.where(hot, tmax + 5, tmax)
    return pd.DataFrame({"tmax": tmax, "tmin": tmin, "prcp": prcp}, index=d)


if __name__ == "__main__":
    wx = Weather(synthetic(), 32.08)
    rp = Replayer(wx)
    print(phenology_check(rp).to_string(index=False), "\n")
    df = rp.replay("rice", "wheat")
    print(df[["label", "k_stress", "r_stress", "r_driver", "r_heat_days", "r_delay"]].tail(8).to_string(index=False))
    s = rp.summarise("rice", "wheat", df)
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items() if k != "soil_notes"})
    hw = df.loc[df.year == 2021, "r_stress"].iloc[0]
    assert hw >= 0.5, f"injected 2022 heatwave not flagged (stress={hw:.2f})"
    assert len(df) == 45, len(df)
    t = rp.rank({"risk": 3, "water": 3, "soil": 3, "profit": 3})
    assert len(t) == 20 and t["score"].between(0, 1).all()
    print(t[["rotation", "score", "stressed", "water_mm", "soil", "return"]].round(2).head(6).to_string(index=False))
    for irr in ("Limited", "Rainfed"):
        r2 = Replayer(wx, "Sandy", irr).summarise("rice", "wheat")
        print(irr, "stressed", r2["stressed"], "of", r2["seasons"])
    print(trait_gap(rp, "rice", "wheat").to_string(index=False))
    print("OK")
