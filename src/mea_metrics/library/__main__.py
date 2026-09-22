"""CLI: python -m mea_metrics.library A2 --all"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _run_one(recording: str, out_dir: str) -> int:
    import numpy as np
    from mea_metrics.library.table import build_a2_table, write_a2_outputs

    t0 = time.time()
    print(f"=== {recording} ===", flush=True)
    df = build_a2_table(recording)
    pq, csv = write_a2_outputs(df, recording, out_dir)
    n_units = int(df["unit_id"].nunique())
    n_regions = int(df["region_index"].nunique())
    finite_rate = int(np.isfinite(df["rate_hz"].to_numpy()).sum())
    finite_sttc = int(np.isfinite(df["sttc_mean_window"].to_numpy()).sum())
    print(f"rows: {len(df)}  units: {n_units}  regions: {n_regions}", flush=True)
    print(f"shape check: {n_units}×{n_regions} = {n_units * n_regions}", flush=True)
    print(f"finite rates: {finite_rate}/{len(df)}", flush=True)
    print(f"finite sttc_mean_window rows: {finite_sttc}/{len(df)}", flush=True)
    print(
        "rate_hz min/median/max: "
        f"{df['rate_hz'].min():.6g} / {df['rate_hz'].median():.6g} / {df['rate_hz'].max():.6g}",
        flush=True,
    )
    # window-level STTC unique values
    wsttc = df.groupby("region_index")["sttc_mean_window"].first()
    print(
        "sttc_mean_window (per region) min/median/max: "
        f"{wsttc.min():.6g} / {wsttc.median():.6g} / {wsttc.max():.6g}",
        flush=True,
    )
    print(f"burst_count sum: {df['burst_count'].sum():.0f}", flush=True)
    print(f"elapsed_s: {time.time() - t0:.1f}", flush=True)
    print(f"wrote {pq}", flush=True)
    print(f"wrote {csv}", flush=True)
    if len(df) != n_units * n_regions:
        print("ERROR: row count != units × regions", file=sys.stderr)
        return 1
    if finite_rate != len(df):
        print("ERROR: non-finite rate_hz", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mea_metrics.library", description="Plan A metric library")
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, help_ in (("A1", "Rate/ISI only path (writes full A2 columns)"), ("A2", "Rate/ISI + bursts + STTC + health")):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--recording", default="SMJM_Bicuculline")
        sp.add_argument("--all", action="store_true", help="All four Adam recordings")
        sp.add_argument("--out-dir", default="reports/library")

    args = p.parse_args(argv)
    if args.cmd not in ("A1", "A2"):
        return 2

    from mea_metrics.library.table import ALL_ADAM_RECORDINGS

    recs = list(ALL_ADAM_RECORDINGS) if args.all else [args.recording]
    rc = 0
    for rec in recs:
        rc = _run_one(rec, args.out_dir) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
