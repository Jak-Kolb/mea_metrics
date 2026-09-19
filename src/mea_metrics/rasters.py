"""Build named rasters from plx data (MATLAB getRasters + badSignals/badRegions)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .plx import PlxData, spike_times_s

_LETTERS = "abcdefghijklmnopqrstuvwxyz"


@dataclass
class RasterSet:
    cell_ids: List[str]
    cell_display_names: List[str]
    rasters: List[np.ndarray]  # float64 seconds
    fs: float
    end_time_s: float
    n_active_electrodes: int
    n_total_electrodes: int

    @property
    def cell_count(self) -> int:
        return len(self.cell_ids)


def build_rasters_from_plx(plx: PlxData) -> RasterSet:
    """Reproduce getRasters.m naming and spike-time conversion.

    Per electrode, units sorted ascending by unit id; named ``s<electrode>a/b/c/d``
    in that order (lowest unit id → ``a``, even if unit 0).
    """
    cell_ids: List[str] = []
    display: List[str] = []
    rasters: List[np.ndarray] = []
    for ele, units in plx.electrodes.items():
        for j, (unit_id, ts) in enumerate(units):
            if j >= 4:
                # MATLAB warns and skips beyond 4
                continue
            letter = _LETTERS[j]
            cell_ids.append(f"s{ele}{letter}")
            # Display name approximates MATLAB dsp* from SIGName; verify uses CellIDs.
            display.append(f"dsp{ele}{letter}")
            rasters.append(spike_times_s(ts, plx.fs))

    n_active = len(plx.electrodes)
    # MATLAB TotalNumberOfElectrodes = length(SpikeChannels) including empties (64).
    # neo only lists channels with spikes; keep plx electrode count of actives here and
    # allow caller to override total from reference if needed.
    return RasterSet(
        cell_ids=cell_ids,
        cell_display_names=display,
        rasters=rasters,
        fs=plx.fs,
        end_time_s=plx.end_time_s,
        n_active_electrodes=n_active,
        n_total_electrodes=n_active,  # filled properly in apply step if known
    )


def apply_bad_signals(
    rasters: RasterSet, bad_signals: Optional[np.ndarray]
) -> RasterSet:
    """Drop units flagged in badSignals (boolean/0-1 mask aligned to CellIDs)."""
    if bad_signals is None:
        return rasters
    mask = np.asarray(bad_signals).ravel().astype(bool)
    if mask.size != len(rasters.cell_ids):
        raise ValueError(
            f"badSignals length {mask.size} != n cells {len(rasters.cell_ids)}"
        )
    keep = ~mask
    return RasterSet(
        cell_ids=[c for c, k in zip(rasters.cell_ids, keep) if k],
        cell_display_names=[c for c, k in zip(rasters.cell_display_names, keep) if k],
        rasters=[r for r, k in zip(rasters.rasters, keep) if k],
        fs=rasters.fs,
        end_time_s=rasters.end_time_s,
        n_active_electrodes=rasters.n_active_electrodes,
        n_total_electrodes=rasters.n_total_electrodes,
    )


def apply_bad_regions(
    rasters: RasterSet,
    regions: Sequence[Tuple[float, float]],
    *,
    indicator: int = 1,
) -> RasterSet:
    """Apply removeJunkRecordings.m region cuts (inclusive start/end in seconds)."""
    if indicator != 1 or not regions:
        return rasters

    end_time = float(rasters.end_time_s)
    new_rasters: List[np.ndarray] = []
    for spikes in rasters.rasters:
        keep = np.ones(spikes.shape[0], dtype=bool)
        for start, stop in regions:
            keep &= ~((spikes >= start) & (spikes <= stop))
        new_rasters.append(spikes[keep])

    # Update end time if a cut overhangs the recording end
    ends = np.asarray([e for _, e in regions], dtype=np.float64)
    starts = np.asarray([s for s, _ in regions], dtype=np.float64)
    if np.any(ends > end_time):
        cut_starts = starts[ends > end_time]
        max_remaining = max((float(r.max()) for r in new_rasters if r.size), default=0.0)
        end_time = max(float(np.max(cut_starts) - 0.001), max_remaining + 0.001)

    # Shift if a cut starts at 0
    if np.any(starts == 0):
        cut_ends = ends[starts == 0]
        min_remaining = min(
            (float(r.min()) for r in new_rasters if r.size), default=float(cut_ends.min())
        )
        minz = min(min_remaining - 0.001, float(np.min(cut_ends)))
        new_rasters = [r - minz for r in new_rasters]
        end_time = end_time - minz

    # Drop empty units
    keep_units = [r.size > 0 for r in new_rasters]
    return RasterSet(
        cell_ids=[c for c, k in zip(rasters.cell_ids, keep_units) if k],
        cell_display_names=[c for c, k in zip(rasters.cell_display_names, keep_units) if k],
        rasters=[r for r, k in zip(new_rasters, keep_units) if k],
        fs=rasters.fs,
        end_time_s=end_time,
        n_active_electrodes=rasters.n_active_electrodes,
        n_total_electrodes=rasters.n_total_electrodes,
    )


def build_rasters(
    plx: PlxData,
    *,
    bad_signals: Optional[np.ndarray] = None,
    bad_regions: Optional[Sequence[Tuple[float, float]]] = None,
    bad_regions_indicator: int = 0,
    n_total_electrodes: Optional[int] = None,
) -> RasterSet:
    """Full Stage 1 pipeline: getRasters → badSignals → badRegions."""
    rs = build_rasters_from_plx(plx)
    if n_total_electrodes is not None:
        rs.n_total_electrodes = int(n_total_electrodes)
    rs = apply_bad_signals(rs, bad_signals)
    rs = apply_bad_regions(
        rs, bad_regions or [], indicator=bad_regions_indicator
    )
    return rs
