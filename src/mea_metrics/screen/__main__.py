"""CLI: python -m mea_metrics.screen --recording SMJM_Bicuculline"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mea_metrics.screen", description="Plan B four-bar screen")
    p.add_argument("--recording", default="SMJM_Bicuculline")
    p.add_argument("--table", default=None, help="Path to metrics parquet (default: reports/library/<rec>_metrics.parquet)")
    p.add_argument("--out", default="reports/screen/SCREEN_REPORT.md")
    args = p.parse_args(argv)

    import pandas as pd
    from mea_metrics.matref import load_reference
    from mea_metrics.screen.bars import screen_recording
    from mea_metrics.screen.report import render_screen_report, write_screen_report

    table_path = Path(args.table) if args.table else Path("reports/library") / f"{args.recording}_metrics.parquet"
    if not table_path.is_file():
        print(f"ERROR: missing table {table_path}", file=sys.stderr)
        return 1

    df = pd.read_parquet(table_path)
    ref = load_reference(args.recording)
    if ref.injuries is None or ref.injuries.n < 1:
        print("ERROR: no InjuryIndices on recording", file=sys.stderr)
        return 1
    inj_start = float(ref.injuries.start_sec[0])
    inj_end = float(ref.injuries.end_sec[0])
    inj_label = str(ref.injuries.labels[0])

    results, baseline, during, post = screen_recording(
        df, injury_start_s=inj_start, injury_end_s=inj_end
    )
    text = render_screen_report(
        results,
        recording=args.recording,
        injury_label=inj_label,
        injury_start_s=inj_start,
        injury_end_s=inj_end,
        baseline_regions=baseline.tolist(),
        during_regions=during.tolist(),
        post_regions=post.tolist(),
    )
    out = write_screen_report(text, args.out)
    # summary counts
    from collections import Counter
    c = Counter(r.status for r in results)
    print(f"wrote {out}")
    print(f"bars: PASS={c['PASS']} FAIL={c['FAIL']} SKIP={c['SKIP']}")
    fails = [r for r in results if r.status == "FAIL"]
    if fails:
        print("FAILUREs:")
        for r in fails:
            print(f"  - {r.metric} / {r.bar}: {r.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
