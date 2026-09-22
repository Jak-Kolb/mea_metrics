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



def _as_uint32_timestamp(value) -> int:
    """Interpret a Plexon timestamp as uint32 (handles signed overflow)."""
    arr = np.asarray(value).reshape(-1)
    if arr.size == 0:
        return 0
    if np.issubdtype(arr.dtype, np.unsignedinteger):
        return int(arr[0])
    # Wrap through int64→uint32 so negative Python ints from neo are safe
    return int(np.asarray(arr[0], dtype=np.int64).astype(np.uint32))


def _spike_timestamps_int64(raw) -> np.ndarray:
    """Spike timestamps as non-negative int64 (uint32 semantics if signed wrap)."""
    ts = np.asarray(raw)
    if ts.size == 0:
        return np.asarray([], dtype=np.int64)
    if np.issubdtype(ts.dtype, np.unsignedinteger):
        return ts.astype(np.int64, copy=False)
    if ts.dtype == np.int32 or (ts.dtype == np.int64 and bool(np.any(ts < 0))):
        return np.asarray(ts, dtype=np.int64).astype(np.uint32).astype(np.int64)
    return ts.astype(np.int64, copy=False)


def _unwrap_neo_spike_timestamps(reader) -> None:
    """Rewrite neo data-block timestamps that wrapped through int32 (~2^31)."""
    blocks = getattr(reader, "_data_blocks", None)
    if not blocks or 1 not in blocks:
        return
    for chan_id, block in list(blocks[1].items()):
        if block is None or len(block) == 0:
            continue
        ts = np.asarray(block["timestamp"])
        if not np.issubdtype(ts.dtype, np.signedinteger):
            continue
        if not np.any(ts < 0):
            continue
        unwrapped = ts.astype(np.int64, copy=True)
        unwrapped[ts < 0] += np.int64(2**32)
        try:
            block["timestamp"] = unwrapped
        except (ValueError, TypeError):
            new_block = np.array(block, copy=True)
            new_block["timestamp"] = unwrapped
            blocks[1][chan_id] = new_block



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
    # Plexon timestamps are uint32. Neo may expose signed values that overflow
    # int32 for long recordings (e.g. SM_pHshock ~2.95e9 samples). That breaks
    # segment t_stop and drops late spikes in _get_internal_mask — fix in place.
    last_ts = _as_uint32_timestamp(reader._last_timestamps)
    reader._last_timestamps = last_ts
    _unwrap_neo_spike_timestamps(reader)

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
        ts = _spike_timestamps_int64(reader.get_spike_timestamps(0, 0, i))
        by_ele[ele].append((unit, ts))

    electrodes: Dict[int, List[Tuple[int, np.ndarray]]] = {}
    for ele in sorted(by_ele):
        units = sorted(by_ele[ele], key=lambda x: x[0])
        electrodes[ele] = units

    return PlxData(path=path, fs=fs, last_timestamp=last_ts, electrodes=electrodes)


def spike_times_s(timestamps: np.ndarray, fs: float) -> np.ndarray:
    """Convert integer Plexon timestamps to seconds (float64, no rounding)."""
    return np.asarray(timestamps, dtype=np.float64) / float(fs)
