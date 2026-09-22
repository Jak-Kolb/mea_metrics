# mea_metrics

Python port of Casey Adam’s MEA correlogram / metrics pipeline (see sibling `original_mea_matlab`).

## Status (2026-09-22)

| Stage | SMJM_Bicuculline | ER52 / JMSM / SM_pHshock |
|---|---|---|
| 0–1 harness / rasters | PASS | PASS (pH: 1-sample end_time OK) |
| 2 regions | PASS | PASS |
| 3 correlograms | PASS | PASS (jakpc) |
| 4 metrics | PASS (peaks report-only) | PASS (peaks report-only) |
| 5 summary | PASS | PASS |
| 6 multi-recording package | — | **PASS** — `reports/stage6/STAGE6_MATRIX.md` |

Peak-count match vs MATLAB `RecordingMetrics` is **not** a fail bar (Jak gate). Stage 6 peaks: ER52 ~99.3%; JMSM / SM_pHshock ~89% — see `PORT_NOTES.md`.

## Setup

```bash
cd mea_metrics
python3 -m venv .venv && .venv/bin/pip install -e '.[plx]'
export MEA_MATLAB_DATA=/path/to/data   # must contain matlab_reference/ and raw/
```

On this Mac, `data` → `original_mea_matlab/data`.

## Verify

```bash
.venv/bin/python verify.py SMJM_Bicuculline --stage all
.venv/bin/python verify.py ER52_ImpactWithBicuculline --stage correlograms
```

Stages: `ref`, `rasters`, `regions`, `correlograms`, `metrics`, `summary`, `all`.

## Notes

- MATLAB source wins on conflicts → document in `PORT_NOTES.md`.
- Never commit in `original_mea_matlab` (local reference only).
- Open items: `QUESTIONS.md`.

## Metric library (Plan A)

Defaults and parameter locks live in [`LIBRARY_NOTES.md`](LIBRARY_NOTES.md) (region windows from AnalysisRegions; burst/STTC knobs).

### Run

```bash
# A1 path (rate/ISI; writes the same extended A2 columns today)
.venv/bin/python -m mea_metrics.library A1 --recording SMJM_Bicuculline

# A2 — rate/ISI + bursts + STTC + health (all four Adam recordings)
.venv/bin/python -m mea_metrics.library A2 --all

# or one recording
.venv/bin/python -m mea_metrics.library A2 --recording SMJM_Bicuculline
```

### Outputs

| File | Contents |
|---|---|
| `reports/library/<recording>_metrics.parquet` | Full unit × region table |
| `reports/library/<recording>_metrics_preview.csv` | First ~40 rows for eyeballing |

Recordings: `SMJM_Bicuculline`, `ER52_ImpactWithBicuculline`, `JMSM_ImpactWithoutBicuculline`, `SM_pHshock`.

### A2 columns (beyond A1 rate/ISI)

- Bursts: `burst_count`, `burst_spike_frac`, `mean_ibi_s` (`max_isi_s=0.1`, `min_spikes=3`)
- STTC: `sttc_mean_window`, `sttc_mean_unit`, `sttc_degree` (`dt_s=0.05`, degree thresh `0.1`)
- Health: `is_active`, `is_silent`

