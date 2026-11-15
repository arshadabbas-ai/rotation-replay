# AI acknowledgement: this file was drafted with an AI assistant (Claude, Anthropic)
# and reviewed and edited by team Signal2Decision. See README "Use of AI".
"""Rotation Replay - NASA Space Apps Challenge 2026, Field Shift.
Run:  python -m streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from crops import CROPS, DISTRICTS, KHARIF, RABI
from engine import (IRRIGATION_CAP, SOIL, STRESS_CUTOFF, TRAITS, Replayer, Weather,
                    phenology_check, trait_gap)
from fetch_power import fetch, slug

DATA_DIR = Path(__file__).parent / "data"
ORANGE = "#d9730d"
st.set_page_config(page_title="Rotation Replay", page_icon="🌾", layout="wide")


@st.cache_data(show_spinner="Loading NASA POWER daily weather ...")
def load_weather(name, lat, lon):
    path = DATA_DIR / f"{slug(name)}.csv"
    if path.exists():
        return pd.read_csv(path, index_col="date", parse_dates=True), "cached file"
    return fetch(lat, lon), "live NASA POWER API"


@st.cache_resource(show_spinner="Replaying four decades of seasons ...")
def get_replayer(name, lat, lon, soil, irrigation):
    df, source = load_weather(name, lat, lon)
    return Replayer(Weather(df, lat), soil, irrigation), source


def strip_chart(df, kc, rc, height=56):
    """One cell per season and crop, coloured by stress (single-hue sequential scale)."""
    rows = ((kc, "k_stress", "k_driver", "k_heat_days"), (rc, "r_stress", "r_driver", "r_heat_days"))
    for i, (crop, s_col, d_col, h_col) in enumerate(rows):
        last = i == len(rows) - 1
        data = pd.DataFrame({"Season": df["label"], "Crop": crop.name, "Stress": df[s_col].round(2),
                             "Main driver": df[d_col], "Heat days": df[h_col], "cell": 1})
        st.vega_lite_chart(data, {
            "title": {"text": crop.name, "anchor": "start", "fontSize": 13},
            "mark": {"type": "bar", "stroke": "white", "strokeWidth": 1},
            "encoding": {
                "x": {"field": "Season", "type": "ordinal", "sort": list(df["label"]), "title": None,
                      "scale": {"paddingInner": 0.06},
                      "axis": {"labelAngle": -90, "labelOverlap": True} if last else None},
                "y": {"field": "cell", "type": "quantitative", "axis": None,
                      "scale": {"domain": [0, 1]}},
                "color": {"field": "Stress", "type": "quantitative",
                          "scale": {"domain": [0, 1], "scheme": "oranges"},
                          "legend": {"title": "Stress (0 to 1)", "orient": "bottom"} if last else None},
                "tooltip": [{"field": f, "type": t} for f, t in (
                    ("Season", "nominal"), ("Crop", "nominal"), ("Stress", "quantitative"),
                    ("Main driver", "nominal"), ("Heat days", "quantitative"))],
            },
            "height": height,
        }, width="stretch")


def headline(s, ref=None):
    """Four headline numbers for a rotation, with deltas against a reference rotation."""
    c1, c2, c3, c4 = st.columns(4)
    d = (lambda k, fmt: None) if ref is None else (lambda k, fmt: fmt.format(s[k] - ref[k]))
    c1.metric("Stressed seasons", f"{s['stressed']} of {s['seasons']}", d("stressed", "{:+d}"),
              delta_color="inverse")
    c2.metric("In the last 15 years", f"{s['stressed_recent']} of {s['recent_seasons']}",
              d("stressed_recent", "{:+d}"), delta_color="inverse")
    c3.metric("Irrigation need", f"{s['water_mm']:.0f} mm / year", d("water_mm", "{:+.0f} mm"),
              delta_color="inverse")
    c4.metric("Soil-health score", f"{s['soil']:.2f} / 1", d("soil", "{:+.2f}"))


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Your farm")
    place = st.selectbox("Location", list(DISTRICTS) + ["Custom location"])
    if place == "Custom location":
        lat = st.number_input("Latitude", -60.0, 60.0, 31.50, 0.01)
        lon = st.number_input("Longitude", -180.0, 180.0, 74.30, 0.01)
        name = f"custom_{lat:.2f}_{lon:.2f}"
        st.caption("Crop calendar is tuned for Punjab, Pakistan. Other regions need their own crop table.")
    else:
        (lat, lon), name = DISTRICTS[place], place
    soil = st.selectbox("Soil texture", list(SOIL), index=1)
    irrigation = st.selectbox("Irrigation access", list(IRRIGATION_CAP),
                              help="Limited = about 350 mm available per season.")
    st.header("Current rotation")
    kharif = st.selectbox("Summer (kharif) crop", KHARIF, format_func=lambda k: CROPS[k].name)
    rabi = st.selectbox("Winter (rabi) crop", RABI, format_func=lambda k: CROPS[k].name)
    st.header("Your priorities")
    weights = {
        "risk": st.slider("Climate resilience", 0, 5, 3),
        "water": st.slider("Saving water", 0, 5, 3),
        "soil": st.slider("Soil health", 0, 5, 3),
        "profit": st.slider("Income", 0, 5, 3),
    }

st.title("🌾 Rotation Replay")
st.caption("How would your crop rotation have survived the weather that actually happened? "
           "Every season since 1981, replayed with NASA POWER daily data.")

try:
    rp, source = get_replayer(name, lat, lon, soil, irrigation)
except Exception as e:  # no cached file and no network
    st.error(f"Could not load weather data for this location ({e}). "
             "Run `python fetch_power.py` once to cache the demo districts.")
    st.stop()

df = rp.replay(kharif, rabi)
cur = rp.summarise(kharif, rabi, df)
kc, rc = CROPS[kharif], CROPS[rabi]
table = rp.rank(weights)
is_cur = (table.kharif == kharif) & (table.rabi == rabi)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1 · Survival record", "2 · Season explorer", "3 · Compare rotations",
    "4 · What-if: variety and sowing", "5 · Data and method"])

# ------------------------------------------------------- 1. survival record
with tab1:
    st.subheader(f"{cur['rotation']} at {place}, {df['label'].iloc[0]} to {df['label'].iloc[-1]}")
    headline(cur)
    strip_chart(df, kc, rc)
    st.caption(f"Each cell is one season, labelled sowing year / harvest year. A season counts as "
               f"stressed when its score reaches {STRESS_CUTOFF}. Hover a cell for details, then open "
               "tab 2 to see that season day by day.")
    worst = df.assign(total=df["k_stress"] + df["r_stress"]).nlargest(3, "total")
    st.markdown("**Hardest years:** " + "; ".join(
        f"{r.label} ({kc.name} {r.k_stress:.1f}, {r.k_driver}; {rc.name} {r.r_stress:.1f}, {r.r_driver})"
        for r in worst.itertuples()))
    if cur["rabi_delay"] > 0:
        st.info(f"{kc.name} is usually still in the field at {rc.name} sowing time, so winter sowing "
                f"slips by a median of {cur['rabi_delay']:.0f} days. Late sowing pushes flowering "
                "into hotter weather.")

    st.subheader("Is it getting worse?")
    which = st.radio("Crop", [rc.name, kc.name], horizontal=True, key="trend_crop")
    col, crop = ("r_heat_days", rc) if which == rc.name else ("k_heat_days", kc)
    thr = rp.heat_thr[crop.key]
    base_y = df["year"] < df["year"].min() + 20
    rec_y = df["year"] >= df["year"].max() - 14
    b, r = df.loc[base_y, col].mean(), df.loc[rec_y, col].mean()
    m1, m2 = st.columns(2)
    m1.metric(f"Average heat days, {df['year'].min()} to {df['year'].min() + 19}", f"{b:.1f} days")
    m2.metric("Average heat days, last 15 years", f"{r:.1f} days", f"{r - b:+.1f} days",
              delta_color="inverse")
    heat = pd.DataFrame({"Season": df["label"], "Heat days": df[col]})
    st.vega_lite_chart(heat, {
        "mark": {"type": "bar", "color": ORANGE, "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
        "encoding": {
            "x": {"field": "Season", "type": "ordinal", "sort": list(df["label"]), "title": None,
                  "axis": {"labelAngle": -90, "labelOverlap": True}},
            "y": {"field": "Heat days", "type": "quantitative",
                  "title": f"Days above {thr:.1f} °C"},
            "tooltip": [{"field": "Season", "type": "nominal"},
                        {"field": "Heat days", "type": "quantitative"}],
        },
        "height": 220,
    }, width="stretch")
    st.caption(f"Heat days in the {crop.name} sensitive window (around flowering and grain or boll "
               f"filling). Local threshold {thr:.1f} °C: the higher of the crop threshold "
               f"({crop.heat_thr:.0f} °C) and the 90th percentile for that crop stage here in the "
               "first 20 years.")
    st.download_button("Download this replay as CSV", df.to_csv(index=False),
                       file_name=f"rotation_replay_{slug(place)}_{kharif}_{rabi}.csv", mime="text/csv")

# --------------------------------------------------------- 2. season explorer
with tab2:
    st.subheader("Replay one season day by day")
    e1, e2 = st.columns([2, 1])
    default = str(worst.iloc[0]["label"])
    label = e1.select_slider("Season (sowing year / harvest year)", options=list(df["label"]), value=default)
    side = e2.radio("Crop", [rc.name, kc.name], horizontal=True, key="explore_crop")
    year = int(df.loc[df["label"] == label, "year"].iloc[0])
    daily, info = rp.detail(kharif, rabi, year, "rabi" if side == rc.name else "kharif")
    c = info["crop"]
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Sown", info["sow_date"].strftime("%d %b %Y"),
              f"{info['delay']} days late" if info.get("delay", 0) > 0 else None, delta_color="inverse")
    a2.metric("Flowering", info["flower_date"].strftime("%d %b %Y"))
    a3.metric("Maturity", info["maturity_date"].strftime("%d %b %Y"))
    a4.metric("Heat days", f"{info['heat_days']}")
    a5.metric("Season stress", f"{info['stress']:.2f}", info["driver"], delta_color="off")
    st.vega_lite_chart(daily, {
        "layer": [
            {"data": {"values": [{"start": str(info["w0_date"]), "end": str(info["w1_date"])}]},
             "mark": {"type": "rect", "color": ORANGE, "opacity": 0.15},
             "encoding": {"x": {"field": "start", "type": "temporal"}, "x2": {"field": "end"}}},
            {"mark": {"type": "line", "strokeWidth": 2, "color": "#555555"},
             "encoding": {
                 "x": {"field": "Date", "type": "temporal", "title": None},
                 "y": {"field": "Tmax", "type": "quantitative", "title": "Daily maximum temperature (°C)",
                       "scale": {"zero": False}},
                 "tooltip": [{"field": "Date", "type": "temporal"}, {"field": "Tmax", "type": "quantitative"},
                             {"field": "Tmin", "type": "quantitative"}, {"field": "Rain", "type": "quantitative"}]}},
            {"mark": {"type": "rule", "color": ORANGE, "strokeDash": [6, 4], "strokeWidth": 2},
             "encoding": {"y": {"datum": round(info["heat_thr"], 1)}}},
        ],
        "height": 300,
    }, width="stretch")
    st.caption(f"Grey line: daily maximum temperature from sowing to 10 days after maturity. Shaded band: "
               f"the {c.name} sensitive window. Dashed line: heat threshold ({info['heat_thr']:.1f} °C). "
               f"Days above the dashed line inside the band are heat days. Season rainfall "
               f"{info['rain_mm']:.0f} mm, irrigation applied {info['irrigation_mm']:.0f} mm, "
               f"rain in the 10 days after maturity {info['harvest_rain_mm']:.0f} mm.")

# ------------------------------------------------------------ 3. alternatives
with tab3:
    rank_me = int(table.index[is_cur][0]) + 1
    st.subheader("Rotations that fit your priorities")
    st.write(f"Your current rotation ranks **{rank_me} of {len(table)}** for the priorities set in the "
             "sidebar. Move the sliders to see the ranking change.")
    alts = table[~is_cur]
    for colm, a in zip(st.columns(3), alts.head(3).itertuples()):
        with colm:
            st.markdown(f"#### {a.rotation}")
            st.metric("Stressed seasons", f"{a.stressed} of {a.seasons}",
                      f"{a.stressed - cur['stressed']:+d} vs current", delta_color="inverse")
            st.metric("Irrigation need", f"{a.water_mm:.0f} mm / year",
                      f"{a.water_mm - cur['water_mm']:+.0f} mm", delta_color="inverse")
            st.metric("Soil-health score", f"{a.soil:.2f}", f"{a.soil - cur['soil']:+.2f}")
            st.caption("Soil: " + "; ".join(a.soil_notes) + ".")

    st.subheader("Compare side by side")
    pick = st.selectbox("Compare the current rotation with", list(alts["rotation"]))
    alt = alts[alts["rotation"] == pick].iloc[0]
    adf = rp.replay(alt.kharif, alt.rabi)
    st.markdown(f"**Current: {cur['rotation']}**")
    strip_chart(df, kc, rc)
    st.markdown(f"**Alternative: {pick}** (changes are relative to the current rotation)")
    headline(rp.summarise(alt.kharif, alt.rabi, adf), cur)
    strip_chart(adf, CROPS[alt.kharif], CROPS[alt.rabi])
    with st.expander("All 20 rotations"):
        show = table[["rotation", "score", "stressed", "stressed_recent", "water_mm", "soil", "return"]].copy()
        show.columns = ["Rotation", "Priority score", "Stressed seasons", "Stressed (last 15 yrs)",
                        "Irrigation mm/yr", "Soil health", "Risk-adjusted return index"]
        st.dataframe(show.round(2), hide_index=True, width="stretch")

# ----------------------------------------------------------------- 4. what-if
with tab4:
    st.subheader("What would a different variety or sowing date have rescued?")
    st.write("Change one crop and the whole record is replayed again. This links the rotation choice to "
             "the variety choice: it shows which trait is worth asking a breeder or seed dealer for.")
    w0, w1, w2, w3 = st.columns([1.2, 1, 1, 1])
    target = w0.radio("Crop to change", [rc.name, kc.name], key="whatif_crop")
    tkey = rabi if target == rc.name else kharif
    dur = w1.slider("Crop duration (%)", -20, 10, 0, 5, help="Negative = earlier-maturing variety.")
    tol = w2.slider("Extra heat tolerance (°C)", 0.0, 4.0, 0.0, 0.5)
    shift = w3.slider("Sowing date shift (days)", -20, 20, 0, 5, help="Negative = sow earlier.")
    trait = {tkey: {"gdd_scale": 1 + dur / 100, "heat_plus": tol, "sow_shift": shift}}
    wdf = rp.replay(kharif, rabi, trait)
    wsum = rp.summarise(kharif, rabi, wdf, trait)
    headline(wsum, cur)
    col = "r_stress" if tkey == rabi else "k_stress"
    m = df[["year", col]].merge(wdf[["year", col]], on="year", suffixes=("", "_new"))
    was, now = m[col] >= STRESS_CUTOFF, m[col + "_new"] >= STRESS_CUTOFF
    st.markdown(f"**{CROPS[tkey].name}:** {int((was & ~now).sum())} stressed seasons rescued, "
                f"{int((~was & now).sum())} newly stressed.")
    strip_chart(wdf, kc, rc)
    st.markdown("**Standard options, one change at a time**")
    st.dataframe(trait_gap(rp, kharif, rabi), hide_index=True, width="stretch")
    st.caption("Options tested: " + ", ".join(TRAITS) + ".")

# ------------------------------------------------------- 5. method and limits
with tab5:
    st.markdown(f"""
**NASA data.** NASA POWER daily agroclimatology (community AG): maximum and minimum 2 m
temperature and bias-corrected precipitation, {rp.wx.first_year} to {rp.wx.last_year},
for latitude {lat:.2f}, longitude {lon:.2f}. Loaded from: {source}.

**Method.** Each crop's thermal-time need is calibrated on this location's first 20 years, so
hot years develop faster. For every season the engine counts heat days in the crop's sensitive
window, frost days near flowering, the irrigation gap (FAO-56 crop coefficients with
Hargreaves reference evapotranspiration, 75% effective rainfall) and rain at harvest.
A heat day must be hotter than both the crop's threshold and the local 90th percentile for
that crop stage in the first 20 years. The winter crop is only sown once the summer crop is
off the field.

**Limits.** Stress scores are agronomic screening proxies, not yield predictions. Crop
thresholds and the return index are editable assumptions in `crops.py` and should be checked
against local extension guidance. POWER is a roughly 50 km gridded product, so it describes
the district climate, not one field. Pests, prices and groundwater quality are not modelled.

**Use of AI.** Code was drafted with an AI assistant (Claude, Anthropic) and reviewed by the team.
""")
    st.markdown("**Simulated crop calendar and heat thresholds (sanity check)**")
    st.dataframe(phenology_check(rp), hide_index=True, width="stretch")
