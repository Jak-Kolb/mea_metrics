"""Four screening bars (LOCAL_PLAN B). Thresholds drafted on SMJM then frozen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .interpret import interpretability_pass

# --- Frozen on SMJM_Bicuculline 2026-09-22 ---
STABILITY_MIN_SPEARMAN = 0.50
STABILITY_MAX_MEDIAN_CV = 0.75  # soft diagnostic only
BEYOND_RATE_MAX_ABS_SPEARMAN = 0.90
TREATMENT_MIN_ABS_COHEN_D = 0.30

UNIT_METRICS: Sequence[str] = (
    "rate_hz",
    "isi_mean_s",
    "isi_median_s",
    "cv_isi",
    "burst_count",
    "burst_spike_frac",
    "mean_ibi_s",
    "sttc_mean_unit",
    "sttc_degree",
    "n_spikes",
)
WINDOW_METRICS: Sequence[str] = ("sttc_mean_window", "sttc_rate_resid_window")
NOVEL_METRICS: Sequence[str] = (
    "sttc_rate_resid_unit",
    "sttc_degree_delta",
    "sttc_mean_unit_delta",
    "rate_hz_delta",
    "burst_count_delta",
)
ALL_METRICS: Sequence[str] = tuple(list(UNIT_METRICS) + list(WINDOW_METRICS) + list(NOVEL_METRICS))


@dataclass
class BarResult:
    metric: str
    bar: str
    status: str  # PASS | FAIL | SKIP
    score: float
    threshold: str
    note: str


def _injury_region_split(
    df: pd.DataFrame, injury_start_s: float, injury_end_s: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    regs = (
        df.groupby("region_index", as_index=False)[["window_start_s", "window_end_s"]]
        .first()
        .sort_values("region_index")
    )
    baseline, during, post = [], [], []
    for _, r in regs.iterrows():
        i = int(r["region_index"])
        lo, hi = float(r["window_start_s"]), float(r["window_end_s"])
        if lo < injury_end_s and hi > injury_start_s:
            during.append(i)
        elif hi <= injury_start_s:
            baseline.append(i)
        else:
            post.append(i)
    return np.asarray(baseline, int), np.asarray(during, int), np.asarray(post, int)


def partition_regions(
    df: pd.DataFrame, injury_start_s: float, injury_end_s: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Public alias for screen baseline / during / post region split."""
    return _injury_region_split(df, injury_start_s, injury_end_s)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(m.sum()) < 5:
        return float("nan")
    ar = pd.Series(a[m]).rank().to_numpy()
    br = pd.Series(b[m]).rank().to_numpy()
    if np.std(ar) == 0 or np.std(br) == 0:
        return float("nan")
    return float(np.corrcoef(ar, br)[0, 1])


def _cohen_d(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    x = x[np.isfinite(x)]
    y = y[np.isfinite(y)]
    if x.size < 3 or y.size < 3:
        return float("nan")
    vx, vy = np.var(x, ddof=1), np.var(y, ddof=1)
    pooled = np.sqrt(((x.size - 1) * vx + (y.size - 1) * vy) / (x.size + y.size - 2))
    if pooled == 0:
        return float("nan")
    return float((np.mean(y) - np.mean(x)) / pooled)


def bar_stability(df: pd.DataFrame, metric: str, baseline_regions: np.ndarray) -> BarResult:
    if baseline_regions.size < 4:
        return BarResult(metric, "baseline_stability", "SKIP", float("nan"), "n/a", "too few baseline regions")
    base = df[df["region_index"].isin(baseline_regions)].copy()

    if metric in WINDOW_METRICS:
        series = base.groupby("region_index")[metric].first().sort_index()
        vals = series.to_numpy(dtype=float)
        mid = max(1, vals.size // 2)
        rho = _spearman(vals[:mid], vals[mid : mid + mid])
        mean = float(np.nanmean(vals))
        cv = float(np.nanstd(vals) / mean) if mean != 0 else float("nan")
        if np.isfinite(rho) and rho >= STABILITY_MIN_SPEARMAN:
            status, score, thr = "PASS", float(rho), f"Spearman≥{STABILITY_MIN_SPEARMAN}"
            note = f"window split-half Spearman={rho:.3f}; CV across baseline={cv:.3f}"
        elif (not np.isfinite(rho)) and np.isfinite(cv) and cv <= STABILITY_MAX_MEDIAN_CV:
            # Too few region tiles for Spearman; accept low CV as stability.
            status, score, thr = "PASS", float(cv), f"CV≤{STABILITY_MAX_MEDIAN_CV} (Spearman undefined)"
            note = f"window Spearman undefined (n_tiles={vals.size}); CV across baseline={cv:.3f}"
        else:
            status = "FAIL"
            score = float(rho) if np.isfinite(rho) else (float(cv) if np.isfinite(cv) else float("nan"))
            thr = f"Spearman≥{STABILITY_MIN_SPEARMAN}"
            note = f"window split-half Spearman={rho:.3f}; CV across baseline={cv:.3f}"
        return BarResult(metric, "baseline_stability", status, score, thr, note)

    regs = [int(x) for x in baseline_regions.tolist()]
    mid = len(regs) // 2
    early, late = regs[:mid], regs[mid:]
    piv = base.pivot_table(index="unit_id", columns="region_index", values=metric, aggfunc="mean")
    early_m = piv.reindex(columns=early).mean(axis=1)
    late_m = piv.reindex(columns=late).mean(axis=1)
    rho = _spearman(early_m.to_numpy(), late_m.to_numpy())
    cvs = piv.reindex(columns=regs).std(axis=1, ddof=0) / piv.reindex(columns=regs).mean(axis=1).replace(0, np.nan)
    med_cv = float(np.nanmedian(cvs.to_numpy()))
    status = "PASS" if np.isfinite(rho) and rho >= STABILITY_MIN_SPEARMAN else "FAIL"
    note = f"unit split-half Spearman={rho:.3f}; median unit CV={med_cv:.3f}"
    if status == "FAIL" and np.isfinite(med_cv) and med_cv <= STABILITY_MAX_MEDIAN_CV:
        note += " (median CV within soft cap, Spearman still below → FAIL)"
    return BarResult(
        metric,
        "baseline_stability",
        status,
        float(rho) if np.isfinite(rho) else float("nan"),
        f"Spearman≥{STABILITY_MIN_SPEARMAN}",
        note,
    )


def bar_beyond_rate(df: pd.DataFrame, metric: str) -> BarResult:
    if metric == "rate_hz":
        return BarResult(
            metric,
            "beyond_rate",
            "SKIP",
            float("nan"),
            f"|ρ|<{BEYOND_RATE_MAX_ABS_SPEARMAN}",
            "reference rate metric — bar 2 not applicable",
        )
    sub = df[["rate_hz", metric]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 20:
        return BarResult(metric, "beyond_rate", "SKIP", float("nan"), "n/a", "too few finite rows")
    rho = _spearman(sub["rate_hz"].to_numpy(), sub[metric].to_numpy())
    status = "PASS" if np.isfinite(rho) and abs(rho) < BEYOND_RATE_MAX_ABS_SPEARMAN else "FAIL"
    return BarResult(
        metric,
        "beyond_rate",
        status,
        float(abs(rho)) if np.isfinite(rho) else float("nan"),
        f"|Spearman(rate)|<{BEYOND_RATE_MAX_ABS_SPEARMAN}",
        f"Spearman(metric, rate_hz)={rho:.3f}",
    )


def bar_treatment(
    df: pd.DataFrame,
    metric: str,
    baseline_regions: np.ndarray,
    post_regions: np.ndarray,
    *,
    recording: str | None = None,
) -> BarResult:
    if metric.endswith("_delta"):
        return BarResult(
            metric,
            "treatment_response",
            "SKIP",
            float("nan"),
            "n/a",
            "metric is already a post−baseline delta — treatment bar not applicable",
        )
    if post_regions.size == 0 or baseline_regions.size == 0:
        return BarResult(metric, "treatment_response", "SKIP", float("nan"), "n/a", "no baseline or post regions")

    if metric in WINDOW_METRICS:
        base_v = df[df["region_index"].isin(baseline_regions)].groupby("region_index")[metric].first().to_numpy()
        post_v = df[df["region_index"].isin(post_regions)].groupby("region_index")[metric].first().to_numpy()
        d = _cohen_d(base_v, post_v)
    else:
        base = df[df["region_index"].isin(baseline_regions)].groupby("unit_id")[metric].median()
        post = df[df["region_index"].isin(post_regions)].groupby("unit_id")[metric].median()
        both = base.index.intersection(post.index)
        d = _cohen_d(base.loc[both].to_numpy(), post.loc[both].to_numpy())

    status = "PASS" if np.isfinite(d) and abs(d) >= TREATMENT_MIN_ABS_COHEN_D else "FAIL"
    return BarResult(
        metric,
        "treatment_response",
        status,
        float(abs(d)) if np.isfinite(d) else float("nan"),
        f"|Cohen_d|≥{TREATMENT_MIN_ABS_COHEN_D}",
        f"Cohen_d(post−baseline)={d:.3f}  *n=1 culture ({recording or 'unknown'}), no holdout yet*",
    )


def bar_interpretability(metric: str) -> BarResult:
    status, note = interpretability_pass(metric)
    return BarResult(metric, "interpretability", status, 1.0 if status == "PASS" else 0.0, "blurb registered", note)


def screen_recording(
    df: pd.DataFrame,
    *,
    injury_start_s: float,
    injury_end_s: float,
    metrics: Optional[Sequence[str]] = None,
    recording: Optional[str] = None,
) -> Tuple[List[BarResult], np.ndarray, np.ndarray, np.ndarray]:
    metrics_list = list(metrics) if metrics is not None else list(ALL_METRICS)
    baseline, during, post = _injury_region_split(df, injury_start_s, injury_end_s)
    results: List[BarResult] = []
    for m in metrics_list:
        if m not in df.columns:
            for bar in ("baseline_stability", "beyond_rate", "treatment_response", "interpretability"):
                results.append(BarResult(m, bar, "SKIP", float("nan"), "n/a", "column missing"))
            continue
        results.append(bar_stability(df, m, baseline))
        results.append(bar_beyond_rate(df, m))
        rec = recording or (str(df["recording"].iloc[0]) if "recording" in df.columns and len(df) else "unknown")
        results.append(bar_treatment(df, m, baseline, post, recording=rec))
        results.append(bar_interpretability(m))
    return results, baseline, during, post
