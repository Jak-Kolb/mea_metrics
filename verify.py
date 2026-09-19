#!/usr/bin/env python3
"""Stage-by-stage verification harness against MATLAB reference .mat files.

Usage:
  python verify.py <recording> --stage {ref,rasters,regions,correlograms,metrics,summary,all}

Step 0: --stage ref prints the reference inventory and exits 0 on success.
Later stages are stubs that exit non-zero until implemented.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without install: PYTHONPATH=src or repo-relative
_REPO = Path(__file__).resolve().parent
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


STAGES = ("ref", "rasters", "regions", "correlograms", "metrics", "summary", "all")


def stage_ref(recording: str) -> int:
    from mea_metrics.matref import inventory_text, load_reference

    ref = load_reference(recording)
    text = inventory_text(ref)
    print(text)
    if ref.load_warnings:
        # still exit 0 if core inventory printed; warnings are informational
        pass
    if not ref.files_present:
        print("ERROR: no reference files found", file=sys.stderr)
        return 1
    return 0


def stage_stub(name: str) -> int:
    print(f"stage '{name}': not implemented yet (Step 0 harness only)")
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
    if args.stage == "all":
        rc = stage_ref(args.recording)
        if rc != 0:
            return rc
        for s in ("rasters", "regions", "correlograms", "metrics", "summary"):
            print("")
            r = stage_stub(s)
            if r != 0:
                return r
        return 0
    return stage_stub(args.stage)


if __name__ == "__main__":
    sys.exit(main())
