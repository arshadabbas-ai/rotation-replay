# AI acknowledgement: this file was drafted with an AI assistant (Claude, Anthropic)
# and reviewed and edited by team Signal2Decision. See README "Use of AI".
"""Crop knowledge base for Rotation Replay.

Every number here is an editable agronomic assumption (typical Punjab, Pakistan
practice and commonly cited stress thresholds). They are screening proxies, not
calibrated yield-model parameters. Review them against local extension guides.

Phenology is given as typical calendar days (sowing -> flowering -> maturity).
The engine converts these to thermal time (growing degree days) using each
location's own 1981-2000 baseline, so hot years develop faster and cool years
slower.
"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Crop:
    key: str
    name: str
    season: str                 # "kharif" (summer) or "rabi" (winter)
    family: str
    legume: bool
    sow_month: int              # nominal sowing / transplanting date
    sow_day: int
    days_flower: int            # typical days sowing -> flowering
    days_maturity: int          # typical days sowing -> maturity
    tbase: float                # base temperature for thermal time (deg C)
    heat_thr: float             # daily Tmax above this in the window = heat day
    heat_window: Tuple[int, int]  # days relative to flowering (start, end)
    heat_fail_days: int         # heat days at which heat stress score reaches 1
    frost_thr: Optional[float]  # Tmin below this near flowering = frost day
    kc: Tuple[float, float, float]  # FAO-56 style Kc: initial, mid, end
    harvest_rain_mm: float      # rain in 10 days after maturity that hurts harvest
    extra_water_mm: float       # puddling / percolation water (rice)
    return_index: float         # relative gross return, 0-1 (placeholder, edit!)
    deep_root: bool = False


CROPS = {c.key: c for c in [
    # ---- Kharif (summer) ----
    Crop("rice", "Rice (basmati)", "kharif", "Poaceae", False, 7, 5, 85, 120,
         10.0, 37.0, (-5, 10), 6, None, (1.05, 1.20, 0.90), 40, 400, 0.80),
    Crop("cotton", "Cotton", "kharif", "Malvaceae", False, 5, 15, 65, 165,
         15.0, 40.0, (0, 40), 10, None, (0.35, 1.15, 0.60), 30, 0, 0.75, True),
    Crop("maize", "Maize (autumn)", "kharif", "Poaceae", False, 7, 25, 55, 100,
         10.0, 38.0, (-5, 10), 5, None, (0.30, 1.20, 0.50), 50, 0, 0.70),
    Crop("mung", "Mung bean", "kharif", "Fabaceae", True, 7, 5, 38, 72,
         10.0, 40.0, (0, 20), 6, None, (0.40, 1.05, 0.60), 40, 0, 0.45),
    Crop("sorghum", "Sorghum", "kharif", "Poaceae", False, 6, 20, 65, 105,
         10.0, 40.0, (-5, 15), 8, None, (0.30, 1.05, 0.55), 50, 0, 0.35, True),
    # ---- Rabi (winter) ----
    Crop("wheat", "Wheat", "rabi", "Poaceae", False, 11, 15, 115, 150,
         0.0, 34.0, (0, 30), 10, 0.0, (0.40, 1.15, 0.40), 30, 0, 0.60),
    Crop("chickpea", "Chickpea", "rabi", "Fabaceae", True, 10, 25, 120, 160,
         0.0, 33.0, (0, 30), 8, 1.0, (0.40, 1.00, 0.35), 30, 0, 0.50, True),
    Crop("canola", "Canola / mustard", "rabi", "Brassicaceae", False, 10, 20, 105, 155,
         0.0, 30.0, (0, 30), 8, 1.0, (0.35, 1.10, 0.35), 30, 0, 0.55, True),
    Crop("lentil", "Lentil", "rabi", "Fabaceae", True, 11, 1, 110, 150,
         0.0, 32.0, (0, 30), 8, 1.0, (0.40, 1.05, 0.35), 30, 0, 0.45),
]}

KHARIF = [k for k, c in CROPS.items() if c.season == "kharif"]
RABI = [k for k, c in CROPS.items() if c.season == "rabi"]

# Demo districts (lat, lon). Data for these is cached in data/ by fetch_power.py
DISTRICTS = {
    "Sargodha": (32.08, 72.67),
    "Khushab": (32.30, 72.35),
    "Faisalabad": (31.42, 73.08),
    "Multan": (30.20, 71.47),
    "Bahawalpur": (29.40, 71.68),
    "Sialkot": (32.49, 74.52),
}
