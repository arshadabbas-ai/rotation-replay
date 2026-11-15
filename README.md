# Rotation Replay

**NASA Space Apps Challenge 2026 · Field Shift: Adapting Farms with NASA Data · Team Signal2Decision**

Most crop tools answer "what should I plant?" from average climate. Rotation Replay asks a
different question: **how would this rotation have survived the weather that actually
happened since 1981, and is it getting worse?**

A farmer enters location, soil texture, irrigation access, current rotation and priorities.
The tool replays every summer (kharif) and winter (rabi) season against NASA POWER daily
weather and reports:

1. **Survival record** – stressed seasons out of all seasons, year by year, with the main driver
   (heat, frost, water, harvest rain).
2. **Trend** – heat days in the winter crop's sensitive window, baseline versus the last 15 years.
3. **Alternatives** – all 20 kharif × rabi rotations ranked by the farmer's own priorities
   (climate resilience, water, soil health, income).
4. **Season explorer** – any single season day by day: sowing, flowering, maturity, the sensitive
   window and the heat threshold.
5. **Trait gap / what-if** – the replay re-run with an earlier-maturing variety, a more heat-tolerant
   variety, or earlier sowing, showing how many stressed seasons each would have rescued.

## Run it

```bash
pip install -r requirements.txt
python fetch_power.py        # one-time: caches NASA POWER data for 6 Punjab districts in data/
python tests/test_engine.py  # optional smoke test (uses synthetic weather, not NASA data)
streamlit run app.py
```

Commit the `data/*.csv` files so the deployed app needs no live API call.
Deploy free on Streamlit Community Cloud: New app → this repo → main file `app.py`.

## NASA data

NASA POWER Project (https://power.larc.nasa.gov), daily point API, community `AG`, no key needed:
`T2M_MAX`, `T2M_MIN` (2 m air temperature, °C) and `PRECTOTCORR` (bias-corrected
precipitation, mm/day), 1981 to mid-2026.

## Method

- **Phenology:** thermal time (growing degree days), calibrated per location on its first 20 years.
- **Heat / frost:** days beyond the threshold in the flowering and grain-fill window. A heat day must
  exceed both the crop threshold and the local 90th percentile for that crop stage (first 20 years).
- **Water:** FAO-56 crop coefficients × Hargreaves reference evapotranspiration, 75% effective
  rainfall, soil-texture loss factor, irrigation cap by access level.
- **Rotation interaction:** the winter crop is sown only after the summer crop is harvested,
  so a late summer crop pushes winter flowering into hotter weather.
- **Soil health:** transparent rules (legume, crop-family diversity, deep roots, puddled rice,
  turnaround pressure).

## Limits

- Stress scores are agronomic screening proxies, **not yield predictions**.
- Crop thresholds, calendars and the return index in `crops.py` are editable assumptions for
  Punjab, Pakistan, and need checking against local extension guidance.
- POWER is a ~50 km gridded product: it describes district climate, not a single field.
- Pests, prices, groundwater quality and soil chemistry are not modelled.

## Use of AI

Code and documentation were drafted with Claude (Anthropic) and reviewed, tested and edited by
the team. No AI-generated images, video or audio are used.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface |
| `engine.py` | Replay engine, scoring, ranking, trait gap |
| `crops.py` | Crop knowledge base and demo districts |
| `fetch_power.py` | NASA POWER download and cache |
| `diagnose.py` | Calibration diagnostics on the real data |
| `tests/test_engine.py` | Smoke test on synthetic weather |
