# Library notes (Plan A defaults)

Locked 2026-09-22 with Jak. Change here when defaults change.

## Defaults

| Choice | Value |
|---|---|
| Windows | **Region-aligned** tiles from `AnalysisRegions` when present; fixed `win_s`/`step_s` grid is a later optional mode |
| Bursts | **Max-interval** detector; parameters documented below (tunable, not magic) |
| Pairwise connectivity | **STTC** (Cutts & Eglen 2014, DOI 10.1523/JNEUROSCI.2767-14.2014) |
| First recording | **SMJM_Bicuculline** (A1), then all four Adam recordings (A2) |
| Outputs | `reports/library/<recording>_metrics.parquet` (+ small CSV preview) |

## Burst detector (max-interval) — initial params

- A burst = run of ≥ `min_spikes` spikes with all consecutive ISIs ≤ `max_isi_s`.
- Start: `max_isi_s = 0.1`, `min_spikes = 3` (common culture defaults; revisit after SMJM smoke).
- Report per unit × window: burst count, fraction of spikes in bursts, mean IBI (NaN if <2 bursts).

## STTC

- Pairwise spike-time tiling coefficient; exclude silent units in a window (spike count = 0).
- Window-level summary: mean STTC over active pairs (optional: residualize vs mean firing rate in Plan C).

## Rate / ISI (A1)

Per unit × region window: mean rate (Hz), ISI mean/median, CV_ISI (NaN if <2 ISIs).

## Non-goals for A1

A1 shipped rate/ISI only. Bursts/STTC/health arrived in A2.

## STTC params (A2)

- `dt_s = 0.05` (50 ms tiling half-width; common culture default).
- Exclude silent units (0 spikes in the window) from pairs.
- Per window: `sttc_mean_window` = mean over active pairs.
- Per unit: `sttc_mean_unit` = mean STTC to other active units; `sttc_degree` = count of partners with STTC > `0.1` (thin topology v1).

## Electrode health (A2, basic)

Per unit × window: `is_active` / `is_silent` (spike count > 0).

## Non-goals for A2

No ML, no Plan C novel metrics, no calcium (Plan D). Topology beyond degree-on-thresholded-STTC stays for later.

## Screening thresholds (B1, frozen on SMJM 2026-09-22)

Applied by `python -m mea_metrics.screen`. Change here when deliberately re-frozen.

| Bar | Rule |
|---|---|
| Baseline stability | Split-half Spearman of early vs late **baseline** regions ≥ **0.50**. Soft diagnostic: median unit CV ≤ 0.75. Window-level metrics with too few tiles may PASS on CV ≤ 0.75 if Spearman is undefined. |
| Beyond rate | \|Spearman(metric, `rate_hz`)\| < **0.90** across unit×region rows. `rate_hz` itself is SKIP. |
| Treatment response | \|Cohen's d\| between per-unit (or per-region) medians in **post** vs **baseline** ≥ **0.30**. *n=1 culture on SMJM; no holdout — asterisk in report.* |
| Interpretability | Metric has a registered plain-language blurb in `screen/interpret.py` (A v1 auto-PASS). |

Baseline / during / post regions are derived from `InjuryIndices` overlap with AnalysisRegions tiles.
