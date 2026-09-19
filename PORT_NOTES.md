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
