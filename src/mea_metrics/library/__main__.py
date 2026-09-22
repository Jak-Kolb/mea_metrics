"""CLI: python -m mea_metrics.library A1 --recording SMJM_Bicuculline"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mea_metrics.library", description="Plan A metric library")
    sub = p.add_subparsers(dest="cmd", required=True)

    a1 = sub.add_parser("A1", help="Rate/ISI table on AnalysisRegions windows")
    a1.add_argument("--recording", default="SMJM_Bicuculline")
    a1.add_argument("--out-dir", default="reports/library")

    args = p.parse_args(argv)
    if args.cmd != "A1":
        return 2

    import numpy as np
    from mea_metrics.library.table import build_a1_table, write_a1_outputs

    df = build_a1_table(args.recording)
    pq, csv = write_a1_outputs(df, args.recording, args.out_dir)
    n_units = int(df["unit_id"].nunique())
    n_regions = int(df["region_index"].nunique())
    finite_rate = int(np.isfinite(df["rate_hz"].to_numpy()).sum())
    print(f"recording: {args.recording}")
    print(f"rows: {len(df)}  units: {n_units}  regions: {n_regions}")
    print(f"shape check: {n_units}×{n_regions} = {n_units * n_regions} (rows={len(df)})")
    print(f"finite rates: {finite_rate}/{len(df)}")
    print(
        "rate_hz min/median/max: "
        f"{df['rate_hz'].min():.6g} / {df['rate_hz'].median():.6g} / {df['rate_hz'].max():.6g}"
    )
    print(f"wrote {pq}")
    print(f"wrote {csv}")
    if len(df) != n_units * n_regions:
        print("ERROR: row count != units × regions", file=sys.stderr)
        return 1
    if finite_rate != len(df):
        print("ERROR: non-finite rate_hz", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
