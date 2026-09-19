"""Pipeline constants mirroring Main_AnalyzeRecordingData.m / plotProps."""

from __future__ import annotations

import os
from pathlib import Path

# Defaults from MATLAB Main_AnalyzeRecordingData.m / plotProps.mat
BIN_MAX = 1.0  # seconds
N_BINS = 2001
SMOOTHING_FACTOR = 0.01
UNIF_P = 0.05
SPARSE_THRESHOLD = 0
INCLUDE_AUTOCORRELOGRAMS = False
REGION_LEN_MIN = 7
SMOOTHING_WINDOW_SIZE = 20
MAX_PEAK_COUNT_BEFORE_NOISE = 10


def matlab_data_root() -> Path:
    """Root containing matlab_reference/ and raw/.

    Box default: /workspace/mea_metrics_port/data
    Override with env MEA_MATLAB_DATA (e.g. Mac symlink to original_mea_matlab/data).
    """
    env = os.environ.get("MEA_MATLAB_DATA")
    if env:
        return Path(env).expanduser().resolve()
    # package lives at <repo>/src/mea_metrics/; data is sibling of src
    here = Path(__file__).resolve()
    repo = here.parents[2]  # .../mea_metrics_port
    return (repo / "data").resolve()


def matlab_reference_dir(recording: str) -> Path:
    return matlab_data_root() / "matlab_reference" / recording


def raw_plx_path(recording: str) -> Path:
    return matlab_data_root() / "raw" / f"{recording}.plx"
