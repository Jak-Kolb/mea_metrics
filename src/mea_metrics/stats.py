"""Per-region raster stats (MATLAB plotStatsInEachRegion.m numbers only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

from .regions import RegionTable


@dataclass
class RegionStats:
    """Per-region stats keyed by 0-based region index."""

    # rate: spike_count / region_length_seconds  (MATLAB mislabels as per-minute)
    spike_rate: Dict[int, np.ndarray] = field(default_factory=dict)
    # rate / total_spike_count  (MATLAB quirk — replicate)
    spike_fraction: Dict[int, np.ndarray] = field(default_factory=dict)
    isis: Dict[int, List[np.ndarray]] = field(default_factory=dict)
    spike_counts: Dict[int, np.ndarray] = field(default_factory=dict)


def compute_region_stats(
    rasters: Sequence[np.ndarray],
    regions: RegionTable,
) -> RegionStats:
    """Port the numeric block of plotStatsInEachRegion.m (no plotting).

    Region length divisor is **seconds** (AnalysisRegions.Seconds), despite the
    MATLAB comment saying \"per minute\". Documented in PORT_NOTES.md.
    """
    rasters_f = [np.asarray(r, dtype=np.float64) for r in rasters]
    totals = np.asarray([r.size for r in rasters_f], dtype=np.float64)
    # Avoid div-by-zero for empty units (should not occur post Stage 1)
    totals_safe = np.where(totals == 0, np.nan, totals)

    out = RegionStats()
    for i, (t0, t1) in enumerate(regions.seconds):
        length_s = float(t1 - t0)
        counts = np.asarray(
            [np.sum((r >= t0) & (r <= t1)) for r in rasters_f], dtype=np.float64
        )
        # MATLAB: regionSpikeCount = count / (Seconds_end - Seconds_start)
        rate = counts / length_s
        frac = rate / totals_safe
        isis: List[np.ndarray] = []
        for r in rasters_f:
            if r.size < 2:
                isis.append(np.asarray([], dtype=np.float64))
                continue
            # spikes in region → interval indices max(1, find-1) on full ISI list
            in_reg = (r >= t0) & (r <= t1)
            idxs = np.flatnonzero(in_reg)
            # MATLAB: max(1, find(x)-1) then SpikeIntervals(those)
            # SpikeIntervals(k) = r[k+1]-r[k] for k=1..n-1 in 1-based → r[k]-r[k-1] 0-based
            iv_idx = np.maximum(0, idxs - 1)
            iv_idx = iv_idx[iv_idx < r.size - 1]
            intervals = r[1:] - r[:-1]
            isis.append(intervals[iv_idx] if iv_idx.size else np.asarray([], dtype=np.float64))

        out.spike_counts[i] = counts
        out.spike_rate[i] = rate
        out.spike_fraction[i] = frac
        out.isis[i] = isis
    return out
