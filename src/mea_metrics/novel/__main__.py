"""CLI: python -m mea_metrics.novel --all"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

ALL = (
    "SMJM_Bicuculline",
    "ER52_ImpactWithBicuculline",
    "JMSM_ImpactWithoutBicuculline",
    "SM_pHshock",
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mea_metrics.novel")
    p.add_argument("--recording", default="SMJM_Bicuculline")
    p.add_argument("--all", action="store_true")
    p.add_argument("--out-dir", default="reports/library")
    args = p.parse_args(argv)

    from mea_metrics.novel.table import build_novel_table, write_novel_outputs

    recs = list(ALL) if args.all else [args.recording]
    for rec in recs:
        print(f"=== novel {rec} ===", flush=True)
        df = build_novel_table(rec)
        pq, csv = write_novel_outputs(df, rec, args.out_dir)
        # culture-level recovery snapshot (same on every row)
        row = df.iloc[0]
        print(
            f"injury={row['injury_label']}  tau_rec_burst_s={row['tau_rec_burst_s']:.4g}  "
            f"tau_rec_rate_s={row['tau_rec_rate_s']:.4g}",
            flush=True,
        )
        print(
            f"burst_rate ratios post0/mid/last="
            f"{row['burst_rate_ratio_post0']:.4g}/"
            f"{row['burst_rate_ratio_post_mid']:.4g}/"
            f"{row['burst_rate_ratio_post_last']:.4g}",
            flush=True,
        )
        print(f"wrote {pq}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
