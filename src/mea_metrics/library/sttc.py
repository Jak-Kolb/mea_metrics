"""Spike Time Tiling Coefficient (Cutts & Eglen 2014). Plan A2."""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np

from .rate import spikes_in_window

DEFAULT_DT_S = 0.05  # 50 ms tiling half-width
DEFAULT_DEGREE_THRESH = 0.1


def _tile_fraction(spikes_s: np.ndarray, dt_s: float, duration_s: float) -> float:
    """Fraction of [0, duration] covered by unions of [t-dt, t+dt] clipped to window."""
    if spikes_s.size == 0 or duration_s <= 0:
        return 0.0
    lo = np.maximum(0.0, spikes_s - dt_s)
    hi = np.minimum(duration_s, spikes_s + dt_s)
    order = np.argsort(lo)
    lo, hi = lo[order], hi[order]
    covered = 0.0
    cur_lo, cur_hi = float(lo[0]), float(hi[0])
    for a, b in zip(lo[1:], hi[1:]):
        a, b = float(a), float(b)
        if a <= cur_hi:
            if b > cur_hi:
                cur_hi = b
        else:
            covered += cur_hi - cur_lo
            cur_lo, cur_hi = a, b
    covered += cur_hi - cur_lo
    return float(min(1.0, covered / duration_s))


def _proportion_within(spikes_a: np.ndarray, spikes_b: np.ndarray, dt_s: float) -> float:
    """Fraction of A spikes within ±dt of at least one B spike (vectorized)."""
    if spikes_a.size == 0:
        return 0.0
    if spikes_b.size == 0:
        return 0.0
    idx = np.searchsorted(spikes_b, spikes_a)
    # candidate neighbors: idx-1 and idx
    hit = np.zeros(spikes_a.size, dtype=bool)
    # right neighbor
    right_ok = idx < spikes_b.size
    if np.any(right_ok):
        hit[right_ok] |= np.abs(spikes_b[idx[right_ok]] - spikes_a[right_ok]) <= dt_s
    # left neighbor
    left_ok = idx > 0
    if np.any(left_ok):
        hit[left_ok] |= np.abs(spikes_b[idx[left_ok] - 1] - spikes_a[left_ok]) <= dt_s
    return float(np.mean(hit))


def sttc_pair(
    spikes_a: np.ndarray,
    spikes_b: np.ndarray,
    duration_s: float,
    *,
    dt_s: float = DEFAULT_DT_S,
) -> float:
    """STTC for two spike trains over a window of length duration_s.

    Spikes should be window-local in [0, duration_s] (tiling uses that clock).
    """
    a = np.asarray(spikes_a, dtype=np.float64).ravel()
    b = np.asarray(spikes_b, dtype=np.float64).ravel()
    if a.size == 0 or b.size == 0 or duration_s <= 0:
        return float("nan")
    pa = _proportion_within(a, b, dt_s)
    pb = _proportion_within(b, a, dt_s)
    ta = _tile_fraction(a, dt_s, duration_s)
    tb = _tile_fraction(b, dt_s, duration_s)
    den1 = 1.0 - pa * tb
    den2 = 1.0 - pb * ta
    if den1 == 0.0 or den2 == 0.0:
        return float("nan")
    return float(0.5 * ((pa - tb) / den1 + (pb - ta) / den2))


def window_sttc_summary(
    unit_spikes: Sequence[np.ndarray],
    start_s: float,
    end_s: float,
    *,
    dt_s: float = DEFAULT_DT_S,
    degree_thresh: float = DEFAULT_DEGREE_THRESH,
) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Pairwise STTC among active units in a window.

    Returns mean_sttc, unit_mean_sttc, unit_degree, active_mask.
    """
    dur = float(end_s - start_s)
    n = len(unit_spikes)
    local = [spikes_in_window(sp, start_s, end_s) - start_s for sp in unit_spikes]
    active = np.array([s.size > 0 for s in local], dtype=bool)
    unit_mean = np.full(n, np.nan, dtype=np.float64)
    unit_deg = np.zeros(n, dtype=np.float64)
    active_idx = np.flatnonzero(active)
    if active_idx.size < 2:
        return float("nan"), unit_mean, unit_deg, active

    mat = np.full((n, n), np.nan, dtype=np.float64)
    pair_vals: List[float] = []
    for ii in range(active_idx.size):
        i = int(active_idx[ii])
        for jj in range(ii + 1, active_idx.size):
            j = int(active_idx[jj])
            v = sttc_pair(local[i], local[j], dur, dt_s=dt_s)
            mat[i, j] = mat[j, i] = v
            if np.isfinite(v):
                pair_vals.append(v)

    mean_sttc = float(np.mean(pair_vals)) if pair_vals else float("nan")
    for i in active_idx:
        row = mat[i, active]
        row = row[np.isfinite(row)]
        if row.size:
            unit_mean[i] = float(np.mean(row))
            unit_deg[i] = float(np.sum(row > degree_thresh))
    return mean_sttc, unit_mean, unit_deg, active
