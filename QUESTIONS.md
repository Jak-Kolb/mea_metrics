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
