"""Assemble and write Plan A metric tables."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from ..config import raw_plx_path
from ..matref import load_reference
from ..plx import load_plx
from ..rasters import RasterSet, build_rasters
from .rate import rate_isi_row
from .windows import Window, windows_from_regions


def _load_rasters(recording: str) -> RasterSet:
    """Load plx rasters with the same badSignals / badRegions cuts as Stage 1."""
    ref = load_reference(recording)
    plx = load_plx(raw_plx_path(recording))
    return build_rasters(
        plx,
        bad_signals=ref.bad_signals,
        bad_regions=ref.bad_regions,
        bad_regions_indicator=int(ref.bad_regions_indicator or 0),
        n_total_electrodes=ref.n_total_electrodes,
    )


def build_a1_table(
    recording: str,
    *,
    rasters: Optional[RasterSet] = None,
    regions_sec: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Per unit × region: rate_hz, isi_mean/median, cv_isi (+ n_spikes)."""
    ref = load_reference(recording)
    rs = rasters if rasters is not None else _load_rasters(recording)
    regs = regions_sec if regions_sec is not None else ref.regions_sec
    if regs is None:
        raise RuntimeError(f"{recording}: no AnalysisRegions (regions_sec)")
    windows: List[Window] = windows_from_regions(regs)

    rows = []
    for w in windows:
        for unit_i, (uid, spikes) in enumerate(zip(rs.cell_ids, rs.rasters)):
            m = rate_isi_row(spikes, w.start_s, w.end_s)
            rows.append(
                {
                    "recording": recording,
                    "unit_id": uid,
                    "unit_index": unit_i,
                    "region_index": w.index,
                    "window_start_s": w.start_s,
                    "window_end_s": w.end_s,
                    "window_dur_s": w.duration_s,
                    "window_source": w.source,
                    **m,
                }
            )
    df = pd.DataFrame(rows)
    col_order = [
        "recording",
        "unit_id",
        "unit_index",
        "region_index",
        "window_start_s",
        "window_end_s",
        "window_dur_s",
        "window_source",
        "n_spikes",
        "rate_hz",
        "isi_mean_s",
        "isi_median_s",
        "cv_isi",
    ]
    return df[col_order]


def write_a1_outputs(
    df: pd.DataFrame,
    recording: str,
    out_dir: Union[str, Path] = "reports/library",
    *,
    preview_rows: int = 40,
) -> tuple[Path, Path]:
    """Write ``<recording>_metrics.parquet`` + small CSV preview."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parquet_path = out / f"{recording}_metrics.parquet"
    csv_path = out / f"{recording}_metrics_preview.csv"
    df.to_parquet(parquet_path, index=False)
    df.head(preview_rows).to_csv(csv_path, index=False)
    return parquet_path, csv_path
