"""Bar 4 — interpretability blurbs for A v1 metrics (auto-pass if present)."""

from __future__ import annotations

METRIC_BLURBS = {
    "rate_hz": "Mean spike rate in the region window (spikes/s).",
    "isi_mean_s": "Mean inter-spike interval among spikes in the window.",
    "isi_median_s": "Median inter-spike interval in the window (robust to outliers).",
    "cv_isi": "Coefficient of variation of ISIs (std/mean); irregularity of firing.",
    "burst_count": "Count of max-interval bursts (ISI≤0.1 s, ≥3 spikes) in the window.",
    "burst_spike_frac": "Fraction of spikes that fall inside detected bursts.",
    "mean_ibi_s": "Mean inter-burst interval (NaN if fewer than 2 bursts).",
    "sttc_mean_window": "Mean Spike Time Tiling Coefficient over active unit pairs in the window.",
    "sttc_mean_unit": "This unit's mean STTC to other active units in the window.",
    "sttc_degree": "Count of partners with STTC > 0.1 (thin topology on thresholded STTC).",
    "n_spikes": "Raw spike count in the window (reference; expected to track rate closely).",

    # Plan C
    "sttc_rate_resid_unit": "STTC (unit mean) residualized against firing rate — sync beyond rate.",
    "sttc_rate_resid_window": "Window mean STTC residualized against window mean rate.",
    "sttc_degree_delta": "Post−baseline change in STTC degree (partners with STTC>0.1).",
    "sttc_mean_unit_delta": "Post−baseline change in unit mean STTC.",
    "rate_hz_delta": "Post−baseline change in mean firing rate.",
    "burst_count_delta": "Post−baseline change in burst count.",
}


def interpretability_pass(metric: str) -> tuple[str, str]:
    blurb = METRIC_BLURBS.get(metric)
    if blurb:
        return "PASS", blurb
    return "FAIL", "No plain-language spike-train story registered for this metric."
