# Port notes — mea_metrics (Step 0+)

## Data path mapping (plan wording vs actual layout)

The tentative plan refers to the original MATLAB repo layout:

| Plan wording | Actual Mac / New Bot layout |
| --- | --- |
| `original_mea_matlab/Output Files/<recording>/*.mat` | `<matlab_repo>/data/matlab_reference/<recording>/*.mat` |
| `original_mea_matlab/Raw Recordings/<recording>.plx` | `<matlab_repo>/data/raw/<recording>.plx` |

On this box (local verify):

- Default data root: `/workspace/mea_metrics_port/data` (sibling of `src/`)
- Override: env `MEA_MATLAB_DATA`

On Mac later: point `MEA_MATLAB_DATA` (or symlink) at  
`/Users/jakkolb/Desktop/Coding/GitHub/original_mea_matlab/data`.

Resolved by `mea_metrics.config.matlab_data_root()`:

- `matlab_reference/<recording>/` — nine `.mat` reference files
- `raw/<recording>.plx` — raw Plexon (Stage 1+)

## MATLAB field names vs plan naming

Observed on `SMJM_Bicuculline` (scipy `loadmat(..., struct_as_record=False, squeeze_me=True)`):

| File | Top-level / fields used |
| --- | --- |
| `AnalysisRegions.mat` | `AnalysisRegions`: `Minutes` (14,2), `Seconds` (14,2), `numRegions` |
| `InjuryIndicies.mat` | **spelling is Indicies** (not Indices): `InjuryStartMin/EndMin/StartSec/EndSec`, `InjuryLabels`, `NumberOfInjuriesOrTreatments` |
| `badRegions.mat` | `badRegions.badRegionsIndicator` only (value 0); **no region table** when indicator=0 |
| `badSignals.mat` | top-level `badSignals` uint8 (50,) — all zeros for SMJM |
| `plotProps.mat` | `automatedRegionBinLength=7`, `unifPThresh=0.05`, `correlogramBinMax=1`, `numberOfCorrelogramBins=2001`, `correlogramSmoothingFactor=0.01`, `sparseCorrelogramThresh=0`, `includeAutocorrelogramsInStatistics=0`, `SmoothingWindowSize=20`, … |
| `ProcessedData.mat` | `CellIDs`, `CellDisplayNames`, `Raster`, `CellCount`, `NumberOfActiveElectrodes`, `TotalNumberOfElectrodes`, `ExperimentSamplFreq`, `ExperimentEndTime`, `ExperimentEndTimestamp`, `FiringCountOfEachCell`, `SpikeIntervals`, `RegionStats`, … |
| `RawData.mat` | plx-ish struct (`ADFrequency`, `LastTimestamp`, …) |
| `Correlograms.mat` | `CorrelogramBins`; `Region1`…`Region14` each: `CorrelogramProbabilities` (2001, n_pairs), `ComparisonNames`, `numberOfSpikesContributingToTheCorrelogram`, `CellAsComparisonInds`, `CellAsReferenceInds` |
| `RecordingMetrics.mat` | `meanSPM`, …; `CorrelogramMetrics.RegionK`: `leaderProb`, `followerProb`, `uniformityTest`, `uniformityTestPValue`, `correlogramPeaks`, `correlogramPeakLocations`, `numberOfCorrelogramPeaks`, `leaderProbMat`, `numPeaksMat`, `unifTestMat`, `unifTestpMat` |

## Region indexing in Python

`ref.correlograms` and `ref.metrics` use **0-based** int keys: `Region1 → 0`, …, `Region14 → 13`.

## Step 0 status

- `matref.load_reference` + `verify.py --stage ref` implemented.
- Pipeline modules (`plx`, `rasters`, …) are stubs only — Stage 1 not started.

## badRegions / bad_regions (settled 2026-09-19)

See `QUESTIONS.md` resolved section. Summary: `badRegionsIndicator==0` ⇒ no `badStartTime`/`badEndTime` fields in the mat (confirmed on all four recordings). Python exposes `bad_regions_indicator: int` and `bad_regions: list[tuple[start_s, end_s]]` (empty when indicator is 0). Times are inclusive seconds after MATLAB’s `.*60`.

## Stage 2 — regions / stats quirks

- Auto regions follow `getInjuryOrTreatmentIndicies.m` with `M = floor(end_time_s/60)` as `max(minBinsSPM)`.
- Region ends use `L/1000` minute gap; last region dropped if length/L < 0.8.
- Silent-minute filter: `minBinsSPM = 1..M`, region owns labels with `s <= label <= e`; drop if any owned minute has `meanSPM == 0`.
- `plotStatsInEachRegion.m` divides spike counts by region length in **seconds** while commenting "per minute" — replicated in `stats.compute_region_stats` (`spike_rate`).

## Stage 3 — correlograms

- Lag = `t_cmp - t_ref` (float64); window inclusive on both ends.
- `RegionTimes==60` → 0 quirk implemented.
- `searchsorted` path bit-identical to brute-force histogram counts on sampled pairs.
- vs `Correlograms.mat`: event counts exact; ≥99.9% bins exact; all residual diffs traced to lags on half-ms edges (`(round(lag*fs)+20)%40==0`), float edge construction vs MATLAB.
- Region caches under `reports/cache/<recording>/region{k}.npz` (gitignored).

## Stage 4 — metrics (in progress)

- Loess smoother: dumped linear kernel `data/loess_kernel_2001_w20.mat` (MATLAB `smoothdata(...,'loess',20)` impulse responses). `K @ probs` matches column-wise `smoothdata` to ~1e-18.
- Uniformity: χ² on **raw** probs; decisions exact vs `RecordingMetrics`; p relative error ≲ 3e-11 (underflow p≈0 excluded).
- `leaderProb`: exact to 1e-12 abs on finite entries.
- Empty pairs (`n_events==0` / all-NaN) with `sparseCorrelogramThresh==0`: **0 peaks** (not NaN).
- **Peak counts vs `RecordingMetrics.mat` ~93.7% (SMJM, all regions).** Root cause: MATLAB `smoothdata(matrix,'loess',20)` vs `smoothdata(column,'loess',20)` differ by ULPs (~1e-18). That flips `findpeaks` on equal-height / near-threshold peaks (~230/2500 pairs in Region1). `RecordingMetrics` matches the **matrix** path 100%. The plan’s linear kernel matches the **column** path; Python vs MATLAB column-wise `findpeaks` on Region1 is **99.56%** (11/2500 ULP residuals). Regenerating metrics with matrix `smoothdata` reproduces the mat; column-wise does not. Not a SciPy vs MATLAB prominence algorithm gap on identical input.

