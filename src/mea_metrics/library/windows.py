"""Analysis windows for the metric library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class Window:
    """One analysis tile (seconds)."""

    index: int
    start_s: float
    end_s: float
    source: str = "region"  # "region" | "grid" (grid = later mode)

    @property
    def duration_s(self) -> float:
        return float(self.end_s - self.start_s)


def windows_from_regions(
    regions_sec: np.ndarray,
    *,
    source: str = "region",
) -> List[Window]:
    """Build windows from AnalysisRegions ``regions_sec`` (N×2, seconds).

    Locked A1 default: one window per region, start/end as stored (no pad/trim).
    """
    arr = np.asarray(regions_sec, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"regions_sec must be (N,2); got {arr.shape}")
    out: List[Window] = []
    for i, (lo, hi) in enumerate(arr):
        lo_f, hi_f = float(lo), float(hi)
        if not np.isfinite(lo_f) or not np.isfinite(hi_f) or hi_f <= lo_f:
            raise ValueError(f"bad region {i}: [{lo_f}, {hi_f}]")
        out.append(Window(index=i, start_s=lo_f, end_s=hi_f, source=source))
    return out


def windows_fixed_grid(
    end_time_s: float,
    win_s: float,
    step_s: float,
    *,
    start_s: float = 0.0,
) -> List[Window]:
    """Optional later mode: fixed-duration sliding/tiling grid (not A1 default)."""
    if win_s <= 0 or step_s <= 0:
        raise ValueError("win_s and step_s must be > 0")
    out: List[Window] = []
    t = float(start_s)
    i = 0
    while t + win_s <= float(end_time_s) + 1e-12:
        out.append(Window(index=i, start_s=t, end_s=t + win_s, source="grid"))
        t += step_s
        i += 1
    return out
