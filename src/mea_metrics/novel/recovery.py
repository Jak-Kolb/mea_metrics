"""Recovery-time / return-to-baseline on the region grid (Plan C)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


def _network_burst_rate(df: pd.DataFrame) -> pd.Series:
    """Proxy network burst rate per region: mean(burst_count / window_dur_s) over active units."""
    d = df.copy()
    dur = d["window_dur_s"].replace(0, np.nan)
    d["_br"] = d["burst_count"] / dur
    if "is_active" in d.columns:
        d = d[d["is_active"].astype(bool)]
    return d.groupby("region_index")["_br"].mean().sort_index()


def _network_mean_rate(df: pd.DataFrame) -> pd.Series:
    d = df
    if "is_active" in d.columns:
        d = d[d["is_active"].astype(bool)]
    return d.groupby("region_index")["rate_hz"].mean().sort_index()


def recovery_metrics(
    df: pd.DataFrame,
    *,
    baseline_regions: np.ndarray,
    post_regions: np.ndarray,
    injury_end_s: float,
    band_k: float = 1.0,
) -> Dict[str, float]:
    """Compute culture-level recovery summaries from the library table.

    Returns scalars (repeated onto every row by the caller):
    - ``tau_rec_burst_s``: time from injury end to first post region whose
      network burst-rate is within baseline mean ± k·SD. NaN if never.
    - ``tau_rec_rate_s``: same for network mean rate.
    - ``burst_rate_ratio_post0`` / ``_post_mid`` / ``_post_last``: post/baseline
      ratios at first, middle, and last post regions.
    - ``rate_ratio_post0`` / ``_post_mid`` / ``_post_last``: same for mean rate.
    """
    br = _network_burst_rate(df)
    mr = _network_mean_rate(df)
    # region start times
    starts = df.groupby("region_index")["window_start_s"].first()

    def _band(series: pd.Series) -> Tuple[float, float, float]:
        base = series.reindex(baseline_regions).dropna()
        mu = float(base.mean()) if len(base) else float("nan")
        sd = float(base.std(ddof=0)) if len(base) else float("nan")
        return mu, sd, float(band_k)

    def _tau(series: pd.Series, mu: float, sd: float, k: float) -> float:
        if not np.isfinite(mu):
            return float("nan")
        lo, hi = mu - k * (sd if np.isfinite(sd) else 0.0), mu + k * (sd if np.isfinite(sd) else 0.0)
        for ridx in post_regions:
            if ridx not in series.index or not np.isfinite(series.loc[ridx]):
                continue
            v = float(series.loc[ridx])
            if lo <= v <= hi:
                t0 = float(starts.loc[ridx]) if ridx in starts.index else float("nan")
                return t0 - float(injury_end_s) if np.isfinite(t0) else float("nan")
        return float("nan")

    def _ratios(series: pd.Series, mu: float) -> Tuple[float, float, float]:
        if not np.isfinite(mu) or mu == 0 or len(post_regions) == 0:
            return float("nan"), float("nan"), float("nan")
        idxs = list(post_regions)
        picks = [idxs[0], idxs[len(idxs) // 2], idxs[-1]]
        out = []
        for ridx in picks:
            v = float(series.loc[ridx]) if ridx in series.index else float("nan")
            out.append(v / mu if np.isfinite(v) else float("nan"))
        return out[0], out[1], out[2]

    mu_b, sd_b, k = _band(br)
    mu_r, sd_r, _ = _band(mr)
    b0, bmid, blast = _ratios(br, mu_b)
    r0, rmid, rlast = _ratios(mr, mu_r)
    return {
        "tau_rec_burst_s": _tau(br, mu_b, sd_b, k),
        "tau_rec_rate_s": _tau(mr, mu_r, sd_r, k),
        "burst_rate_ratio_post0": b0,
        "burst_rate_ratio_post_mid": bmid,
        "burst_rate_ratio_post_last": blast,
        "rate_ratio_post0": r0,
        "rate_ratio_post_mid": rmid,
        "rate_ratio_post_last": rlast,
        "baseline_burst_rate_mean": mu_b,
        "baseline_rate_mean": mu_r,
    }


def add_unit_topology_deltas(
    df: pd.DataFrame,
    *,
    baseline_regions: np.ndarray,
    post_regions: np.ndarray,
) -> pd.DataFrame:
    """Per-unit Δ of sttc_degree and sttc_mean_unit (post median − baseline median)."""
    out = df.copy()
    base = out[out["region_index"].isin(baseline_regions)]
    post = out[out["region_index"].isin(post_regions)]
    for col, newcol in (
        ("sttc_degree", "sttc_degree_delta"),
        ("sttc_mean_unit", "sttc_mean_unit_delta"),
        ("rate_hz", "rate_hz_delta"),
        ("burst_count", "burst_count_delta"),
    ):
        b = base.groupby("unit_id")[col].median()
        p = post.groupby("unit_id")[col].median()
        both = b.index.intersection(p.index)
        delta = (p.loc[both] - b.loc[both]).to_dict()
        out[newcol] = out["unit_id"].map(delta)
    return out
