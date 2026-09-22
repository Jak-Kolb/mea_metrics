"""Assemble and write Plan A metric tables."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from ..config import raw_plx_path
from ..matref import load_reference
from ..plx import load_plx
from ..rasters import RasterSet, build_rasters
from .bursts import burst_metrics_row
from .health import health_row
from .rate import rate_isi_row
from .sttc import DEFAULT_DEGREE_THRESH, DEFAULT_DT_S, window_sttc_summary
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


def build_a2_table(
    recording: str,
    *,
    rasters: Optional[RasterSet] = None,
    regions_sec: Optional[np.ndarray] = None,
    sttc_dt_s: float = DEFAULT_DT_S,
    sttc_degree_thresh: float = DEFAULT_DEGREE_THRESH,
) -> pd.DataFrame:
    """Per unit × region: A1 rate/ISI + A2 bursts, STTC, health, thin topology."""
    ref = load_reference(recording)
    rs = rasters if rasters is not None else _load_rasters(recording)
    regs = regions_sec if regions_sec is not None else ref.regions_sec
    if regs is None:
        raise RuntimeError(f"{recording}: no AnalysisRegions (regions_sec)")
    windows: List[Window] = windows_from_regions(regs)

    rows = []
    for w in windows:
        mean_sttc, unit_mean_sttc, unit_degree, active_mask = window_sttc_summary(
            rs.rasters,
            w.start_s,
            w.end_s,
            dt_s=sttc_dt_s,
            degree_thresh=sttc_degree_thresh,
        )
        n_active = int(active_mask.sum())
        for unit_i, (uid, spikes) in enumerate(zip(rs.cell_ids, rs.rasters)):
            m = rate_isi_row(spikes, w.start_s, w.end_s)
            b = burst_metrics_row(spikes, w.start_s, w.end_s)
            h = health_row(spikes, w.start_s, w.end_s)
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
                    **b,
                    **h,
                    "sttc_mean_window": mean_sttc,
                    "sttc_mean_unit": float(unit_mean_sttc[unit_i]),
                    "sttc_degree": float(unit_degree[unit_i]),
                    "n_active_units_window": float(n_active),
                    "sttc_dt_s": float(sttc_dt_s),
                    "sttc_degree_thresh": float(sttc_degree_thresh),
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
        "burst_count",
        "burst_spike_frac",
        "mean_ibi_s",
        "is_active",
        "is_silent",
        "sttc_mean_window",
        "sttc_mean_unit",
        "sttc_degree",
        "n_active_units_window",
        "sttc_dt_s",
        "sttc_degree_thresh",
    ]
    return df[col_order]


# Back-compat alias used by A1 CLI path
def build_a1_table(*args, **kwargs) -> pd.DataFrame:
    """A1 = A2 table (A2 is a strict column extension)."""
    return build_a2_table(*args, **kwargs)


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


write_a2_outputs = write_a1_outputs

ALL_ADAM_RECORDINGS: Sequence[str] = (
    "SMJM_Bicuculline",
    "ER52_ImpactWithBicuculline",
    "JMSM_ImpactWithoutBicuculline",
    "SM_pHshock",
)
