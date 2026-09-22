# Culture × Δ-metric co-movement (Plan C optional)

## Method

- One row per recording (n=4 Adam cultures).
- Region split = same screen harness logic: `partition_regions` / `_injury_region_split` with injury from novel `injury_start_s`/`injury_end_s` (written by novel build via matref + `pick_primary_injury`).
- **Δ columns:** for novel `*_delta`, culture mean of per-unit deltas; for unit metrics, median-across-units of (unit post median − unit baseline median); for window metrics, mean(post regions) − mean(baseline regions).
- Recovery `tau_rec_*` are times (s); `*_ratio_*` are post/baseline ratios (not true deltas). PCA uses the coherent Δ set only (standardized columns).
- **Descriptive only.** n=4 → no inference, no LOO classifiers, no p-values.

Matrix CSV: `reports/screen/culture_delta_matrix.csv`

Figures: `reports/screen/comovement_corr.png`, `reports/screen/comovement_pca.png`

## Table snapshot (PCA Δ columns)

| recording | rate_hz | burst_count | sttc_mean_unit | sttc_degree | sttc_rate_resid_unit | sttc_mean_window | sttc_rate_resid_window | rate_hz_delta | burst_count_delta | sttc_mean_unit_delta | sttc_degree_delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `SMJM_Bicuculline` | 0.3682 | 35.5 | 0.303 | 8.5 | 0.2917 | 0.315 | 0.005063 | 1.536 | 27.95 | 0.3376 | 12.56 |
| `ER52_ImpactWithBicuculline` | 0.004767 | 21 | 0.01964 | -2 | 0.0202 | 0.02158 | 0.02657 | -0.006114 | 13.51 | 0.02207 | -4.449 |
| `JMSM_ImpactWithoutBicuculline` | -0.5196 | -23 | -0.05381 | -4 | -0.02222 | -0.05174 | -0.006739 | -0.6654 | -35.79 | -0.06339 | -3.561 |
| `SM_pHshock` | -0.3384 | -12 | 0.07611 | -1 | 0.0853 | 0.06273 | 0.1253 | -0.4167 | -22 | 0.07174 | -1.088 |

## Field kinds (ratios / taus excluded from PCA)

| field | kind |
|---|---|
| `burst_rate_ratio_post0` | ratio |
| `burst_rate_ratio_post_mid` | ratio |
| `burst_rate_ratio_post_last` | ratio |
| `rate_ratio_post0` | ratio |
| `rate_ratio_post_mid` | ratio |
| `rate_ratio_post_last` | ratio |
| `tau_rec_burst_s` | tau_s |
| `tau_rec_rate_s` | tau_s |

## PCA (standardized Δ columns)

- Variance explained: **PC1=82.7%, PC2=10.9%**
- Top PC1 loadings (signed):

  - `rate_hz_delta`: 0.3292
  - `sttc_degree`: 0.3265
  - `sttc_mean_window`: 0.326
  - `sttc_mean_unit_delta`: 0.3253
  - `sttc_mean_unit`: 0.323
  - `sttc_rate_resid_unit`: 0.3193
  - `rate_hz`: 0.3137
  - `sttc_degree_delta`: 0.3106
  - `burst_count`: 0.2903
  - `burst_count_delta`: 0.2881
  - `sttc_rate_resid_window`: -0.06727
- Top PC2 loadings (signed):

  - `sttc_rate_resid_window`: 0.7751
  - `burst_count`: -0.3013
  - `burst_count_delta`: -0.2894
  - `sttc_rate_resid_unit`: 0.2202
  - `rate_hz`: -0.2018
  - `sttc_mean_unit`: 0.2014
  - `sttc_mean_unit_delta`: 0.1701
  - `sttc_mean_window`: 0.1532

## Co-moving pairs (|r|≥0.7 among PCA Δ cols)

- `sttc_mean_window` ↔ `sttc_mean_unit_delta`: r=0.9996
- `burst_count` ↔ `burst_count_delta`: r=0.9995
- `sttc_mean_unit` ↔ `sttc_mean_unit_delta`: r=0.9994
- `sttc_mean_unit` ↔ `sttc_mean_window`: r=0.9983
- `sttc_mean_unit` ↔ `sttc_rate_resid_unit`: r=0.9975
- `sttc_degree` ↔ `sttc_mean_window`: r=0.9971
- `sttc_rate_resid_unit` ↔ `sttc_mean_unit_delta`: r=0.9962
- `sttc_rate_resid_unit` ↔ `sttc_mean_window`: r=0.996
- `sttc_degree` ↔ `sttc_mean_unit_delta`: r=0.9947
- `sttc_degree` ↔ `sttc_rate_resid_unit`: r=0.9919
- `sttc_mean_unit` ↔ `sttc_degree`: r=0.9915
- `rate_hz` ↔ `burst_count`: r=0.9849
- `rate_hz` ↔ `burst_count_delta`: r=0.9822
- `sttc_degree` ↔ `sttc_degree_delta`: r=0.9814
- `sttc_rate_resid_unit` ↔ `sttc_degree_delta`: r=0.9778
- `sttc_mean_window` ↔ `sttc_degree_delta`: r=0.9707
- `sttc_degree` ↔ `rate_hz_delta`: r=0.9703
- `sttc_mean_unit_delta` ↔ `sttc_degree_delta`: r=0.9656
- `sttc_mean_unit` ↔ `sttc_degree_delta`: r=0.9638
- `sttc_mean_window` ↔ `rate_hz_delta`: r=0.9602

## Takeaway (3–5 sentences, descriptive)

Across the four cultures, PC1 explains ~83% of standardized Δ variance (PC2 ~11%). Nearly all coherent Δ-metrics (rate, burst, STTC mean/degree, unit rate-residual STTC, and novel `*_delta` means) load with the same PC1 sign, so post−baseline excitability and topology tend to co-move as one descriptive axis — SMJM up, JMSM/pHshock down, ER52 near flat. `sttc_rate_resid_window` is the clear odd-one-out (near-zero PC1, dominant PC2), hinting window-level residual sync is less locked to the rate/topology bundle here. Ratio and τ_rec fields stay in the CSV only; they are not Δ-units and were excluded from PCA. **Hard caveat: n=4, descriptive only — no inference, no LOO/classifiers, no screen-threshold changes.**

