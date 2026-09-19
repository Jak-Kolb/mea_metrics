# Porting plan: `original_mea_matlab` → `mea_metrics`

Read this first, then the MATLAB source. Where this file and the MATLAB source disagree, the source wins and you note it in `PORT_NOTES.md`.

- MATLAB repo (read-only): `/Users/jakkolb/Desktop/Coding/GitHub/original_mea_matlab`
- Python repo (work here): `/Users/jakkolb/Desktop/Coding/GitHub/mea_metrics`
- Reference outputs already exist: `original_mea_matlab/Output Files/<recording>/*.mat` (nine files per recording, including the human answers: `badSignals.mat`, `badRegions.mat`, `AnalysisRegions.mat`, `InjuryIndicies.mat`)
- Raw recordings: `original_mea_matlab/Raw Recordings/<recording>.plx`
- MATLAB is installed (it produced those outputs). You need it once, in Step 4.

Goal: `mea_metrics` reproduces every number the MATLAB pipeline produces, proven stage by stage against those `.mat` files. Not a redesign. Not a prettier pipeline.

Supersedes `REPLICATION_TASK.md` where the two differ — that file covered the case where the MATLAB outputs don't exist yet.

## Five rules that make this fast

1. **Port numbers, not pictures.** Eight of the thirteen MATLAB files exist to draw figures. Skip them (table below).
2. **Don't port the prompts.** Every interactive question in the MATLAB code was already answered, and the answers are saved in the reference `.mat` files. Read them; do not rebuild the question flow.
3. **Harness before code.** Step 0 builds the comparison harness. After that, each stage is checked the minute it is written, so a mistake costs minutes instead of a day.
4. **One recording end to end first** (`SMJM_Bicuculline`), then the other three in one pass.
5. **Buy your way past the two hard spots.** The smoothing operator gets dumped out of MATLAB once as a matrix (Step 4). The correlogram bin-edge problem is solved by doing MATLAB's exact float arithmetic (Step 3). Don't reverse-engineer either one by hand.

Rules that still hold: replicate quirky behavior instead of fixing it (put fixes behind a flag defaulting to MATLAB behavior), never widen a tolerance to pass a test, and write anything you can't settle into `QUESTIONS.md` rather than guessing.

## What to port, what to skip

| MATLAB file | Port | Python home |
| --- | --- | --- |
| `Main_AnalyzeRecordingData.m` | parameters only | `config.py` |
| `Function to Read plx Files/*` | no — use `neo` | `plx.py` |
| `getRasters.m` | yes | `rasters.py` |
| `removeBadSignals.m` | answers only | `rasters.py` |
| `removeJunkRecordings.m` | yes | `rasters.py` |
| `calculateRasterMetrics.m` | numbers only (3 figures skipped) | `stats.py` |
| `getInjuryOrTreatmentIndicies.m` | region/injury math only | `regions.py` |
| `plotStatsInEachRegion.m` | numbers only | `stats.py` |
| `generateCorrelograms.m` | yes — the core | `correlogram.py` |
| `calculateCorrelogramMetrics.m` | yes — metric math, not the imagesc blocks | `metrics.py` |
| `summarizeCorrelograms.m` | classification math only (~15% of the file) | `summary.py` |
| `PlotPopulationMetricChanges.m` | no | — |
| `Violin.m`, `violinplot.m`, `hatchfill.m`, `PlotCorrelogramGeneration.m` | no | — |

Package layout in `mea_metrics`:

```
src/mea_metrics/{config,matref,plx,rasters,regions,stats,correlogram,metrics,summary,report}.py
tests/
verify.py                  # CLI harness
reports/                   # generated
PORT_NOTES.md QUESTIONS.md
```

Constants (from `Main_AnalyzeRecordingData.m`): `bin_max = 1.0` s, `n_bins = 2001` (1 ms bins), `smoothing_factor = 0.01`, `unif_p = 0.05`, `sparse_threshold = 0`, `include_autocorrelograms = False`, `region_len_min = 7`.

---

## Step 0 — harness first

Build `matref.py` and `verify.py` before any pipeline code.

- `matref.load_reference(recording) -> Reference`: reads the nine `.mat` files with `scipy.io.loadmat(..., struct_as_record=False, squeeze_me=True)`, falling back to `h5py` for v7.3 files (remember HDF5 hands you MATLAB arrays transposed). Expose plain numpy: `ref.cell_ids`, `ref.rasters`, `ref.regions_min`, `ref.regions_sec`, `ref.correlograms[region] -> (probs, n_events, names)`, `ref.metrics[region] -> (p_values, uniform, leader_prob, n_peaks, peak_locations)`, `ref.bad_signals`, `ref.bad_regions`, `ref.injuries`.
- `verify.py <recording> --stage {ref,rasters,regions,correlograms,metrics,summary,all}`: prints one row per stage — items compared, % exactly equal, worst absolute and relative difference — and exits non-zero on failure.

**Done when** `python verify.py SMJM_Bicuculline --stage ref` prints the reference inventory: number of units, unit names, number of regions, region bounds, pairs per region, and the saved human answers. Eyeball that against the paper before writing pipeline code.

## Step 1 — loader and rasters

`plx.load_plx(path)` via `neo.rawio.PlexonRawIO`: integer timestamps and unit ids per (electrode, unit), plus `ADFrequency` and `LastTimestamp`. Spike times in seconds are `timestamps.astype(np.float64) / fs` — divide once, never round.

`rasters.build_rasters(plx)` reproduces `getRasters.m`: per electrode, `unique(units)` ascending, named `s<electrode>a/b/c/d` in that order — the lowest unit value gets `a` even when it is unit 0 (unsorted). Then apply `badSignals` (drop those units) and `badRegions` from the reference: drop spikes with `start <= t <= end`; if a cut ends the recording, the end time becomes `max(cut_start - 0.001, max_remaining + 0.001)`; if a cut starts at 0, subtract `min(min_remaining - 0.001, cut_end)` from every spike time and from the end time; drop units left empty.

Check the electrode numbering: MATLAB names units from the `SIG` field, neo reports its own channel id. If names don't line up, fix the mapping here — every later stage inherits it.

**Done when** unit names, unit count and every unit's spike times equal `ProcessedData` exactly (integers divided identically, so require exact equality).

## Step 2 — regions and stats

Regions come from `AnalysisRegions.mat`. Also implement the auto rule in `regions.auto_regions`, because new recordings won't have a saved answer, and verify it reproduces the saved table:

```python
M = int(end_time_s // 60)
end_round = M if (M % L) else (L - (M % L)) + M      # when M divides evenly, MATLAB adds one more bin
edges  = L * np.arange(int(end_round // L) + 1)      # MATLAB 0:L:end_round
starts, ends = edges[:-1].astype(float), edges[1:].astype(float) - L / 1000
ends[-1] = min(ends[-1], end_time_s / 60)
if (ends[-1] - starts[-1]) / L < 0.8:
    starts, ends = starts[:-1], ends[:-1]
```

Then MATLAB deletes any region containing a minute with zero network firing: per-minute counts per unit (`minute_bins = 0..floor(end_time_s/60)`, label `k` covers [k-1, k) minutes), mean across units, region `[s, e]` owns labels `s <= k <= e`, delete the region if any of its labels has mean 0. A 98.5-minute recording with `L = 7` gives 14 regions, first `[0, 6.993]`, last `[91, 97.993]`, before this rule runs.

`stats.py` carries the cheap per-region numbers from `plotStatsInEachRegion.m`: spikes in region per unit divided by the region length **in seconds** (the variable is named per-minute but the divisor is seconds — replicate, note in `PORT_NOTES.md`), fraction of each unit's total spikes, and in-region ISIs.

**Done when** the region table matches `AnalysisRegions.mat` exactly, both minutes and seconds, from the auto rule alone.

## Step 3 — correlograms (the core)

```python
centers = np.linspace(-bin_max, bin_max, n_bins)
spacing = np.mean(np.gradient(centers))
edges   = np.sort(np.concatenate([centers - spacing/2, [centers[-1] + spacing/2]]))

# region bounds: inclusive on BOTH ends; any bound equal to 60 s becomes 0 (generateCorrelograms.m)
lo = np.searchsorted(t_cmp, t_ref - bin_max, side="left")
hi = np.searchsorted(t_cmp, t_ref + bin_max, side="right")
lags = np.concatenate([t_cmp[a:b] - t for a, b, t in zip(lo, hi, t_ref)]) if t_ref.size else np.empty(0)
lags = lags[(lags >= -bin_max) & (lags <= bin_max)]
counts, _ = np.histogram(lags, edges)
probs = counts / lags.size if lags.size else np.full(n_bins, np.nan)   # 0/0 -> NaN, as MATLAB gives
```

The lag must be `t_cmp - t_ref` in float64 from the divided timestamps, in that order. At 40 kHz about 2.5% of lags land exactly on a bin edge, and only identical arithmetic puts them on the same side; integer-sample binning moves roughly 1% of counts. All ordered pairs are built, including each unit against itself.

Performance: don't build the full lag matrix, stream region by region, cache to `reports/cache/<recording>/region<k>.npz` (float32 in the cache, float64 in every calculation), and parallelize across regions with `multiprocessing` once it is correct.

**Done when**: (a) the `searchsorted` path and a brute-force `t_cmp[:, None] - t_ref[None, :]` path give bit-identical counts on one region; (b) against `Correlograms.mat`, event counts match exactly and bin counts match in ≥ 99.9% of bins, with every differing bin traced to a lag on an edge — at 40 kHz that means `(lag_samples + 20) % 40 == 0`. Report the counts, don't hide them.

## Step 4 — the three metrics

Uniformity and area left of zero are direct:

```python
E = n_events / L                       # L = n_bins = 2001
O = probs * n_events
stat = np.sum((O - E) ** 2 / E)        # empty pair -> NaN
p = scipy.stats.chi2.sf(stat, L - 1)   # MATLAB chi2cdf(..., 'upper')
is_uniform = p > 0.05                  # NaN > 0.05 is False: empty pairs read "nonuniform"
area_left = probs[centers < 0].sum() + 0.5 * probs[centers == 0].sum()
```

Peak count needs `smoothdata(x, 'loess', 20)`. Don't re-derive it. `'loess'` is a weighted least-squares fit whose weights depend only on position, so the whole smoother is a **linear operator** — dump it out of MATLAB once:

```matlab
% dump_loess_kernel.m — run once in original_mea_matlab
L = 2001; w = 20; K = zeros(L, L);
for i = 1:L
    e = zeros(L,1); e(i) = 1;
    K(:,i) = smoothdata(e, 'loess', w);     % column i = response to an impulse at i
end
save('loess_kernel_2001_w20.mat', 'K', '-v7.3');
```

In Python, `sm = K @ probs` reproduces MATLAB's smoothing exactly, including the shifted windows at both ends, because smoothing a sum of impulses is the sum of their smoothed responses. Sanity-check `K` on load: rows sum to 1 (a smoother preserves constants), and every row is zero outside a ~20-wide band except near the edges. The matrix assumes NaN-free input — `smoothdata` drops NaNs by default, which changes the operator — so short-circuit the all-NaN (empty pair) case to 0 peaks, which is where MATLAB's own chain lands. Speed: the interior rows are all the same 20-tap kernel, so convolve with that kernel and apply the first and last ~10 rows densely; or just use a banded/sparse matmul. (This trick works because `'loess'` is linear. It would not work for `'rloess'`, which iterates on residuals.)

Then:

```python
sm = K @ probs
sm = np.fmax(0.0, sm)                  # MATLAB max(0, NaN) == 0; np.maximum would keep the NaN
sm = sm / sm.sum()                     # all-zero input -> NaN vector
peaks, _ = scipy.signal.find_peaks(sm, prominence=1.0 / L)
n_peaks = peaks.size if np.isfinite(sm).all() else 0
```

**Done when**, against `RecordingMetrics.mat`: uniformity decisions identical, p-values within 1e-9 relative, `leaderProb` within 1e-12 absolute, peak counts identical for ≥ 99% of correlograms with the exceptions listed, and peak locations identical where counts agree. If peak counts miss the bar, the culprit is almost always `find_peaks` on a plateau (MATLAB returns a flat peak's first index, SciPy the middle one) — check that before touching the kernel.

## Step 5 — summaries

From `summarizeCorrelograms.m`, port the classification math only, over cross-correlograms (drop the diagonal when `include_autocorrelograms` is false):

- Leader/follower: `strength = abs(leader_prob - 0.5) / 0.5`, five classes at 0, 0.2, 0.4, 0.6, 0.8, 1.0 — Weak, Fairly Weak, Intermediate, Fairly Strong, Strong; first class includes its lower edge, last its upper edge.
- Peak counts: one class per count from the lowest observed up to `min(10, highest observed)`; the top class reads "or more" only when the observed maximum exceeds 10.
- Uniformity: Nonuniform (False) / Uniform (True).
- Denominators as MATLAB has them: leader/follower and peak counts exclude NaN entries; uniformity does not (the array is logical), so empty correlograms count as Nonuniform and stay in the denominator. Emit an `excluding_empty` variant as extra columns so the difference is visible.

Skip the zone/transition histograms (the "previously classified as …" figures) unless you later need that figure; if you do port them, they are probabilities of the current class given the previous zone's class.

**Done when** per-region class fractions match values recomputed from the reference arrays to 1e-12.

## Step 6 — the other three recordings, then package it

Run `SM_pHshock`, `ER52_ImpactWithBicuculline`, `JMSM_ImpactWithoutBicuculline` through `verify.py`. Then:

- `report.py` writes `reports/verification_<recording>.{md,json}`: recording facts (duration, sampling rate, active electrodes, units per electrode, whether unit 0 is present, regions, regions dropped by the silent-minute rule, empty correlograms per region), one row per stage with match rates and worst differences, and every mismatch category with a cause or the word "unexplained".
- CLI: `mea-metrics run <recording>` and `mea-metrics verify <recording>`.
- `README.md`: install, run one recording, run the tests, regenerate the reports.
- `PORT_NOTES.md`: each MATLAB quirk deliberately reproduced, with file and line.

## Acceptance table

| Check | Bar |
| --- | --- |
| Unit names, spike times, raster stats | Exact |
| Region tables (from the auto rule) | Exact |
| Correlogram event counts | Exact |
| Correlogram bin counts | ≥ 99.9% exact, every mismatch traced to a bin-edge tie |
| Uniformity decisions | Identical |
| Area left of zero | Within 1e-12 |
| Peak counts | Identical for ≥ 99% of correlograms, exceptions listed |
| Class fractions per region | Within 0.5 percentage points |

## Mismatch triage

Work in this order; each check is a one-liner and rules out a whole class of causes.

1. **Unit names shifted by a letter** → unit 0 is in the file and the electrode mapping or naming is off. Compare per-name spike counts against the reference.
2. **A whole region missing or extra** → the silent-minute rule, or the `[s, e]` inclusive bounds.
3. **Bin counts off by a few** → bin-edge ties. Count lags with `(lag_samples + 20) % 40 == 0` and check the differing bins are a subset.
4. **Uniformity p-values off but decisions right** → `n_events` mismatch, not the test; compare `n_events` first.
5. **Peak counts off** → plateau handling in `find_peaks`, then the kernel, in that order.
6. **Fractions off while metrics match** → the denominator rule for empty correlograms.

## Quirks to reproduce, not fix

Unit 0 becomes signal `a`; empty correlograms give NaN probabilities, `False` uniformity and 0 peaks; `followerProb` drops the last bin; region bounds equal to 60 s become 0; region bounds are inclusive on both ends; `CellDisplayNames` is not filtered with `CellIDs`; a fifth unit on one electrode reuses the fourth name; `maxPkCount` is saved one region stale; per-region spike counts are divided by seconds despite the per-minute name.

## Kickoff prompt

> Read `PORTING_PLAN.md` in `mea_metrics`. The MATLAB source at `/Users/jakkolb/Desktop/Coding/GitHub/original_mea_matlab` is the specification — read the file listed for a step before writing that step. Do the steps in order, commit after each, keep the test suite green, and run `verify.py` after every step. Copy MATLAB's odd behavior rather than fixing it, and log each one in `PORT_NOTES.md`. Never loosen a tolerance or skip a comparison to make a check pass — unexplained mismatches go in the verification report. Anything you can't settle from the MATLAB source goes in `QUESTIONS.md`. Start with Step 0 and stop after printing the reference inventory for `SMJM_Bicuculline` so I can check it.
