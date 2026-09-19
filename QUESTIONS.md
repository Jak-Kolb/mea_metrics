# Questions / unsettled items

Template: add items here instead of guessing. Resolve or carry into later stages.

## Open

1. **badRegions when indicator=0**  
   For `SMJM_Bicuculline`, `badRegions.mat` contains only `badRegionsIndicator=0` — no start/end region table. Confirm with other recordings whether a region list appears only when indicator≠0, and what field names that table uses.

2. **InjuryIndicies spelling**  
   File and struct are named `InjuryIndicies` (MATLAB typo). Keep that spelling in loaders; do not “fix” on read.

3. **badSignals semantics**  
   SMJM has a length-50 uint8 vector of all zeros (one flag per unit?). Confirm whether nonzero entries are unit indices vs boolean mask aligned to `CellIDs`.

## Resolved (Step 0)

- Data paths: use `data/matlab_reference` and `data/raw`, not plan’s `Output Files` / `Raw Recordings` (see `PORT_NOTES.md`).
- Correlogram/metrics region keys: 0-based in Python (`Region1=0`).
