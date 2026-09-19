# Questions / unsettled items

Template: add items here instead of guessing. Resolve or carry into later stages.

## Open

1. **badSignals nonzero encoding across recordings**  
   Settled for SMJM (length-`CellCount` logical/0-1 mask, all false). Confirm on any recording that flags units: nonzero entries are mask positions aligned to `CellIDs`, not a list of indices (`removeBadSignals.m`). **Does not block Stage 1** — all four paper recordings are all-zero masks.

## Resolved

### badRegions table shape (2026-09-19) — settled for Stage 1

**Sources:** `original_mea_matlab/Analysis Execution/removeJunkRecordings.m`; `badRegions.mat` for all four recordings under `data/matlab_reference/`.

**MATLAB write/load contract** (`removeJunkRecordings.m`)
- Struct field `badRegionsIndicator` ∈ {0, 1}.
- **Only if indicator == 1:** creates `badStartTime` / `badEndTime` (user enters **minutes**, then `.*60` → **seconds**).
- Spike drop uses inclusive bounds: `start <= t <= end`.
- **If indicator == 0:** start/end fields are **never created**. Saved `.mat` contains only `badRegionsIndicator`.

**All four reference mats today**
| Recording | `badRegionsIndicator` | other fields |
| --- | --- | --- |
| SMJM_Bicuculline | 0 | none |
| SM_pHshock | 0 | none |
| ER52_ImpactWithBicuculline | 0 | none |
| JMSM_ImpactWithoutBicuculline | 0 | none |

**Python `Reference` API**
```python
ref.bad_regions_indicator: int   # 0 | 1  (== MATLAB badRegionsIndicator)
ref.bad_regions: list[tuple[float, float]]  # (start_s, end_s), inclusive seconds
# Always a list. Empty when indicator==0 (MATLAB omitted the time fields).
# Not None — empty list is the “no cuts” value so Stage 1 can always iterate.
```

Rejected: `None` when indicator==0 — empty list matches “no intervals” more cleanly for consumers.

### Other Step 0 resolutions
- Data paths: `data/matlab_reference` + `data/raw` (see `PORT_NOTES.md`).
- Correlogram/metrics region keys: 0-based (`Region1=0`).
- `InjuryIndicies` spelling kept as in MATLAB.

## Open — Stage 4 peak acceptance (2026-09-19)

**Question for New Bot / Jak:** Stage 4 plan bar is ≥99% peak counts vs `RecordingMetrics.mat`. That file matches MATLAB **matrix** `smoothdata`+`findpeaks`. Our dumped loess kernel (plan Step 4) matches **column** `smoothdata` and reaches ~93.7% vs the mat, but **≥99.5%** vs column-wise MATLAB on the same `Correlograms.mat`. Uniformity + leader already exact.

Accept which gate?
1. **Column-wise** (kernel path as planned) ≥99% vs live MATLAB column `smoothdata`+`findpeaks` — treat RecordingMetrics peak mismatch as known ULP quirk; note in PORT_NOTES.
2. Require bit-match to **matrix** path / RecordingMetrics peaks (would need non-linear / non-kernel approach or shipping MATLAB-smoothed arrays).
3. Other.

Until answered, `verify.py --stage metrics` fails on the RecordingMetrics peak bar while reporting unif/leader green.

## Open — Stage 4 RecordingMetrics peaks not regenerable (2026-09-19)

**Gate was Option 2:** ≥99% peak counts vs `RecordingMetrics.mat`.

**Finding:** Live MATLAB R2024b on jakpc, exact `calculateCorrelogramMetrics` path
(`smoothdata(rcor,'loess',20)` matrix → `max(0,·)` → renorm → `findpeaks(...,'MinPeakProminence',1/2001)`)
reproduces `RecordingMetrics` peak counts **100%** for Regions 1–7 and 14, but only
**~89–98%** for Regions 8–13. Overall **34356/35000 = 98.16%** — ceiling below the 99% bar.
Sweeping loess window ∈ {8…24} and prominence factor ∈ {0.25…2}×1/n does not beat loess/20/1.0
on Region 8 (best still 2230/2500).

`Correlograms.mat` and `RecordingMetrics.mat` share the same mtime (2026-09-18 18:28) but
Regions 8–13 peak fields are **not** a regeneration of the former with the current source.

Uniformity + leaderProb already exact vs `RecordingMetrics` in Python.

**Need gate revision:**
1. Re-gold: regenerate `RecordingMetrics` peaks from current Correlograms on jakpc; Python matches that (≥99% / exact).
2. Score peaks only on Regions 1–7+14 (where live MATLAB ≡ RecordingMetrics); document R8–13 as reference drift.
3. Lower bar to ≥98% with PORT_NOTES on R8–13 non-regenerability.
4. Other.

Holding Stage 5.
