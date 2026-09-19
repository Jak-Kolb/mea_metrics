"""Correlogram generation (MATLAB generateCorrelograms.m)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

ArrayLike = Union[np.ndarray, Sequence[np.ndarray]]


def bin_centers_and_edges(
    bin_max: float = 1.0, n_bins: int = 2001
) -> Tuple[np.ndarray, np.ndarray]:
    """MATLAB linspace centers + gradient-based edges."""
    centers = np.linspace(-bin_max, bin_max, n_bins, dtype=np.float64)
    spacing = float(np.mean(np.gradient(centers)))
    edges = np.sort(
        np.concatenate([centers - spacing / 2.0, [centers[-1] + spacing / 2.0]])
    )
    return centers, edges


def _apply_region_bound_quirk(bounds_sec: np.ndarray) -> np.ndarray:
    """``RegionTimes(RegionTimes==60) = 0`` from generateCorrelograms.m."""
    out = np.array(bounds_sec, dtype=np.float64, copy=True)
    out[out == 60.0] = 0.0
    return out


def spikes_in_region(
    spikes: np.ndarray, t0: float, t1: float
) -> np.ndarray:
    """Inclusive both ends; empty → empty float64 array."""
    sp = np.asarray(spikes, dtype=np.float64)
    if sp.size == 0:
        return sp
    return sp[(sp >= t0) & (sp <= t1)]


def pair_lags_searchsorted(
    t_ref: np.ndarray,
    t_cmp: np.ndarray,
    bin_max: float,
) -> np.ndarray:
    """Lags ``t_cmp - t_ref`` inside ``[-bin_max, bin_max]`` via searchsorted.

    Matches plan Step 3 / MATLAB ``bsxfun(@minus, cmp, ref')`` then window.
    """
    t_ref = np.asarray(t_ref, dtype=np.float64)
    t_cmp = np.asarray(t_cmp, dtype=np.float64)
    if t_ref.size == 0 or t_cmp.size == 0:
        return np.empty(0, dtype=np.float64)
    # NaN placeholders (empty MATLAB rasters) → no finite lags
    if not np.isfinite(t_ref).any() or not np.isfinite(t_cmp).any():
        return np.empty(0, dtype=np.float64)
    t_ref = t_ref[np.isfinite(t_ref)]
    t_cmp = t_cmp[np.isfinite(t_cmp)]
    if t_ref.size == 0 or t_cmp.size == 0:
        return np.empty(0, dtype=np.float64)

    lo = np.searchsorted(t_cmp, t_ref - bin_max, side="left")
    hi = np.searchsorted(t_cmp, t_ref + bin_max, side="right")
    parts = [t_cmp[a:b] - t for a, b, t in zip(lo, hi, t_ref)]
    if not parts:
        return np.empty(0, dtype=np.float64)
    lags = np.concatenate(parts)
    return lags[(lags >= -bin_max) & (lags <= bin_max)]


def pair_lags_bruteforce(
    t_ref: np.ndarray,
    t_cmp: np.ndarray,
    bin_max: float,
) -> np.ndarray:
    """Brute-force ``t_cmp[:, None] - t_ref[None, :]`` for identity checks."""
    t_ref = np.asarray(t_ref, dtype=np.float64)
    t_cmp = np.asarray(t_cmp, dtype=np.float64)
    t_ref = t_ref[np.isfinite(t_ref)]
    t_cmp = t_cmp[np.isfinite(t_cmp)]
    if t_ref.size == 0 or t_cmp.size == 0:
        return np.empty(0, dtype=np.float64)
    lags = (t_cmp[:, None] - t_ref[None, :]).ravel()
    return lags[(lags >= -bin_max) & (lags <= bin_max)]


def lags_to_probs(
    lags: np.ndarray, edges: np.ndarray, n_bins: int
) -> Tuple[np.ndarray, int]:
    """MATLAB ``histcounts(..., 'Normalization', 'probability')``.

    Empty lags → all-NaN probs and n_events=0 (MATLAB histcounts on []).
    """
    if lags.size == 0:
        return np.full(n_bins, np.nan, dtype=np.float64), 0
    counts, _ = np.histogram(lags, bins=edges)
    probs = counts.astype(np.float64) / float(lags.size)
    return probs, int(lags.size)


@dataclass
class RegionCorrelograms:
    probs: np.ndarray  # (n_bins, n_pairs)
    n_events: np.ndarray  # (n_pairs,)
    names: List[str]


def compute_region_correlograms(
    cell_ids: Sequence[str],
    region_rasters: Sequence[np.ndarray],
    *,
    bin_max: float = 1.0,
    n_bins: int = 2001,
    edges: Optional[np.ndarray] = None,
) -> RegionCorrelograms:
    """All ordered pairs (cmp vs ref) for one region — column order matches MATLAB."""
    if edges is None:
        _, edges = bin_centers_and_edges(bin_max, n_bins)
    n = len(cell_ids)
    probs = np.empty((n_bins, n * n), dtype=np.float64)
    n_events = np.empty(n * n, dtype=np.float64)
    names: List[str] = []
    col = 0
    for i, ref_id in enumerate(cell_ids):
        t_ref = region_rasters[i]
        for j, cmp_id in enumerate(cell_ids):
            t_cmp = region_rasters[j]
            lags = pair_lags_searchsorted(t_ref, t_cmp, bin_max)
            p, nev = lags_to_probs(lags, edges, n_bins)
            probs[:, col] = p
            n_events[col] = nev
            names.append(f"{cmp_id} vs. {ref_id}")
            col += 1
    return RegionCorrelograms(probs=probs, n_events=n_events, names=names)


def prepare_region_rasters(
    rasters: Sequence[np.ndarray], t0: float, t1: float
) -> List[np.ndarray]:
    """Slice rasters to region; empty → empty array (NaN pad not needed for searchsorted)."""
    return [spikes_in_region(r, t0, t1) for r in rasters]


def cache_path(cache_dir: Path, region_index: int) -> Path:
    return Path(cache_dir) / f"region{region_index}.npz"


def save_region_cache(
    path: Path, result: RegionCorrelograms, centers: np.ndarray
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # float32 in cache per plan; float64 used in compute
    np.savez_compressed(
        path,
        probs=result.probs.astype(np.float32),
        n_events=result.n_events.astype(np.float64),
        names=np.asarray(result.names, dtype=object),
        centers=centers.astype(np.float64),
    )


def load_region_cache(path: Path) -> Optional[RegionCorrelograms]:
    if not path.is_file():
        return None
    z = np.load(path, allow_pickle=True)
    return RegionCorrelograms(
        probs=z["probs"].astype(np.float64),
        n_events=z["n_events"].astype(np.float64),
        names=[str(x) for x in z["names"].tolist()],
    )


def compute_all_regions(
    cell_ids: Sequence[str],
    rasters: Sequence[np.ndarray],
    regions_sec: np.ndarray,
    *,
    bin_max: float = 1.0,
    n_bins: int = 2001,
    cache_dir: Optional[Path] = None,
    region_indices: Optional[Sequence[int]] = None,
) -> Dict[int, RegionCorrelograms]:
    """Compute correlograms region-by-region (optionally cached)."""
    centers, edges = bin_centers_and_edges(bin_max, n_bins)
    bounds = _apply_region_bound_quirk(np.asarray(regions_sec, dtype=np.float64))
    indices = list(region_indices) if region_indices is not None else list(range(bounds.shape[0]))
    out: Dict[int, RegionCorrelograms] = {}
    for ri in indices:
        t0, t1 = float(bounds[ri, 0]), float(bounds[ri, 1])
        if cache_dir is not None:
            cp = cache_path(cache_dir, ri)
            cached = load_region_cache(cp)
            if cached is not None:
                out[ri] = cached
                continue
        region_rasters = prepare_region_rasters(rasters, t0, t1)
        result = compute_region_correlograms(
            cell_ids, region_rasters, bin_max=bin_max, n_bins=n_bins, edges=edges
        )
        if cache_dir is not None:
            save_region_cache(cache_path(cache_dir, ri), result, centers)
        out[ri] = result
    return out
