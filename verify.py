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
    if args.stage == "all":
        rc = stage_ref(args.recording)
        if rc != 0:
            return rc
        print("")
        rc = stage_rasters(args.recording)
        if rc != 0:
            return rc
        for s in ("regions", "correlograms", "metrics", "summary"):
            print("")
            r = stage_stub(s)
            if r != 0:
                return r
        return 0
    return stage_stub(args.stage)


if __name__ == "__main__":
    sys.exit(main())
