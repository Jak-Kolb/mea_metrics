"""Build Plan C novel-metric tables from library parquets + InjuryIndices."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

from ..matref import load_reference
from ..screen.bars import _injury_region_split
from ..screen.__main__ import pick_primary_injury
from .normalize import add_rate_normalized_sttc
from .recovery import add_unit_topology_deltas, recovery_metrics


def build_novel_table(
    recording: str,
    *,
    library_parquet: Optional[Union[str, Path]] = None,
    band_k: float = 1.0,
) -> pd.DataFrame:
    path = Path(library_parquet) if library_parquet else Path("reports/library") / f"{recording}_metrics.parquet"
    df = pd.read_parquet(path)
    ref = load_reference(recording)
    if ref.injuries is None or ref.injuries.n < 1:
        raise RuntimeError(f"{recording}: no InjuryIndices")
    _, inj_start, inj_end, inj_label = pick_primary_injury(ref.injuries)
    baseline, during, post = _injury_region_split(df, inj_start, inj_end)

    out = add_rate_normalized_sttc(df)
    out = add_unit_topology_deltas(out, baseline_regions=baseline, post_regions=post)
    rec = recovery_metrics(
        out,
        baseline_regions=baseline,
        post_regions=post,
        injury_end_s=inj_end,
        band_k=band_k,
    )
    for k, v in rec.items():
        out[k] = v
    out["injury_label"] = inj_label
    out["injury_start_s"] = inj_start
    out["injury_end_s"] = inj_end
    out["n_baseline_regions"] = int(baseline.size)
    out["n_post_regions"] = int(post.size)
    return out


def write_novel_outputs(
    df: pd.DataFrame,
    recording: str,
    out_dir: Union[str, Path] = "reports/library",
) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pq = out / f"{recording}_novel.parquet"
    csv = out / f"{recording}_novel_preview.csv"
    df.to_parquet(pq, index=False)
    df.head(40).to_csv(csv, index=False)
    return pq, csv
