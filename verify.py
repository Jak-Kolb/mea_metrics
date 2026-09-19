#!/usr/bin/env python3
"""Stage-by-stage verification harness against MATLAB reference .mat files.

Usage:
  python verify.py <recording> --stage {ref,rasters,regions,correlograms,metrics,summary,all}
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


STAGES = ("ref", "rasters", "regions", "correlograms", "metrics", "summary", "all")


def stage_ref(recording: str) -> int:
    from mea_metrics.matref import inventory_text, load_reference

    ref = load_reference(recording)
    print(inventory_text(ref))
    if not ref.files_present:
        print("ERROR: no reference files found", file=sys.stderr)
        return 1
    return 0


def stage_rasters(recording: str) -> int:
    """Compare plx→rasters pipeline to ProcessedData (exact equality)."""
    import numpy as np

    from mea_metrics.config import raw_plx_path
    from mea_metrics.matref import load_reference
    from mea_metrics.plx import load_plx
    from mea_metrics.rasters import build_rasters

    ref = load_reference(recording)
    plx_path = raw_plx_path(recording)
    if not plx_path.is_file():
        print(f"ERROR: missing plx {plx_path}", file=sys.stderr)
        return 1

    plx = load_plx(plx_path)
    got = build_rasters(
        plx,
        bad_signals=ref.bad_signals,
        bad_regions=ref.bad_regions,
        bad_regions_indicator=ref.bad_regions_indicator,
        n_total_electrodes=ref.n_total_electrodes,
    )

    ref_ids = list(ref.cell_ids)
    ref_rasters = list(ref.rasters)

    n_items = 0
    n_equal = 0
    worst_abs = 0.0
    failures: list[str] = []

    # names + count
    n_items += 1
    if got.cell_ids == ref_ids:
        n_equal += 1
        print(f"cell_ids: EXACT match ({len(ref_ids)} units)")
    else:
        failures.append(
            f"cell_ids mismatch: got {got.cell_ids[:5]}... ({len(got.cell_ids)}) "
            f"vs ref {ref_ids[:5]}... ({len(ref_ids)})"
        )
        print(failures[-1])

    n_items += 1
    if len(got.rasters) == len(ref_rasters):
        n_equal += 1
        print(f"unit_count: EXACT match ({len(ref_rasters)})")
    else:
        failures.append(
            f"unit_count mismatch: got {len(got.rasters)} vs ref {len(ref_rasters)}"
        )
        print(failures[-1])

    # per-unit spike times
    n_compare = min(len(got.rasters), len(ref_rasters))
    time_equal = 0
    for i in range(n_compare):
        n_items += 1
        a = np.asarray(got.rasters[i], dtype=np.float64)
        b = np.asarray(ref_rasters[i], dtype=np.float64)
        if a.shape == b.shape and np.array_equal(a, b):
            n_equal += 1
            time_equal += 1
        else:
            if a.shape == b.shape and a.size:
                d = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))
                worst_abs = max(worst_abs, d)
            name = ref_ids[i] if i < len(ref_ids) else f"idx{i}"
            failures.append(
                f"spikes[{name}]: shape {a.shape} vs {b.shape}"
                + (f" max_abs={worst_abs}" if a.shape == b.shape else "")
            )
            if len(failures) <= 8:
                print(failures[-1])

    print(f"spike_times: {time_equal}/{n_compare} units exactly equal")

    # fs / end time (informational + soft check)
    if ref.fs is not None:
        n_items += 1
        if float(got.fs) == float(ref.fs):
            n_equal += 1
            print(f"fs: EXACT match ({got.fs})")
        else:
            failures.append(f"fs mismatch: got {got.fs} vs ref {ref.fs}")
            print(failures[-1])

    if ref.end_time_s is not None:
        n_items += 1
        if float(got.end_time_s) == float(ref.end_time_s):
            n_equal += 1
            print(f"end_time_s: EXACT match ({got.end_time_s})")
        else:
            # still report; may differ if badRegions shifted (not for SMJM)
            d = abs(float(got.end_time_s) - float(ref.end_time_s))
            worst_abs = max(worst_abs, d)
            failures.append(
                f"end_time_s mismatch: got {got.end_time_s} vs ref {ref.end_time_s} (abs={d})"
            )
            print(failures[-1])

    pct = 100.0 * n_equal / n_items if n_items else 0.0
    print(
        f"\nrasters summary: {n_equal}/{n_items} exact ({pct:.4f}%), "
        f"worst_abs_diff={worst_abs}"
    )
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures[:20]:
            print(f"  - {f}")
        return 1
    print("rasters: PASS (exact match to ProcessedData)")
    return 0



def stage_regions(recording: str) -> int:
    """Compare auto_regions output to AnalysisRegions.mat (exact)."""
    import numpy as np

    from mea_metrics.matref import load_reference
    from mea_metrics.regions import auto_regions
    from mea_metrics.stats import compute_region_stats

    ref = load_reference(recording)
    if ref.regions_min is None or ref.regions_sec is None:
        print("ERROR: AnalysisRegions missing from reference", file=sys.stderr)
        return 1
    if ref.end_time_s is None:
        print("ERROR: end_time_s missing from reference", file=sys.stderr)
        return 1

    L = 7
    if ref.plot_props is not None and getattr(ref.plot_props, "automated_region_bin_length", None):
        L = int(ref.plot_props.automated_region_bin_length)

    tab = auto_regions(ref.end_time_s, ref.rasters, region_len_min=L)

    failures = []
    n_items = 0
    n_equal = 0

    n_items += 1
    if tab.num_regions == ref.num_regions:
        n_equal += 1
        print(f"num_regions: EXACT match ({ref.num_regions})")
    else:
        failures.append(f"num_regions {tab.num_regions} vs {ref.num_regions}")
        print(failures[-1])

    n_items += 1
    if np.array_equal(tab.minutes, np.asarray(ref.regions_min, dtype=np.float64)):
        n_equal += 1
        print(f"regions_min: EXACT match shape={tab.minutes.shape}")
    else:
        d = np.max(np.abs(tab.minutes - ref.regions_min)) if tab.minutes.shape == ref.regions_min.shape else float("nan")
        failures.append(f"regions_min mismatch max_abs={d}")
        print(failures[-1])
        print("  got:\n", tab.minutes)
        print("  ref:\n", ref.regions_min)

    n_items += 1
    if np.array_equal(tab.seconds, np.asarray(ref.regions_sec, dtype=np.float64)):
        n_equal += 1
        print(f"regions_sec: EXACT match shape={tab.seconds.shape}")
    else:
        d = np.max(np.abs(tab.seconds - ref.regions_sec)) if tab.seconds.shape == ref.regions_sec.shape else float("nan")
        failures.append(f"regions_sec mismatch max_abs={d}")
        print(failures[-1])

    # Smoke-run stats (no MATLAB numeric dump to compare yet)
    stats = compute_region_stats(ref.rasters, tab)
    print(f"stats: computed for {len(stats.spike_rate)} regions (smoke OK)")

    pct = 100.0 * n_equal / n_items if n_items else 0.0
    print(f"\nregions summary: {n_equal}/{n_items} exact ({pct:.4f}%)")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("regions: PASS (exact match to AnalysisRegions)")
    return 0



def stage_correlograms(recording: str) -> int:
    """Compare computed correlograms to Correlograms.mat (≥99.9% bins; edge ties)."""
    import numpy as np
    from pathlib import Path as P

    from mea_metrics.matref import load_reference
    from mea_metrics.correlogram import (
        bin_centers_and_edges,
        compute_all_regions,
        pair_lags_searchsorted,
        pair_lags_bruteforce,
        prepare_region_rasters,
        _apply_region_bound_quirk,
    )

    ref = load_reference(recording)
    bin_max = float(ref.plot_props.correlogram_bin_max)
    n_bins = int(ref.plot_props.number_of_correlogram_bins)
    centers, edges = bin_centers_and_edges(bin_max, n_bins)
    if not np.allclose(centers, ref.correlogram_bins):
        print("ERROR: bin centers differ from reference CorrelogramBins")
        return 1

    # (a) searchsorted vs brute-force bit-identical counts on region 0, pair (0,1)
    bounds = _apply_region_bound_quirk(ref.regions_sec)
    rr0 = prepare_region_rasters(ref.rasters, float(bounds[0, 0]), float(bounds[0, 1]))
    lags_s = pair_lags_searchsorted(rr0[0], rr0[1], bin_max)
    lags_b = pair_lags_bruteforce(rr0[0], rr0[1], bin_max)
    cs, _ = np.histogram(lags_s, edges)
    cb, _ = np.histogram(lags_b, edges)
    if not np.array_equal(cs, cb):
        print("ERROR: searchsorted vs brute-force histogram counts differ on region0 pair(0,1)")
        return 1
    print("searchsorted vs brute-force: bit-identical counts on region0 pair (0,1)")

    cache_dir = P("reports/cache") / recording
    got = compute_all_regions(
        ref.cell_ids,
        ref.rasters,
        ref.regions_sec,
        bin_max=bin_max,
        n_bins=n_bins,
        cache_dir=cache_dir,
    )

    fs = float(ref.fs) if ref.fs else 40000.0
    total_bins = 0
    match_bins = 0
    total_pairs = 0
    event_pairs_exact = 0
    name_ok = True
    edge_cols_ok = 0
    edge_cols = 0

    for ri in sorted(got):
        g = got[ri]
        rp, rn, rnames = ref.correlograms[ri]
        rp = rp.astype(np.float64)
        rn = rn.astype(np.float64)
        total_pairs += g.n_events.size
        event_pairs_exact += int(np.sum(g.n_events == rn))
        if list(g.names) != list(rnames):
            name_ok = False
        eq = np.isclose(g.probs, rp, equal_nan=True)
        total_bins += eq.size
        match_bins += int(eq.sum())
        diff_cols = np.unique(np.where(~eq)[1])
        for col in diff_cols:
            edge_cols += 1
            i_ref = col // len(ref.cell_ids)
            j_cmp = col % len(ref.cell_ids)
            t0, t1 = float(bounds[ri, 0]), float(bounds[ri, 1])
            # use cached region rasters
            rras = prepare_region_rasters(ref.rasters, t0, t1)
            lags = pair_lags_searchsorted(rras[i_ref], rras[j_cmp], bin_max)
            our_c, _ = np.histogram(lags, edges)
            if rn[col] == 0 or np.isnan(rp[0, col]):
                continue
            ref_c = np.rint(rp[:, col] * rn[col]).astype(np.int64)
            mismatch = int(np.abs(our_c.astype(np.int64) - ref_c).sum())
            samples = np.round(lags * fs).astype(np.int64)
            n_edge = int(np.sum((samples + 20) % 40 == 0))
            if mismatch <= 2 * n_edge:
                edge_cols_ok += 1

    pct = 100.0 * match_bins / total_bins if total_bins else 0.0
    print(f"names match all regions: {name_ok}")
    print(f"n_events exact pairs: {event_pairs_exact}/{total_pairs}")
    print(f"bin match: {match_bins}/{total_bins} ({pct:.6f}%)")
    print(f"differing pair-columns explained by edge ties: {edge_cols_ok}/{edge_cols}")
    print(f"cache: {cache_dir}")

    if not name_ok:
        print("ERROR: ComparisonNames mismatch")
        return 1
    if event_pairs_exact != total_pairs:
        print("ERROR: n_events not exact for all pairs")
        return 1
    if pct < 99.9:
        print(f"ERROR: bin match {pct:.6f}% < 99.9%")
        return 1
    if edge_cols and edge_cols_ok != edge_cols:
        print("ERROR: some differing columns not explained by edge ties")
        return 1
    print("correlograms: PASS")
    return 0



def stage_metrics(recording: str) -> int:
    """Compare correlogram metrics to RecordingMetrics.mat.

    Uniformity decisions must be exact; p-values within 1e-9 relative (skipping
    underflow); leaderProb within 1e-12 abs. Peak counts are reported vs the
    saved mat; see PORT_NOTES.md — matrix vs column smoothdata ULPs prevent a
    fair ≥99% bar against RecordingMetrics when using the plan's linear kernel.
    """
    import numpy as np
    from pathlib import Path as P

    from mea_metrics.matref import load_reference
    from mea_metrics.metrics import compute_region_metrics, load_loess_kernel

    ref = load_reference(recording)
    kernel_path = P("data/loess_kernel_2001_w20.mat")
    if not kernel_path.is_file():
        print(f"ERROR: missing loess kernel {kernel_path}")
        return 1
    K = load_loess_kernel(kernel_path)
    centers = ref.correlogram_bins

    n_pairs = 0
    unif_ok = 0
    lead_ok = 0
    lead_n = 0
    peak_ok = 0
    loc_ok = 0
    loc_tot = 0
    p_rel_vals = []

    for ri in sorted(ref.correlograms):
        probs, nev, _ = ref.correlograms[ri]
        got = compute_region_metrics(probs, nev, centers, K)
        p_ref, u_ref, lead_ref, npeak_ref, plocs_ref = ref.metrics[ri]
        u_ref = np.asarray(u_ref, dtype=np.uint8).ravel()
        npeak_ref = np.asarray(npeak_ref, dtype=np.float64).ravel()
        lead_ref = np.asarray(lead_ref, dtype=np.float64).ravel()
        p_ref = np.asarray(p_ref, dtype=np.float64).ravel()

        n_pairs += got.n_peaks.size
        unif_ok += int(np.sum(got.is_uniform.astype(np.uint8) == u_ref))

        lm = np.isfinite(got.leader_prob) & np.isfinite(lead_ref)
        lead_n += int(lm.sum())
        lead_ok += int(np.sum(np.abs(got.leader_prob[lm] - lead_ref[lm]) <= 1e-12))

        peak_ok += int(np.sum(got.n_peaks == npeak_ref))

        mask = (
            np.isfinite(got.p_uniform)
            & np.isfinite(p_ref)
            & (np.abs(p_ref) > 1e-300)
        )
        if mask.any():
            p_rel_vals.append(
                np.abs(got.p_uniform[mask] - p_ref[mask]) / np.abs(p_ref[mask])
            )

        for j in range(got.n_peaks.size):
            if got.n_peaks[j] != npeak_ref[j]:
                continue
            loc_tot += 1
            ol = np.asarray(got.peak_locations[j], dtype=np.float64)
            rl = np.asarray(plocs_ref[j], dtype=np.float64)
            rl = rl[np.isfinite(rl)]
            if ol.size == rl.size and (
                ol.size == 0 or np.allclose(np.sort(ol), np.sort(rl), atol=1e-9)
            ):
                loc_ok += 1

    p_rel = float(np.max(np.concatenate(p_rel_vals))) if p_rel_vals else 0.0
    peak_pct = 100.0 * peak_ok / n_pairs if n_pairs else 0.0
    print(f"uniformity decisions: {unif_ok}/{n_pairs}")
    print(f"uniformity p worst rel (p>|1e-300|): {p_rel:.3e}")
    print(f"leaderProb abs<=1e-12: {lead_ok}/{lead_n}")
    print(f"peak counts vs RecordingMetrics: {peak_ok}/{n_pairs} ({peak_pct:.4f}%)")
    print(f"peak locations where counts agree: {loc_ok}/{loc_tot}")

    ok = True
    if unif_ok != n_pairs:
        print("ERROR: uniformity decisions not exact")
        ok = False
    if p_rel > 1e-9:
        print(f"ERROR: uniformity p relative {p_rel:.3e} > 1e-9")
        ok = False
    if lead_ok != lead_n:
        print("ERROR: leaderProb not within 1e-12")
        ok = False
    if peak_pct < 99.0:
        print(
            f"ERROR: peak count match {peak_pct:.4f}% < 99% vs RecordingMetrics "
            "(known: matrix vs column smoothdata ULPs; see PORT_NOTES.md / QUESTIONS.md)"
        )
        ok = False
    if ok:
        print("metrics: PASS")
        return 0
    print("metrics: FAIL")
    return 1


def stage_stub(name: str) -> int:
    print(f"stage '{name}': not implemented yet")
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verify mea_metrics against MATLAB reference")
    p.add_argument("recording", help="Recording name, e.g. SMJM_Bicuculline")
    p.add_argument(
        "--stage",
        choices=STAGES,
        default="ref",
        help="Which stage to run (default: ref)",
    )
    args = p.parse_args(argv)

    if args.stage == "ref":
        return stage_ref(args.recording)
    if args.stage == "rasters":
        return stage_rasters(args.recording)
    if args.stage == "regions":
        return stage_regions(args.recording)
    if args.stage == "correlograms":
        return stage_correlograms(args.recording)
    if args.stage == "metrics":
        return stage_metrics(args.recording)
    if args.stage == "all":
        rc = stage_ref(args.recording)
        if rc != 0:
            return rc
        print("")
        rc = stage_rasters(args.recording)
        if rc != 0:
            return rc
        print("")
        rc = stage_regions(args.recording)
        if rc != 0:
            return rc
        print("")
        rc = stage_correlograms(args.recording)
        if rc != 0:
            return rc
        print("")
        rc = stage_metrics(args.recording)
        if rc != 0:
            return rc
        print("")
        r = stage_stub("summary")
        if r != 0:
            return r
        return 0
    return stage_stub(args.stage)


if __name__ == "__main__":
    sys.exit(main())
