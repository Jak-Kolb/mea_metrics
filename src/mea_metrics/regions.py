"""Analysis region auto-binning (MATLAB getInjuryOrTreatmentIndicies auto path)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

ArrayLike = Union[np.ndarray, Sequence[np.ndarray]]


@dataclass
class RegionTable:
    minutes: np.ndarray  # (n, 2) float64
    seconds: np.ndarray  # (n, 2) float64

    @property
    def num_regions(self) -> int:
        return int(self.minutes.shape[0])


def _max_minute_edge(end_time_s: float) -> int:
    """Last integer in MATLAB ``0:end_time_s/60`` (i.e. floor of minutes)."""
    return int(np.floor(float(end_time_s) / 60.0))


def auto_regions(
    end_time_s: float,
    rasters: Optional[ArrayLike] = None,
    *,
    region_len_min: float = 7.0,
    drop_silent: bool = True,
) -> RegionTable:
    """Reproduce the automatic region split from getInjuryOrTreatmentIndicies.m.

    Parameters
    ----------
    end_time_s
        ``ProcessedData.ExperimentEndTime`` (seconds).
    rasters
        Spike-time arrays (seconds). Required when ``drop_silent`` is True.
    region_len_min
        ``plotProps.automatedRegionBinLength`` (default 7).
    """
    L = float(region_len_min)
    M = _max_minute_edge(end_time_s)  # max(RecordingMetrics.minBinsSPM)

    # MATLAB:
    # if rem(M, L) ~= 0: endBinRound = M
    # else: endBinRound = (L - rem(M, L)) + M   # when rem==0, adds a full extra L
    if M % L != 0:
        end_bin_round = M
    else:
        end_bin_round = (L - (M % L)) + M

    edges = L * np.arange(0, int(end_bin_round // L) + 1, dtype=np.float64)
    starts = edges[:-1].copy()
    ends = edges[1:].copy() - L / 1000.0
    ends[-1] = min(float(ends[-1]), float(end_time_s) / 60.0)

    if (ends[-1] - starts[-1]) / L < 0.8:
        starts = starts[:-1]
        ends = ends[:-1]

    minutes = np.column_stack([starts, ends])

    if drop_silent:
        if rasters is None:
            raise ValueError("rasters required when drop_silent=True")
        minutes = _drop_silent_regions(minutes, rasters, end_time_s)

    seconds = minutes * 60.0
    return RegionTable(minutes=minutes.astype(np.float64), seconds=seconds.astype(np.float64))


def _drop_silent_regions(
    minutes: np.ndarray,
    rasters: ArrayLike,
    end_time_s: float,
) -> np.ndarray:
    """Remove regions that contain any minute with mean network SPM == 0.

    Matches:
      idx = minBinsSPM >= s & minBinsSPM <= e
      empty = sum(meanSPM(idx)>0)/numel < 1
    """
    M = _max_minute_edge(end_time_s)
    # histcounts edges 0:M → M bins; minBinsSPM = 1..M
    edges = np.arange(0, M + 1, dtype=np.float64)
    per_unit = []
    for spikes in rasters:
        sp = np.asarray(spikes, dtype=np.float64) / 60.0
        counts, _ = np.histogram(sp, bins=edges)
        per_unit.append(counts.astype(np.float64))
    if not per_unit:
        return minutes
    mean_spm = np.mean(np.vstack(per_unit), axis=0)  # length M, index 0 → minute label 1
    min_bins_spm = np.arange(1, M + 1, dtype=np.float64)

    keep = []
    for s, e in minutes:
        mask = (min_bins_spm >= s) & (min_bins_spm <= e)
        if not np.any(mask):
            keep.append(False)
            continue
        frac_positive = np.sum(mean_spm[mask] > 0) / np.sum(mask)
        keep.append(frac_positive >= 1.0)  # emptyRegions = frac < 1
    return minutes[np.asarray(keep, dtype=bool)]
