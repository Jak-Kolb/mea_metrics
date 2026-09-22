"""Max-interval burst detector (Plan A2).

Defaults from LIBRARY_NOTES.md: max_isi_s=0.1, min_spikes=3.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from .rate import spikes_in_window

DEFAULT_MAX_ISI_S = 0.1
DEFAULT_MIN_SPIKES = 3


def detect_bursts(
    spikes_s: np.ndarray,
    *,
    max_isi_s: float = DEFAULT_MAX_ISI_S,
    min_spikes: int = DEFAULT_MIN_SPIKES,
) -> List[Tuple[int, int]]:
    """Return burst index ranges as (start_idx, end_idx_exclusive) into spikes_s.

    A burst is a run of ≥ min_spikes spikes whose consecutive ISIs are all ≤ max_isi_s.
    """
    sp = np.asarray(spikes_s, dtype=np.float64).ravel()
    n = int(sp.size)
    if n < min_spikes:
        return []
    isi = np.diff(sp)
    bursts: List[Tuple[int, int]] = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and isi[j] <= max_isi_s:
            j += 1
        # spikes i..j inclusive form a run linked by short ISIs
        length = j - i + 1
        if length >= min_spikes:
            bursts.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    return bursts


def burst_metrics_row(
    spikes_s: np.ndarray,
    start_s: float,
    end_s: float,
    *,
    max_isi_s: float = DEFAULT_MAX_ISI_S,
    min_spikes: int = DEFAULT_MIN_SPIKES,
) -> Dict[str, float]:
    """Per unit × window: burst_count, burst_spike_frac, mean_ibi_s."""
    sp = spikes_in_window(spikes_s, start_s, end_s)
    n = int(sp.size)
    bursts = detect_bursts(sp, max_isi_s=max_isi_s, min_spikes=min_spikes)
    n_bursts = len(bursts)
    n_in_burst = int(sum(b - a for a, b in bursts))
    frac = float(n_in_burst / n) if n > 0 else float("nan")
    if n_bursts < 2:
        mean_ibi = float("nan")
    else:
        # IBI = time from end of burst k to start of burst k+1
        ibis = [float(sp[bursts[k + 1][0]] - sp[bursts[k][1] - 1]) for k in range(n_bursts - 1)]
        mean_ibi = float(np.mean(ibis))
    return {
        "burst_count": float(n_bursts),
        "burst_spike_frac": frac,
        "mean_ibi_s": mean_ibi,
    }
