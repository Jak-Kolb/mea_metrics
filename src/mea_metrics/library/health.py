"""Basic electrode / unit health flags (Plan A2, lightweight)."""

from __future__ import annotations

from typing import Dict

import numpy as np

from .rate import spikes_in_window


def health_row(spikes_s: np.ndarray, start_s: float, end_s: float) -> Dict[str, float]:
    """Per unit × window health basics."""
    sp = spikes_in_window(spikes_s, start_s, end_s)
    n = int(sp.size)
    return {
        "is_active": float(n > 0),
        "is_silent": float(n == 0),
    }
