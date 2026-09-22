"""CLI: python -m mea_metrics.screen [--all | --recording NAME]"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

ALL_RECORDINGS = (
    "SMJM_Bicuculline",
    "ER52_ImpactWithBicuculline",
    "JMSM_ImpactWithoutBicuculline",
    "SM_pHshock",
)


def pick_primary_injury(injuries):
    """Choose the primary insult tile.

    Skip negative-time placeholders (seen on ER52). Prefer Impact / CO2 / pH /
    Shutoff labels when present; else first non-negative injury.
    """
    cands = []
    for i in range(injuries.n):
        s = float(injuries.start_sec[i])
        e = float(injuries.end_sec[i])
        label = str(injuries.labels[i])
        if s < 0:
            continue
        cands.append((i, s, e, label))
    if not cands:
        i = 0
        return i, float(injuries.start_sec[0]), float(injuries.end_sec[0]), str(injuries.labels[0])
    prefer = ("impact", "co_2", "co2", "shutoff", "ph", "phshock", "pH".lower())
    for key in prefer:
        for i, s, e, label in cands:
            if key in label.lower().replace(" ", ""):
                return i, s, e, label
    i, s, e, label = cands[0]
    return i, s, e, label



def _run_one(recording: str, table: Path | None, out: Path) -> tuple[int, Counter, list]:
    import pandas as pd
    from mea_metrics.matref import load_reference
    from mea_metrics.screen.bars import screen_recording
    from mea_metrics.screen.report import render_screen_report, write_screen_report

    table_path = table if table is not None else Path("reports/library") / f"{recording}_metrics.parquet"
    if not table_path.is_file():
        print(f"ERROR: missing table {table_path}", file=sys.stderr)
        return 1, Counter(), []

    df = pd.read_parquet(table_path)
    novel_path = Path("reports/library") / f"{recording}_novel.parquet"
    if novel_path.is_file():
        novel = pd.read_parquet(novel_path)
        # align on unit_id × region_index; bring C columns only
        ccols = [c for c in novel.columns if c not in df.columns]
        keys = [k for k in ("unit_id", "region_index") if k in df.columns and k in novel.columns]
        if keys and ccols:
            df = df.merge(novel[keys + ccols], on=keys, how="left")
            print(f"merged novel columns: {ccols[:8]}{'...' if len(ccols)>8 else ''}")
    ref = load_reference(recording)
    if ref.injuries is None or ref.injuries.n < 1:
        print(f"ERROR: {recording}: no InjuryIndices", file=sys.stderr)
        return 1, Counter(), []

    inj_i, inj_start, inj_end, inj_label = pick_primary_injury(ref.injuries)
    extra = ""
    if ref.injuries.n > 1:
        extra = f" (InjuryIndices n={ref.injuries.n}; using #{inj_i} '{inj_label}')"

    results, baseline, during, post = screen_recording(
        df, injury_start_s=inj_start, injury_end_s=inj_end
    )
    text = render_screen_report(
        results,
        recording=recording,
        injury_label=inj_label + extra,
        injury_start_s=inj_start,
        injury_end_s=inj_end,
        baseline_regions=baseline.tolist(),
        during_regions=during.tolist(),
        post_regions=post.tolist(),
    )
    write_screen_report(text, out)
    c = Counter(r.status for r in results)
    fails = [r for r in results if r.status == "FAIL"]
    print(f"=== {recording} ===")
    print(f"wrote {out}")
    print(f"injury: {inj_label} [{inj_start:.0f}, {inj_end:.0f}] s{extra}")
    print(f"regions baseline={list(baseline)} during={list(during)} post={list(post)}")
    print(f"bars: PASS={c['PASS']} FAIL={c['FAIL']} SKIP={c['SKIP']}")
    for r in fails:
        print(f"  FAIL {r.metric}/{r.bar}: {r.note}")
    return 0, c, results


def _write_combined(summaries: list[dict], path: Path) -> None:
    lines = [
        "# Screening report — all Adam recordings (B2)",
        "",
        "Same frozen thresholds as B1 (`LIBRARY_NOTES.md`). "
        "Treatment bar: *no culture holdout*; n=1 culture per recording.",
        "",
        "## Per-recording summary",
        "",
        "| recording | PASS | FAIL | SKIP | report |",
        "|---|---:|---:|---:|---|",
    ]
    for s in summaries:
        lines.append(
            f"| `{s['recording']}` | {s['PASS']} | {s['FAIL']} | {s['SKIP']} | "
            f"`{s['report']}` |"
        )
    lines.append("")
    lines.append("## Failure roll-up")
    lines.append("")
    any_fail = False
    for s in summaries:
        fails = s.get("fails") or []
        if not fails:
            continue
        any_fail = True
        lines.append(f"### `{s['recording']}`")
        lines.append("")
        for f in fails:
            lines.append(f"- **{f['metric']} / {f['bar']}**: {f['note']}")
        lines.append("")
    if not any_fail:
        lines.append("_No FAIL bars across recordings._")
        lines.append("")
    lines.extend(_recovery_snapshot_lines())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    print(f"wrote combined {path}")


def _fmt_num(x) -> str:
    import math
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "nan"
    if not math.isfinite(v):
        return "nan"
    if abs(v) >= 1000 or (abs(v) > 0 and abs(v) < 1e-2):
        return f"{v:.4g}"
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.4g}"


def _recovery_snapshot_lines() -> list[str]:
    """Plan C culture-level recovery rows from novel parquets (if present)."""
    import pandas as pd

    lines = [
        "## Plan C recovery snapshot (culture-level)",
        "",
        "| recording | injury | tau_rec_burst_s | tau_rec_rate_s | burst_ratio post0/mid/last |",
        "|---|---|---:|---:|---|",
    ]
    any_row = False
    for rec in ALL_RECORDINGS:
        novel_path = Path("reports/library") / f"{rec}_novel.parquet"
        if not novel_path.is_file():
            continue
        row = pd.read_parquet(novel_path).iloc[0]
        any_row = True
        ratios = "/".join(
            _fmt_num(row[c])
            for c in (
                "burst_rate_ratio_post0",
                "burst_rate_ratio_post_mid",
                "burst_rate_ratio_post_last",
            )
        )
        lines.append(
            f"| `{rec}` | {row.get('injury_label', '?')} | "
            f"{_fmt_num(row.get('tau_rec_burst_s'))} | "
            f"{_fmt_num(row.get('tau_rec_rate_s'))} | {ratios} |"
        )
    if not any_row:
        return []
    lines.append("")
    lines.append(
        "`tau_rec_*` = time (s) from injury end to first post region inside "
        "baseline mean±1 SD; nan = never returned on the region grid."
    )
    lines.append("")
    return lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mea_metrics.screen", description="Plan B four-bar screen")
    p.add_argument("--recording", default="SMJM_Bicuculline")
    p.add_argument("--all", action="store_true", help="All four Adam recordings")
    p.add_argument("--table", default=None)
    p.add_argument("--out", default=None, help="Output md path (single-recording mode)")
    p.add_argument(
        "--combined-out",
        default="reports/screen/SCREEN_REPORT.md",
        help="Combined summary when --all",
    )
    args = p.parse_args(argv)

    recs = list(ALL_RECORDINGS) if args.all else [args.recording]
    summaries = []
    rc = 0
    for rec in recs:
        if args.all or args.out is None:
            out = Path("reports/screen") / f"SCREEN_REPORT_{rec}.md"
        else:
            out = Path(args.out)
        code, counts, results = _run_one(rec, Path(args.table) if args.table else None, out)
        rc = rc or code
        summaries.append(
            {
                "recording": rec,
                "PASS": counts["PASS"],
                "FAIL": counts["FAIL"],
                "SKIP": counts["SKIP"],
                "report": str(out),
                "fails": [{"metric": r.metric, "bar": r.bar, "note": r.note} for r in results if r.status == "FAIL"],
            }
        )

    if args.all:
        _write_combined(summaries, Path(args.combined_out))
        # Keep SMJM alias path for B1 compatibility
        smjm = Path("reports/screen/SCREEN_REPORT_SMJM_Bicuculline.md")
        alias = Path("reports/screen/SCREEN_REPORT.md")
        # combined already at SCREEN_REPORT.md; also copy SMJM detail stays separate
        if smjm.is_file() and not args.combined_out.endswith("SCREEN_REPORT.md"):
            pass
    elif len(recs) == 1 and args.out is None:
        # single default: also write SCREEN_REPORT.md as the SMJM-style alias when SMJM
        pass

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
