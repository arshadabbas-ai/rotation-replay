# AI acknowledgement: this file was drafted with an AI assistant (Claude, Anthropic)
# and reviewed and edited by team Signal2Decision. See README "Use of AI".
"""Rotation Replay engine.

Replays a kharif + rabi crop rotation against every year of daily weather and
scores each season for heat, frost, water and harvest-rain stress.
All scores are transparent agronomic proxies, not yield predictions.
"""
import datetime as dt
import math
from itertools import product

import numpy as np
import pandas as pd

from crops import CROPS, KHARIF, RABI

STRESS_CUTOFF = 0.5        # a season with stress >= this counts as "stressed"
TURNAROUND_DAYS = 7        # minimum gap between harvest and next sowing
SOIL = {                   # (irrigation loss factor, rice percolation factor)
    "Sandy": (1.20, 1.5),
    "Loam": (1.00, 1.0),
    "Clay": (0.90, 0.6),
}
IRRIGATION_CAP = {"Full (canal + tubewell)": None, "Limited": 350.0, "Rainfed": 0.0}


class Weather:
    def __init__(self, df, lat):
        df = df.sort_index()
        full = pd.date_range(df.index[0], df.index[-1], freq="D")
        df = df.reindex(full).interpolate(limit=7).ffill().bfill()
        self.lat = lat
        self.start = full[0].date()
        self.n = len(full)
        self.tmax = df["tmax"].to_numpy(float)
        self.tmin = df["tmin"].to_numpy(float)
        self.prcp = df["prcp"].fillna(0).to_numpy(float)
        self.first_year = full[0].year
        self.last_year = full[-1].year
        self.et0 = self._hargreaves(full.dayofyear.to_numpy())

    def _hargreaves(self, doy):
        """Reference evapotranspiration (mm/day), Hargreaves-Samani (FAO-56)."""
        phi = math.radians(self.lat)
        dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
        dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
        ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
        ra = (24 * 60 / np.pi) * 0.0820 * dr * (
            ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
        tmean = (self.tmax + self.tmin) / 2
        spread = np.sqrt(np.clip(self.tmax - self.tmin, 0, None))
        return np.clip(0.0023 * (tmean + 17.8) * spread * 0.408 * ra, 0, None)

    def idx(self, date):
        return (date - self.start).days

    def date(self, i):
        return self.start + dt.timedelta(days=int(i))

    def gdd(self, tbase):
        tmean = np.clip((self.tmax + self.tmin) / 2, None, 35.0)
        return np.clip(tmean - tbase, 0, None)


def fail_days(crop):
    """Heat days at which the heat score reaches 1 (scaled to the window length)."""
    window = crop.heat_window[1] - crop.heat_window[0] + 1
    return max(crop.heat_fail_days, round(0.3 * window))


def local_heat_threshold(wx, crop, n_years=20, pct=90):
    """Heat-day threshold for this location.

    A day counts as a heat day only if it is hotter than BOTH the crop's
    physiological threshold AND what was normal for that crop stage here
    (90th percentile of daily Tmax in the sensitive window, baseline years).
    This keeps a hot district from being flagged every single year for
    conditions its farmers and varieties are already adapted to.
    """
    vals = []
    for y in range(wx.first_year, wx.first_year + n_years):
        f = wx.idx(dt.date(y, crop.sow_month, crop.sow_day)) + crop.days_flower
        a, b = f + crop.heat_window[0], f + crop.heat_window[1]
        if a >= 0 and b < wx.n:
            vals.append(wx.tmax[a:b + 1])
    if not vals:
        return crop.heat_thr
    return max(crop.heat_thr, float(np.percentile(np.concatenate(vals), pct)))


def calibrate(wx, crop, n_years=20):
    """Thermal-time targets from the location's own baseline (first n_years)."""
    g = wx.gdd(crop.tbase)
    f, m = [], []
    for y in range(wx.first_year, wx.first_year + n_years):
        s = wx.idx(dt.date(y, crop.sow_month, crop.sow_day))
        if s < 0 or s + crop.days_maturity >= wx.n:
            continue
        f.append(g[s:s + crop.days_flower].sum())
        m.append(g[s:s + crop.days_maturity].sum())
    return float(np.mean(f)), float(np.mean(m))


def simulate(wx, crop, sow, gdd_f, gdd_m, soil, irrigation, heat_plus=0.0, heat_thr=None):
    """Replay one crop season starting at day index `sow`. Returns dict or None."""
    max_len = crop.days_maturity + 90
    avail = min(max_len, wx.n - sow - 11)      # keep 10 days for harvest rain
    if sow < 0 or avail < crop.days_flower:
        return None
    cg = np.cumsum(wx.gdd(crop.tbase)[sow:sow + avail])
    fi = int(np.searchsorted(cg, gdd_f))
    mi = int(np.searchsorted(cg, gdd_m))
    if mi >= avail and avail < max_len:
        return None                             # weather record ends mid-season
    immature = mi >= avail
    fi, mi = min(fi, avail - 1), min(mi, avail - 1)
    flower, mat = sow + fi, sow + mi

    w0 = max(sow, flower + crop.heat_window[0])
    w1 = min(mat, flower + crop.heat_window[1])
    thr = (crop.heat_thr if heat_thr is None else heat_thr) + heat_plus
    heat_days = int((wx.tmax[w0:w1 + 1] > thr).sum())
    frost_days = 0
    if crop.frost_thr is not None:
        frost_days = int((wx.tmin[max(sow, flower - 10):flower + 11] < crop.frost_thr).sum())

    frac = cg[:mi + 1] / max(gdd_m, 1.0)
    kc = np.interp(frac, [0, 0.15, 0.45, 0.80, 1.0],
                   [crop.kc[0], crop.kc[0], crop.kc[1], crop.kc[1], crop.kc[2]])
    etc = float((kc * wx.et0[sow:mat + 1]).sum())
    loss, perc = SOIL[soil]
    demand = etc * loss + crop.extra_water_mm * perc
    eff_rain = min(demand, 0.75 * float(wx.prcp[sow:mat + 1].sum()))
    need = max(0.0, demand - eff_rain)
    cap = IRRIGATION_CAP[irrigation]
    applied = need if cap is None else min(need, cap)
    unmet = need - applied

    heat = min(1.0, heat_days / fail_days(crop))
    frost = min(1.0, frost_days / 3)
    water = min(1.0, (unmet / max(demand, 1.0)) / 0.4)
    harvest_rain = float(wx.prcp[mat:mat + 10].sum())
    harv = 1.0 if harvest_rain > crop.harvest_rain_mm else 0.0
    stress = 1 - (1 - heat) * (1 - frost) * (1 - water) * (1 - 0.3 * harv)
    if immature:
        stress = 1.0
    drivers = {"heat": heat, "frost": frost, "water": water, "harvest rain": 0.3 * harv}
    return dict(sow=sow, flower=flower, maturity=mat, w0=w0, w1=w1, heat_thr=thr,
                heat_days=heat_days,
                frost_days=frost_days, irrigation_mm=applied, unmet_mm=unmet,
                harvest_rain_mm=harvest_rain, heat=heat, frost=frost, water=water,
                stress=float(stress), driver=max(drivers, key=drivers.get),
                immature=immature)


class Replayer:
    """Replays rotations for one location and one set of farm conditions."""

    def __init__(self, wx, soil="Loam", irrigation="Full (canal + tubewell)"):
        self.wx, self.soil, self.irrigation = wx, soil, irrigation
        self.targets = {k: calibrate(wx, c) for k, c in CROPS.items()}
        self.heat_thr = {k: local_heat_threshold(wx, c) for k, c in CROPS.items()}

    def _season(self, key, year, not_before, trait):
        crop = CROPS[key]
        t = trait or {}
        gf, gm = self.targets[key]
        scale = t.get("gdd_scale", 1.0)
        nominal = self.wx.idx(dt.date(year, crop.sow_month, crop.sow_day)) + t.get("sow_shift", 0)
        sow = max(nominal, not_before)
        r = simulate(self.wx, crop, sow, gf * scale, gm * scale, self.soil,
                     self.irrigation, t.get("heat_plus", 0.0), self.heat_thr[key])
        if r:
            r["delay"] = sow - nominal
        return r

    def replay(self, kharif, rabi, traits=None):
        """Year-by-year replay. Rabi is sown only after the kharif crop is off."""
        traits = traits or {}
        rows = []
        for y in range(self.wx.first_year, self.wx.last_year + 1):
            k = self._season(kharif, y, -10**9, traits.get(kharif))
            if k is None:
                continue
            r = self._season(rabi, y, k["maturity"] + TURNAROUND_DAYS, traits.get(rabi))
            if r is None:
                continue
            rows.append({
                "year": y, "label": f"{y}/{str(y + 1)[2:]}",
                "k_stress": k["stress"], "k_driver": k["driver"], "k_heat_days": k["heat_days"],
                "k_irrig": k["irrigation_mm"], "k_sow": self.wx.date(k["sow"]),
                "k_flower": self.wx.date(k["flower"]), "k_maturity": self.wx.date(k["maturity"]),
                "r_stress": r["stress"], "r_driver": r["driver"], "r_heat_days": r["heat_days"],
                "r_frost_days": r["frost_days"], "r_irrig": r["irrigation_mm"],
                "r_delay": r["delay"], "r_sow": self.wx.date(r["sow"]),
                "r_flower": self.wx.date(r["flower"]), "r_maturity": self.wx.date(r["maturity"]),
            })
        return pd.DataFrame(rows)

    def detail(self, kharif, rabi, year, which, traits=None):
        """Daily weather and key dates for one season (for the season explorer)."""
        traits = traits or {}
        k = self._season(kharif, year, -10**9, traits.get(kharif))
        res, key = k, kharif
        if which == "rabi":
            res, key = self._season(rabi, year, k["maturity"] + TURNAROUND_DAYS, traits.get(rabi)), rabi
        a, b = res["sow"], res["maturity"] + 10
        daily = pd.DataFrame({
            "Date": [str(self.wx.date(i)) for i in range(a, b + 1)],
            "Tmax": np.round(self.wx.tmax[a:b + 1], 1),
            "Tmin": np.round(self.wx.tmin[a:b + 1], 1),
            "Rain": np.round(self.wx.prcp[a:b + 1], 1),
        })
        info = dict(res)
        for f in ("sow", "flower", "maturity", "w0", "w1"):
            info[f + "_date"] = self.wx.date(res[f])
        info["rain_mm"] = float(self.wx.prcp[res["sow"]:res["maturity"] + 1].sum())
        info["crop"] = CROPS[key]
        return daily, info

    def summarise(self, kharif, rabi, df=None, traits=None):
        df = self.replay(kharif, rabi, traits) if df is None else df
        ks, rs = df["k_stress"] >= STRESS_CUTOFF, df["r_stress"] >= STRESS_CUTOFF
        recent = df["year"] >= df["year"].max() - 14
        n = len(df)
        kc, rc = CROPS[kharif], CROPS[rabi]
        soil, soil_notes = soil_health(kc, rc, df)
        return {
            "kharif": kharif, "rabi": rabi, "rotation": f"{kc.name} → {rc.name}",
            "years": n, "seasons": 2 * n,
            "stressed": int(ks.sum() + rs.sum()),
            "k_stressed": int(ks.sum()), "r_stressed": int(rs.sum()),
            "stressed_recent": int((ks & recent).sum() + (rs & recent).sum()),
            "recent_seasons": int(2 * recent.sum()),
            "resilience": float(1 - (df["k_stress"].mean() + df["r_stress"].mean()) / 2),
            "water_mm": float((df["k_irrig"] + df["r_irrig"]).mean()),
            "soil": soil, "soil_notes": soil_notes,
            "return": float((kc.return_index * (1 - df["k_stress"].mean())
                             + rc.return_index * (1 - df["r_stress"].mean())) / 2),
            "rabi_delay": float(df["r_delay"].median()),
        }

    def rank(self, weights):
        """Score all kharif x rabi rotations with the farmer's priority weights."""
        rows = [self.summarise(k, r) for k, r in product(KHARIF, RABI)]
        t = pd.DataFrame(rows)

        def norm(s, invert=False):
            span = s.max() - s.min()
            v = (s - s.min()) / span if span > 0 else s * 0 + 0.5
            return 1 - v if invert else v

        parts = {"risk": norm(t["resilience"]), "water": norm(t["water_mm"], True),
                 "soil": norm(t["soil"]), "profit": norm(t["return"])}
        total = sum(weights.values()) or 1.0
        t["score"] = sum(weights[k] * parts[k] for k in parts) / total
        return t.sort_values("score", ascending=False).reset_index(drop=True)


def soil_health(kc, rc, df):
    """Rule-based soil-health score (0-1) with the reasons behind it."""
    score, notes = 0.40, []
    if kc.legume or rc.legume:
        score += 0.35
        notes.append("includes a nitrogen-fixing legume")
    if kc.family != rc.family:
        score += 0.20
        notes.append("alternates crop families (breaks pest and disease cycles)")
    else:
        notes.append("same crop family in both seasons")
    if kc.deep_root or rc.deep_root:
        score += 0.05
        notes.append("includes a deep-rooted crop")
    if kc.key == "rice":
        score -= 0.15
        notes.append("puddled rice degrades soil structure")
    if df["r_delay"].median() > 0:
        score -= 0.10
        notes.append("tight turnaround delays winter sowing (residue-burning pressure)")
    return float(np.clip(score, 0, 1)), notes


TRAITS = {
    "10% earlier maturity": {"gdd_scale": 0.90},
    "+2 °C heat tolerance": {"heat_plus": 2.0},
    "Sow 10 days earlier": {"sow_shift": -10},
}


def trait_gap(rp, kharif, rabi):
    """How many stressed seasons would each variety trait / practice rescue?"""
    base = rp.replay(kharif, rabi)
    rows = []
    for key, col in ((kharif, "k_stress"), (rabi, "r_stress")):
        b = int((base[col] >= STRESS_CUTOFF).sum())
        for name, t in TRAITS.items():
            alt = rp.replay(kharif, rabi, {key: t})
            m = base[["year", col]].merge(alt[["year", col]], on="year", suffixes=("", "_alt"))
            was = m[col] >= STRESS_CUTOFF
            now = m[col + "_alt"] >= STRESS_CUTOFF
            rows.append({"Crop": CROPS[key].name, "Change": name,
                         "Stressed seasons before": b, "After": int(now.sum()),
                         "Rescued": int((was & ~now).sum()),
                         "Newly stressed": int((~was & now).sum())})
    return pd.DataFrame(rows)


def phenology_check(rp):
    """Median simulated flowering/maturity dates at nominal sowing, for sanity checks."""
    rows = []
    for key, crop in CROPS.items():
        gf, gm = rp.targets[key]
        fl, ma = [], []
        for y in range(rp.wx.first_year, rp.wx.last_year + 1):
            s = rp.wx.idx(dt.date(y, crop.sow_month, crop.sow_day))
            r = simulate(rp.wx, crop, s, gf, gm, rp.soil, rp.irrigation, 0.0, rp.heat_thr[key])
            if r:
                fl.append(r["flower"] - s)
                ma.append(r["maturity"] - s)
        sow = dt.date(2001, crop.sow_month, crop.sow_day)
        rows.append({"Crop": crop.name, "Sowing": sow.strftime("%d %b"),
                     "Median flowering": (sow + dt.timedelta(int(np.median(fl)))).strftime("%d %b"),
                     "Median maturity": (sow + dt.timedelta(int(np.median(ma)))).strftime("%d %b"),
                     "GDD to maturity": round(gm),
                     "Crop heat threshold (\u00b0C)": crop.heat_thr,
                     "Local heat threshold (\u00b0C)": round(rp.heat_thr[key], 1)})
    return pd.DataFrame(rows)
