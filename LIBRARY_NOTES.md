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

No ML, no novel recovery/topology metrics yet (Plan C), no calcium (Plan D).
