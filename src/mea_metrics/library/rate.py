"""Per-unit rate and ISI stats inside one window."""

from __future__ import annotations

from typing import Dict

import numpy as np


def spikes_in_window(spikes_s: np.ndarray, start_s: float, end_s: float) -> np.ndarray:
    """Spikes with start_s <= t < end_s (half-open; avoids double-count on boundaries)."""
    sp = np.asarray(spikes_s, dtype=np.float64).ravel()
    if sp.size == 0:
        return sp
    return sp[(sp >= start_s) & (sp < end_s)]


def rate_isi_row(spikes_s: np.ndarray, start_s: float, end_s: float) -> Dict[str, float]:
    """Mean rate (Hz) + ISI mean/median/CV for spikes in [start_s, end_s).

    cv_isi = std(ISI)/mean(ISI); NaN if fewer than 2 ISIs (<3 spikes).
    Rate uses full window duration (0 Hz if silent).
    """
    dur = float(end_s - start_s)
    if dur <= 0:
        raise ValueError(f"non-positive duration: {dur}")
    sp = spikes_in_window(spikes_s, start_s, end_s)
    n = int(sp.size)
    rate_hz = n / dur
    if n < 2:
        return {
            "n_spikes": float(n),
            "rate_hz": float(rate_hz),
            "isi_mean_s": float("nan"),
            "isi_median_s": float("nan"),
            "cv_isi": float("nan"),
        }
    isi = np.diff(sp)
    isi_mean = float(np.mean(isi))
    isi_med = float(np.median(isi))
    if n < 3 or isi_mean == 0.0:
        cv = float("nan")
    else:
        cv = float(np.std(isi, ddof=0) / isi_mean)
    return {
        "n_spikes": float(n),
        "rate_hz": float(rate_hz),
        "isi_mean_s": isi_mean,
        "isi_median_s": isi_med,
        "cv_isi": cv,
    }
