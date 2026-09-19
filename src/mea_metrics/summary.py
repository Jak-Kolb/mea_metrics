"""Correlogram classification fractions (MATLAB summarizeCorrelograms.m math only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

LF_NAMES = ("Weak", "Fairly Weak", "Intermediate", "Fairly Strong", "Strong")
LF_EDGES = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0], dtype=np.float64)
UNIF_NAMES = ("Nonuniform", "Uniform")


@dataclass
class RegionClassFractions:
    """Per-region class fractions over cross-correlograms (autos dropped)."""

    leader_follower: np.ndarray  # (5,) Weak..Strong
    peak_count: np.ndarray  # (n_peak_classes,)
    peak_count_names: Tuple[str, ...]
    uniformity: np.ndarray  # (2,) Nonuniform, Uniform
    n_pairs: int  # pairs after dropping autos
    n_lf_denom: int  # non-NaN leader
    n_peak_denom: int  # non-NaN peak counts
    n_unif_denom: int  # all pairs (logical; empties = Nonuniform)


def _offdiag_mask(n_cells: int) -> np.ndarray:
    """True for off-diagonal entries of an n×n matrix in Fortran (MATLAB) order."""
    eye = np.eye(n_cells, dtype=bool)
    return ~eye.reshape(-1, order="F")


def _as_flat(x: np.ndarray, n_cells: int) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64).reshape(-1)
    if a.size != n_cells * n_cells:
        raise ValueError(f"expected {n_cells*n_cells} entries, got {a.size}")
    return a


def classify_region(
    leader_prob: np.ndarray,
    n_peaks: np.ndarray,
    is_uniform: np.ndarray,
    *,
    n_cells: int,
    include_autocorrelograms: bool = False,
    max_peak_count_before_noise: int = 10,
) -> RegionClassFractions:
    """Port summarizeCorrelograms.m classification math for one region.

    Drop autocorrelograms when ``include_autocorrelograms`` is false (default).
    Leader/peak denominators exclude NaN; uniformity keeps every pair (empties =
    Nonuniform).
    """
    lead = _as_flat(leader_prob, n_cells)
    peaks = _as_flat(n_peaks, n_cells)
    unif = _as_flat(np.asarray(is_uniform, dtype=np.float64), n_cells)

    if include_autocorrelograms:
        sel = np.ones(n_cells * n_cells, dtype=bool)
    else:
        sel = _offdiag_mask(n_cells)

    lead = lead[sel]
    peaks = peaks[sel]
    unif = unif[sel]
    n_pairs = int(sel.sum())

    # --- leader / follower strength ---
    strength = np.abs(lead - 0.5) / 0.5
    lf = np.zeros(5, dtype=np.float64)
    finite_lf = np.isfinite(strength)
    for g in range(5):
        a, b = LF_EDGES[g], LF_EDGES[g + 1]
        if g == 0:
            in_bin = finite_lf & (strength >= a - 1.0) & (strength < b)
        elif g < 4:
            in_bin = finite_lf & (strength >= a) & (strength < b)
        else:
            in_bin = finite_lf & (strength >= a) & (strength <= b + 1.0)
        lf[g] = float(np.sum(in_bin))
    n_lf = int(np.sum(finite_lf))
    if n_lf > 0:
        lf = lf / n_lf
    else:
        lf[:] = np.nan

    # --- peak counts ---
    finite_pk = np.isfinite(peaks)
    peaks_f = peaks[finite_pk]
    if peaks_f.size == 0:
        pk = np.zeros(0, dtype=np.float64)
        pk_names: Tuple[str, ...] = ()
        n_pk = 0
    else:
        lo = int(np.min(peaks_f))
        hi_obs = int(np.max(peaks_f))
        hi = int(min(max_peak_count_before_noise, hi_obs))
        bounds = np.arange(lo, hi + 1, dtype=np.int64)
        pk = np.zeros(len(bounds), dtype=np.float64)
        names: List[str] = []
        for i, c in enumerate(bounds):
            if i == len(bounds) - 1 and max_peak_count_before_noise < hi_obs:
                pk[i] = float(np.sum(peaks_f >= c))
                names.append(f"{c} or More")
            elif i == len(bounds) - 1 and max_peak_count_before_noise >= hi_obs:
                # last class is exact count (== hi); MATLAB still uses >= for last
                pk[i] = float(np.sum(peaks_f >= c))
                names.append(str(c))
            else:
                pk[i] = float(np.sum(peaks_f == c))
                names.append(str(c))
        n_pk = int(peaks_f.size)
        pk = pk / n_pk
        pk_names = tuple(names)

    # --- uniformity (include empties as Nonuniform) ---
    # Treat NaN uniform as Nonuniform (0) so denom = n_pairs
    unif_bin = np.where(np.isnan(unif), 0.0, unif)
    unif_frac = np.zeros(2, dtype=np.float64)
    unif_frac[0] = float(np.sum(unif_bin == 0))
    unif_frac[1] = float(np.sum(unif_bin == 1))
    n_unif = n_pairs
    if n_unif > 0:
        unif_frac = unif_frac / n_unif
    else:
        unif_frac[:] = np.nan

    return RegionClassFractions(
        leader_follower=lf,
        peak_count=pk,
        peak_count_names=pk_names,
        uniformity=unif_frac,
        n_pairs=n_pairs,
        n_lf_denom=n_lf,
        n_peak_denom=n_pk,
        n_unif_denom=n_unif,
    )


def classify_all_regions(
    metrics_by_region: dict,
    *,
    n_cells: int,
    include_autocorrelograms: bool = False,
    max_peak_count_before_noise: int = 10,
) -> dict:
    """metrics_by_region: ri -> (p, uniform, leader, n_peaks, peak_locs)."""
    out = {}
    for ri, tup in metrics_by_region.items():
        _p, uniform, leader, n_peaks, _locs = tup
        out[ri] = classify_region(
            leader,
            n_peaks,
            uniform,
            n_cells=n_cells,
            include_autocorrelograms=include_autocorrelograms,
            max_peak_count_before_noise=max_peak_count_before_noise,
        )
    return out
