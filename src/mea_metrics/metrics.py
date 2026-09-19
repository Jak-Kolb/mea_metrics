"""Correlogram metrics (MATLAB calculateCorrelogramMetrics.m)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.signal import find_peaks
from scipy.stats import chi2

ArrayLike = Union[np.ndarray, Sequence[np.ndarray]]


def load_loess_kernel(path: Union[str, Path]) -> np.ndarray:
    """Load K (2001, 2001) from v7.3 mat; rows sum ≈ 1."""
    import h5py

    path = Path(path)
    with h5py.File(path, "r") as f:
        K = np.array(f["K"], dtype=np.float64).T
    if K.shape != (2001, 2001):
        raise ValueError(f"expected K shape (2001,2001), got {K.shape}")
    return K


@dataclass
class RegionMetrics:
    leader_prob: np.ndarray
    follower_prob: np.ndarray
    is_uniform: np.ndarray  # bool
    p_uniform: np.ndarray
    n_peaks: np.ndarray  # float; NaN if sparse
    peak_locations: List[np.ndarray]  # times (s); may contain NaN


def compute_region_metrics(
    probs: np.ndarray,
    n_events: np.ndarray,
    centers: np.ndarray,
    K: np.ndarray,
    *,
    unif_p_thresh: float = 0.05,
    sparse_thresh: float = 0.0,
) -> RegionMetrics:
    """Port calculateCorrelogramMetrics.m numeric core for one region.

    probs: (n_bins, n_pairs), n_events: (n_pairs,)
    """
    probs = np.asarray(probs, dtype=np.float64)
    n_events = np.asarray(n_events, dtype=np.float64)
    centers = np.asarray(centers, dtype=np.float64)
    n_bins, n_pairs = probs.shape
    assert centers.shape == (n_bins,)
    assert K.shape == (n_bins, n_bins)

    left = centers < 0
    right = centers > 0
    zero = centers == 0

    leader = np.nansum(probs[left, :], axis=0) + 0.5 * np.nansum(probs[zero, :], axis=0)
    follower = np.nansum(probs[right, :], axis=0) + 0.5 * np.nansum(probs[zero, :], axis=0)

    # Uniformity chi^2 on raw (unsmoothed) probs
    unif = np.full(n_bins, 1.0 / n_bins, dtype=np.float64)
    p_uniform = np.full(n_pairs, np.nan, dtype=np.float64)
    is_uniform = np.zeros(n_pairs, dtype=bool)
    for j in range(n_pairs):
        n = n_events[j]
        col = probs[:, j]
        if not np.isfinite(n) or n <= 0 or not np.isfinite(col).all():
            # empty / all-NaN → nonuniform, NaN p (MATLAB chi2 on zeros → NaN)
            p_uniform[j] = np.nan
            is_uniform[j] = False
            continue
        expected = n * unif
        observed = n * col
        with np.errstate(divide="ignore", invalid="ignore"):
            stat = np.sum((observed - expected) ** 2 / expected)
        p = float(chi2.sf(stat, n_bins - 1))
        p_uniform[j] = p
        is_uniform[j] = bool(p > unif_p_thresh)

    # Smooth for peak detection
    # Short-circuit all-NaN columns → 0 peaks
    sparse = n_events < sparse_thresh
    n_peaks = np.zeros(n_pairs, dtype=np.float64)
    peak_locations: List[np.ndarray] = []
    prom = float(unif[0])  # MinPeakProminence = 1/n_bins

    # Vectorized smooth where finite
    finite_cols = np.isfinite(probs).all(axis=0) & (n_events > 0)
    smoothed = np.full_like(probs, np.nan)
    if finite_cols.any():
        sm = K @ probs[:, finite_cols]
        sm = np.maximum(0.0, sm)
        col_sums = sm.sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            sm = sm / col_sums
        smoothed[:, finite_cols] = sm

    for j in range(n_pairs):
        if sparse[j]:
            # sparseCorrelogramThresh > 0: MATLAB sets NumPeaks to NaN
            n_peaks[j] = np.nan
            peak_locations.append(np.array([np.nan], dtype=np.float64))
            continue
        col = smoothed[:, j]
        if not np.isfinite(col).all():
            # empty / all-NaN with thresh==0 → 0 peaks (MATLAB findpeaks on NaN → [])
            n_peaks[j] = 0.0
            peak_locations.append(np.empty(0, dtype=np.float64))
            continue
        idxs, _ = find_peaks(col, prominence=prom)
        # Prefer left edge of plateaus (MATLAB findpeaks)
        if idxs.size:
            left = []
            for i in idxs:
                k = int(i)
                while k > 0 and col[k - 1] == col[k]:
                    k -= 1
                left.append(k)
            idxs = np.unique(np.asarray(left, dtype=np.intp))
        n_peaks[j] = float(idxs.size)
        peak_locations.append(centers[idxs] if idxs.size else np.empty(0, dtype=np.float64))

    # Sparse → NaN leader/follower
    leader = leader.astype(np.float64)
    follower = follower.astype(np.float64)
    leader[sparse] = np.nan
    follower[sparse] = np.nan

    return RegionMetrics(
        leader_prob=leader,
        follower_prob=follower,
        is_uniform=is_uniform,
        p_uniform=p_uniform,
        n_peaks=n_peaks,
        peak_locations=peak_locations,
    )
