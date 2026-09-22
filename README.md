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

Defaults locked in `LIBRARY_NOTES.md` (region windows from AnalysisRegions).

**A1** — rate / ISI. **A2** — + max-interval bursts (`max_isi_s=0.1`, `min_spikes=3`), STTC (`dt_s=0.05`, mean over active pairs; per-unit mean + degree at thresh 0.1), basic active/silent flags.

```bash
.venv/bin/python -m mea_metrics.library A2 --all
# or one recording:
.venv/bin/python -m mea_metrics.library A2 --recording SMJM_Bicuculline
```

Writes `reports/library/<recording>_metrics.parquet` (+ CSV preview) for SMJM, ER52, JMSM, SM_pHshock.

