# Project page text (copy into the Project tab, then edit in your own words)

Replace every [bracket] with the real number or link from your own run.
Check each claim against what your app actually shows before you submit.

## Project Name
Rotation Replay

## High-Level Project Summary
Rotation Replay is a decision-support tool that replays a farmer's crop rotation against the
weather that actually happened in every season since 1981, using NASA POWER daily data. Instead
of recommending crops from average climate, it shows how often each crop in the rotation would
have been stressed by heat, frost, water shortage or harvest rain, whether that is getting worse,
and which alternative rotations fit the farmer's own priorities for resilience, water, soil health
and income. It also tests what an earlier-maturing or more heat-tolerant variety, or a changed
sowing date, would have rescued. It addresses Field Shift by combining NASA Earth observation
data with soil texture, crop characteristics and farmer priorities to explore rotations that
protect soil and adapt to changing conditions. The prototype covers six districts of Punjab,
Pakistan, where the rice-wheat and cotton-wheat systems face rising heat and water limits.

## Link to Project Demo
[public link to the 7-slide deck]

## Link to Final Project
[public GitHub repository link] (live app: [Streamlit link, if deployed])

## Detailed Project Description
**What it does.** The farmer chooses a location, soil texture, irrigation access, the current
summer (kharif) and winter (rabi) crop, and sets four priority sliders. The tool then shows:
1. Survival record: one cell per season from 1981/82 to 2025/26, coloured by stress, with the
   main driver. Example: at [district], [rotation] was stressed in [X] of 90 seasons, [Y] of them
   in the last 15 years.
2. Trend: heat days in the crop's sensitive window rose from [a] per season (1981-2000) to [b]
   (last 15 years) for [crop] at [district].
3. Season explorer: any season day by day, with sowing, flowering and maturity dates, the
   sensitive window and the heat threshold.
4. Alternatives: all 20 kharif x rabi rotations ranked by the farmer's priorities, with
   side-by-side comparison.
5. What-if: the record replayed with a shorter-duration variety, extra heat tolerance or a
   shifted sowing date, counting the stressed seasons rescued.

**How it works.** Crop development follows thermal time (growing degree days), calibrated at each
location on its first 20 years, so hot years develop faster. For each season the engine counts
heat days in the flowering and grain-fill window, frost days near flowering, the irrigation gap
(FAO-56 crop coefficients with Hargreaves reference evapotranspiration and 75% effective rainfall)
and rain in the 10 days after maturity. A heat day must exceed both the crop's threshold and the
local 90th percentile for that crop stage. The winter crop is only sown after the summer crop is
harvested, so a late summer crop delays winter sowing and pushes flowering into hotter weather.
Soil health is scored with transparent rules: legumes, crop-family diversity, deep roots,
puddled rice and turnaround pressure.

**Benefits.** Farmers and advisers see risk as a record of real years, not an abstract index.
Breeders and seed dealers see which trait would have mattered most in a given district.

**Limits.** Stress scores are agronomic screening proxies, not yield predictions. Crop thresholds
and the return index are editable assumptions. POWER is a roughly 50 km gridded product, so it
describes district climate, not one field. Pests, prices and groundwater quality are not modelled.

**What we hope to achieve.** Validate the stress record against district yield statistics, add
soil moisture and vegetation indices from satellite missions, and extend the crop table to other
regions.

**Tools.** Python, pandas, NumPy, Streamlit, Vega-Lite, GitHub, VS Code.

## Use of AI (answer truthfully; adjust to match what you actually did)
Yes. An AI assistant (Claude, Anthropic) was used to brainstorm and refine the approach, to draft
the Python code (engine, data download and Streamlit interface) and to draft documentation and
this project text. The team lead, a plant geneticist, reviewed the agronomic assumptions, ran and
checked the tool on NASA data, and edited the outputs. AI use is acknowledged in the README and in
a header comment in every code file. No AI-generated images, video or audio are used.

## NASA Data
NASA POWER (Prediction Of Worldwide Energy Resources) Project, daily point API, agroclimatology
community (AG), https://power.larc.nasa.gov. Parameters: T2M_MAX and T2M_MIN (2 m maximum and
minimum air temperature) and PRECTOTCORR (bias-corrected precipitation), 1 January 1981 to
30 June 2026, for six Punjab districts. The data drive crop development, heat and frost day
counts, reference evapotranspiration, irrigation need and harvest-rain risk in every replayed
season.

## Space Agency Partner Data and Other References
- NASA POWER Project data and API documentation, https://power.larc.nasa.gov
- Allen, Pereira, Raes and Smith (1998), Crop evapotranspiration, FAO Irrigation and Drainage
  Paper 56 (crop coefficients and the Hargreaves equation)
- Open-source software: Python, pandas, NumPy, Streamlit, Vega-Lite
- AI assistant: Claude (Anthropic), as described above
- [add any extension guides or papers you used to check crop thresholds]
