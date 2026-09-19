"""Load Plexon .plx spike data (MATLAB readPLX / getRasters input)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

_LETTERS = "abcdefghijklmnopqrstuvwxyz"


@dataclass
class PlxData:
    """Integer timestamps and unit ids per electrode, plus fs and last timestamp."""

    path: Path
    fs: float
    last_timestamp: int
    # electrode_id -> list of (unit_id, timestamps_int) sorted by unit_id ascending
    electrodes: Dict[int, List[Tuple[int, np.ndarray]]] = field(default_factory=dict)

    @property
    def end_time_s(self) -> float:
        return float(self.last_timestamp) / float(self.fs)


def load_plx(path: Union[str, Path]) -> PlxData:
    """Load a .plx via neo.rawio.PlexonRawIO.

    Spike times in seconds are ``timestamps.astype(np.float64) / fs`` — divide once,
    never round (callers do the divide).
    """
    from neo.rawio import PlexonRawIO

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    reader = PlexonRawIO(filename=str(path))
    reader.parse_header()

    fs = float(reader._global_ssampling_rate)
    last_ts = int(reader._last_timestamps)

    import re
    from collections import defaultdict

    by_ele: Dict[int, List[Tuple[int, np.ndarray]]] = defaultdict(list)
    sc = reader.header["spike_channels"]
    for i, ch in enumerate(sc):
        m = re.match(r"ch(\d+)#(\d+)$", str(ch["id"]))
        if m is None:
            # Fallback: sigNNN name + unit from id if present
            raise ValueError(f"Unrecognized neo spike channel id: {ch['id']!r}")
        ele = int(m.group(1))
        unit = int(m.group(2))
        ts = np.asarray(reader.get_spike_timestamps(0, 0, i), dtype=np.int64)
        by_ele[ele].append((unit, ts))

    electrodes: Dict[int, List[Tuple[int, np.ndarray]]] = {}
    for ele in sorted(by_ele):
        units = sorted(by_ele[ele], key=lambda x: x[0])
        electrodes[ele] = units

    return PlxData(path=path, fs=fs, last_timestamp=last_ts, electrodes=electrodes)


def spike_times_s(timestamps: np.ndarray, fs: float) -> np.ndarray:
    """Convert integer Plexon timestamps to seconds (float64, no rounding)."""
    return np.asarray(timestamps, dtype=np.float64) / float(fs)
