# Analysis (pilot 2)

One command from the raw results to the report, with the decisions fixed before data collection.

## Run on real data

1. In the Google Sheet, download the tabs **trials** and **sessions** as CSV (File > Download > CSV, one tab at a time).
2. Put them in a folder that is **not** inside this repository (participant data must not be pushed).
3. Run:

```sh
pip install pandas scipy statsmodels matplotlib
python analysis/run_analysis.py --sheet path/to/trials.csv path/to/sessions.csv --out path/to/out
```

Result files sent by e-mail (when a participant's transmission failed) can be read instead with
`--json path/to/levelandtiming_*.json`. Both inputs give the same numbers.

Output per mode (lab = main data, online = secondary, analysed separately):

| file | what |
|---|---|
| `report_lab.md` | the report: exclusions, planned contrasts, sensitivity analysis, mixed model, data quality, limits |
| `fig_contrasts_lab.png/.svg` | planned contrasts with CIs |
| `fig_means_lab.png/.svg` | mean answers by seat × level ratio × ITDG |
| `contrasts_lab_main.csv`, `contrasts_lab_all.csv` | contrasts after / before exclusions |
| `lmm_lrt_lab_main.csv`, `lmm_lrt_lab_all.csv` | mixed-model likelihood-ratio tests |
| `screening_lab.csv` | criteria A and B per participant |
| `sessions_all.csv` | every session received, with the reason it was dropped (debug, test code, incomplete, repeat) |

## What it does (fixed in advance)

- **Cleaning:** drops debug runs, participant codes containing `TEST`, other site versions, unfinished sessions,
  and a second session of the same participant code; removes re-sent duplicate trials.
- **Exclusion:** criteria A (hidden reference, Q2 ≤ 2 in 2 of 4) and B (centre-seat retest mean |difference| ≥ 1.6),
  same rule as `tools/screening.py`. Every analysis is reported with and without the excluded listeners.
- **Primary tests:** each listener's contrast of mean answers, one-sample t over listeners (as in `tools/power_sim.py`),
  effect in answer points with 95 % CI and d_z.
  - H1: mean(−6, −3 dB) vs +6 dB, Holm over Q1–Q3
  - level steps −6/−3, −3/0, 0/+6: Bonferroni × 4; −9 vs −6: equivalence (TOST, ±0.3 points, 90 % CI)
  - ITDG 0/20, 0/40, 20/40 ms: Holm within each item
  - H2: ITDG × seat = (20 − 0 ms at the side seats) − (20 − 0 ms at the centre); secondary: side seats, 20 ms vs mean(0, 40)
  - ITDG × level: exploratory
- **Supporting model:** linear mixed model, answer ~ level × ITDG × seat (sum coding) + random intercept per listener,
  likelihood-ratio test per term. The answers are 5-point ordinal, so this is an approximation; the contrasts are primary.
- **Data quality:** hidden-reference answers, `q1_hard` rate, centre-seat retest, Q1–Q3 separability, duration,
  listening time, comprehension-quiz attempts, post-questionnaire, Mac volume (lab).

## Test with simulated data

```sh
python analysis/simulate.py --out /tmp/sim
python analysis/run_analysis.py --sheet /tmp/sim/trials.csv /tmp/sim/sessions.csv --out /tmp/sim_out
```

`simulate.py` makes **simulated** answers from assumed effects (the pilot-1 sizes used in the power analysis) and plants
a debug session, a test code, an unfinished session, re-sent duplicates and two random responders. The report then starts
with a banner saying the data are simulated. These numbers are not perceptual results.
