"""Load MATLAB reference .mat outputs for stage-by-stage verification.

Data layout (actual, not plan wording):
  <MEA_MATLAB_DATA>/matlab_reference/<recording>/*.mat
  <MEA_MATLAB_DATA>/raw/<recording>.plx

Default MEA_MATLAB_DATA on the box: /workspace/mea_metrics_port/data

Region indexing: correlograms and metrics use 0-based int keys where
Region1 → 0, Region2 → 1, ..., RegionN → N-1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .config import matlab_reference_dir

# ---------------------------------------------------------------------------
# low-level loaders
# ---------------------------------------------------------------------------


def _is_mat_struct(obj: Any) -> bool:
    return hasattr(obj, "_fieldnames")


def _to_str(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, (bytes, np.bytes_)):
        return x.decode("utf-8", errors="replace")
    if isinstance(x, np.ndarray):
        if x.dtype.kind in ("U", "S"):
            return str(x.item() if x.ndim == 0 else x.tolist())
        if x.dtype == object and x.size == 1:
            return _to_str(x.flat[0])
    return str(x)


def _as_1d_str_list(arr: Any) -> List[str]:
    if arr is None:
        return []
    a = np.atleast_1d(np.asarray(arr, dtype=object))
    return [_to_str(x) for x in a.flat]


def _as_float_array(arr: Any) -> np.ndarray:
    if arr is None:
        return np.asarray([], dtype=np.float64)
    if isinstance(arr, (int, float, np.integer, np.floating)):
        return np.asarray([arr], dtype=np.float64)
    return np.asarray(arr, dtype=np.float64)


def _as_int_array(arr: Any) -> np.ndarray:
    if arr is None:
        return np.asarray([], dtype=np.int64)
    if isinstance(arr, (int, float, np.integer, np.floating)):
        return np.asarray([int(arr)], dtype=np.int64)
    return np.asarray(arr, dtype=np.int64)


def _loadmat_scipy(path: Path) -> Dict[str, Any]:
    import scipy.io as sio

    return sio.loadmat(
        str(path),
        struct_as_record=False,
        squeeze_me=True,
    )


def _h5_to_numpy(f: Any, ref_or_ds: Any) -> Any:
    """Dereference an h5py dataset / object reference into numpy (MATLAB v7.3)."""
    import h5py

    if isinstance(ref_or_ds, h5py.Reference):
        ds = f[ref_or_ds]
    else:
        ds = ref_or_ds

    if isinstance(ds, h5py.Group):
        # struct → simple namespace dict
        out = {}
        for k in ds.keys():
            out[k] = _h5_to_numpy(f, ds[k])
        return out

    data = ds[()]
    # MATLAB stores column-major; h5py gives C-order → transpose
    if isinstance(data, np.ndarray) and data.ndim >= 2:
        data = np.array(data).T
    # cell arrays of references
    if isinstance(data, np.ndarray) and data.dtype == object:
        flat = []
        for item in data.flat:
            if isinstance(item, h5py.Reference):
                flat.append(_h5_to_numpy(f, item))
            else:
                flat.append(item)
        data = np.array(flat, dtype=object).reshape(data.shape)
    # char arrays
    if isinstance(data, np.ndarray) and data.dtype == np.uint16:
        try:
            chars = "".join(chr(int(c)) for c in np.atleast_1d(data).flat if int(c) != 0)
            return chars
        except Exception:
            pass
    return data


def _loadmat_h5(path: Path) -> Dict[str, Any]:
    import h5py

    out: Dict[str, Any] = {}
    with h5py.File(str(path), "r") as f:
        for key in f.keys():
            out[key] = _h5_to_numpy(f, f[key])
    return out


def loadmat(path: Path) -> Dict[str, Any]:
    """Load a .mat file via scipy; fall back to h5py for MATLAB v7.3."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        return _loadmat_scipy(path)
    except NotImplementedError:
        return _loadmat_h5(path)
    except ValueError as e:
        # scipy raises ValueError for some v7.3 files
        msg = str(e).lower()
        if "hdf" in msg or "v7.3" in msg or "matlab 7.3" in msg:
            return _loadmat_h5(path)
        raise


def _get_top(d: Dict[str, Any], name: str) -> Any:
    if name in d:
        return d[name]
    # case-insensitive fallback
    lower = {k.lower(): k for k in d if not k.startswith("__")}
    if name.lower() in lower:
        return d[lower[name.lower()]]
    raise KeyError(f"Expected top-level key {name!r}; got {list(k for k in d if not k.startswith('__'))}")


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if _is_mat_struct(obj):
        if name in obj._fieldnames:
            return getattr(obj, name)
        # case-insensitive
        for f in obj._fieldnames:
            if f.lower() == name.lower():
                return getattr(obj, f)
        return default
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        for k, v in obj.items():
            if k.lower() == name.lower():
                return v
        return default
    return default


def _region_fields(obj: Any) -> List[str]:
    """Return sorted Region1..RegionN field names present on a struct/dict."""
    if _is_mat_struct(obj):
        names = list(obj._fieldnames)
    elif isinstance(obj, dict):
        names = list(obj.keys())
    else:
        return []
    regions = [n for n in names if n.lower().startswith("region") and n[6:].isdigit()]
    regions.sort(key=lambda n: int(n[6:]))
    return regions


# ---------------------------------------------------------------------------
# Reference dataclass
# ---------------------------------------------------------------------------


@dataclass
class Injuries:
    start_min: np.ndarray
    end_min: np.ndarray
    start_sec: np.ndarray
    end_sec: np.ndarray
    labels: List[str]
    n: int


@dataclass
class PlotProps:
    automated_region_bin_length: int = 7
    unif_p_thresh: float = 0.05
    correlogram_bin_max: float = 1.0
    number_of_correlogram_bins: int = 2001
    correlogram_smoothing_factor: float = 0.01
    sparse_correlogram_thresh: float = 0.0
    include_autocorrelograms_in_statistics: bool = False
    smoothing_window_size: int = 20
    max_peak_count_before_noise: int = 10
    raw: Any = None


@dataclass
class Reference:
    """Plain-numpy view of one recording's MATLAB reference outputs."""

    recording: str
    path: Path

    cell_ids: List[str] = field(default_factory=list)
    cell_display_names: List[str] = field(default_factory=list)
    rasters: List[np.ndarray] = field(default_factory=list)

    regions_min: Optional[np.ndarray] = None  # (n_regions, 2)
    regions_sec: Optional[np.ndarray] = None
    num_regions: int = 0

    # 0-based region index → (probs [n_bins, n_pairs], n_events [n_pairs], names [n_pairs])
    correlograms: Dict[int, Tuple[np.ndarray, np.ndarray, List[str]]] = field(
        default_factory=dict
    )
    correlogram_bins: Optional[np.ndarray] = None

    # 0-based region index → (p_values, uniform, leader_prob, n_peaks, peak_locations)
    metrics: Dict[int, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[Any]]] = (
        field(default_factory=dict)
    )

    bad_signals: Optional[np.ndarray] = None
    bad_regions_indicator: int = 0
    bad_regions: Any = None  # full struct; often only indicator when 0
    injuries: Optional[Injuries] = None
    plot_props: Optional[PlotProps] = None

    fs: Optional[float] = None
    end_time_s: Optional[float] = None
    end_timestamp: Optional[int] = None
    n_active_electrodes: Optional[int] = None
    n_total_electrodes: Optional[int] = None
    cell_count: Optional[int] = None
    n_bins: Optional[int] = None

    files_present: List[str] = field(default_factory=list)
    files_missing: List[str] = field(default_factory=list)
    load_warnings: List[str] = field(default_factory=list)

    # keep raw structs for later stages if needed
    _processed: Any = field(default=None, repr=False)
    _raw_data: Any = field(default=None, repr=False)
    _recording_metrics: Any = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# parsers
# ---------------------------------------------------------------------------

EXPECTED_FILES = [
    "AnalysisRegions.mat",
    "InjuryIndicies.mat",
    "badRegions.mat",
    "badSignals.mat",
    "plotProps.mat",
    "ProcessedData.mat",
    "RawData.mat",
    "Correlograms.mat",
    "RecordingMetrics.mat",
]


def _parse_plot_props(obj: Any) -> PlotProps:
    return PlotProps(
        automated_region_bin_length=int(_field(obj, "automatedRegionBinLength", 7)),
        unif_p_thresh=float(_field(obj, "unifPThresh", 0.05)),
        correlogram_bin_max=float(_field(obj, "correlogramBinMax", 1.0)),
        number_of_correlogram_bins=int(_field(obj, "numberOfCorrelogramBins", 2001)),
        correlogram_smoothing_factor=float(
            _field(obj, "correlogramSmoothingFactor", 0.01)
        ),
        sparse_correlogram_thresh=float(_field(obj, "sparseCorrelogramThresh", 0)),
        include_autocorrelograms_in_statistics=bool(
            int(_field(obj, "includeAutocorrelogramsInStatistics", 0))
        ),
        smoothing_window_size=int(_field(obj, "SmoothingWindowSize", 20)),
        max_peak_count_before_noise=int(_field(obj, "maxPeakCountBeforeNoise", 10)),
        raw=obj,
    )


def _parse_injuries(obj: Any) -> Injuries:
    def _arr(name: str) -> np.ndarray:
        v = _field(obj, name, np.asarray([]))
        if v is None:
            return np.asarray([], dtype=np.float64)
        if isinstance(v, (int, float, np.integer, np.floating)):
            return np.asarray([float(v)], dtype=np.float64)
        if isinstance(v, str):
            return np.asarray([], dtype=np.float64)
        return np.atleast_1d(np.asarray(v, dtype=np.float64)).astype(np.float64)

    labels_raw = _field(obj, "InjuryLabels", [])
    if isinstance(labels_raw, str):
        labels = [labels_raw]
    elif labels_raw is None or (isinstance(labels_raw, np.ndarray) and labels_raw.size == 0):
        labels = []
    else:
        labels = _as_1d_str_list(labels_raw)

    n = _field(obj, "NumberOfInjuriesOrTreatments", len(labels))
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = len(labels)

    return Injuries(
        start_min=_arr("InjuryStartMin"),
        end_min=_arr("InjuryEndMin"),
        start_sec=_arr("InjuryStartSec"),
        end_sec=_arr("InjuryEndSec"),
        labels=labels,
        n=n,
    )


def _parse_rasters(raster_obj: Any) -> List[np.ndarray]:
    if raster_obj is None:
        return []
    a = np.atleast_1d(np.asarray(raster_obj, dtype=object))
    out: List[np.ndarray] = []
    for item in a.flat:
        if item is None:
            out.append(np.asarray([], dtype=np.float64))
        elif isinstance(item, np.ndarray):
            out.append(np.asarray(item, dtype=np.float64).ravel())
        elif isinstance(item, (int, float, np.integer, np.floating)):
            out.append(np.asarray([float(item)], dtype=np.float64))
        else:
            out.append(np.asarray(item, dtype=np.float64).ravel())
    return out


def _parse_peak_locations(arr: Any) -> List[Any]:
    """Keep object array of per-pair peak location vectors as a Python list."""
    if arr is None:
        return []
    a = np.atleast_1d(np.asarray(arr, dtype=object))
    out = []
    for item in a.flat:
        if item is None:
            out.append(np.asarray([], dtype=np.float64))
        elif isinstance(item, np.ndarray):
            out.append(np.asarray(item, dtype=np.float64).ravel())
        elif isinstance(item, (int, float, np.integer, np.floating)):
            out.append(np.asarray([float(item)], dtype=np.float64))
        else:
            try:
                out.append(np.asarray(item, dtype=np.float64).ravel())
            except Exception:
                out.append(item)
    return out


def load_reference(recording: str, data_root: Optional[Union[str, Path]] = None) -> Reference:
    """Load all available reference .mat files for ``recording``.

    Missing Correlograms.mat / RecordingMetrics.mat do not abort the load;
    inventory still reports what exists.
    """
    if data_root is not None:
        ref_dir = Path(data_root) / "matlab_reference" / recording
    else:
        ref_dir = matlab_reference_dir(recording)

    if not ref_dir.is_dir():
        raise FileNotFoundError(
            f"MATLAB reference directory not found: {ref_dir}\n"
            f"Set MEA_MATLAB_DATA to the data root containing matlab_reference/."
        )

    ref = Reference(recording=recording, path=ref_dir)

    present = []
    missing = []
    for fname in EXPECTED_FILES:
        if (ref_dir / fname).is_file():
            present.append(fname)
        else:
            missing.append(fname)
    ref.files_present = present
    ref.files_missing = missing

    # --- badSignals ---
    if "badSignals.mat" in present:
        try:
            d = loadmat(ref_dir / "badSignals.mat")
            bs = _get_top(d, "badSignals")
            # may be bare array or struct
            if _is_mat_struct(bs):
                bs = _field(bs, "badSignals", bs)
            ref.bad_signals = np.asarray(bs).ravel()
        except Exception as e:
            ref.load_warnings.append(f"badSignals.mat: {e}")

    # --- badRegions ---
    if "badRegions.mat" in present:
        try:
            d = loadmat(ref_dir / "badRegions.mat")
            br = _get_top(d, "badRegions")
            ref.bad_regions = br
            ind = _field(br, "badRegionsIndicator", 0)
            ref.bad_regions_indicator = int(ind) if ind is not None else 0
        except Exception as e:
            ref.load_warnings.append(f"badRegions.mat: {e}")

    # --- AnalysisRegions ---
    if "AnalysisRegions.mat" in present:
        try:
            d = loadmat(ref_dir / "AnalysisRegions.mat")
            ar = _get_top(d, "AnalysisRegions")
            mins = _field(ar, "Minutes")
            secs = _field(ar, "Seconds")
            ref.regions_min = np.asarray(mins, dtype=np.float64)
            if ref.regions_min.ndim == 1:
                ref.regions_min = ref.regions_min.reshape(-1, 2)
            ref.regions_sec = np.asarray(secs, dtype=np.float64)
            if ref.regions_sec.ndim == 1:
                ref.regions_sec = ref.regions_sec.reshape(-1, 2)
            nr = _field(ar, "numRegions", ref.regions_min.shape[0])
            ref.num_regions = int(nr)
        except Exception as e:
            ref.load_warnings.append(f"AnalysisRegions.mat: {e}")

    # --- InjuryIndicies (MATLAB spelling) ---
    if "InjuryIndicies.mat" in present:
        try:
            d = loadmat(ref_dir / "InjuryIndicies.mat")
            inj = _get_top(d, "InjuryIndicies")
            ref.injuries = _parse_injuries(inj)
        except Exception as e:
            ref.load_warnings.append(f"InjuryIndicies.mat: {e}")

    # --- plotProps ---
    if "plotProps.mat" in present:
        try:
            d = loadmat(ref_dir / "plotProps.mat")
            pp = _get_top(d, "plotProps")
            ref.plot_props = _parse_plot_props(pp)
            ref.n_bins = ref.plot_props.number_of_correlogram_bins
        except Exception as e:
            ref.load_warnings.append(f"plotProps.mat: {e}")

    # --- ProcessedData ---
    if "ProcessedData.mat" in present:
        try:
            d = loadmat(ref_dir / "ProcessedData.mat")
            pd = _get_top(d, "ProcessedData")
            ref._processed = pd
            ref.cell_ids = _as_1d_str_list(_field(pd, "CellIDs"))
            ref.cell_display_names = _as_1d_str_list(_field(pd, "CellDisplayNames"))
            ref.rasters = _parse_rasters(_field(pd, "Raster"))
            cc = _field(pd, "CellCount", len(ref.cell_ids))
            ref.cell_count = int(cc) if cc is not None else len(ref.cell_ids)
            fs = _field(pd, "ExperimentSamplFreq")
            ref.fs = float(fs) if fs is not None else None
            et = _field(pd, "ExperimentEndTime")
            ref.end_time_s = float(et) if et is not None else None
            ets = _field(pd, "ExperimentEndTimestamp")
            ref.end_timestamp = int(ets) if ets is not None else None
            na = _field(pd, "NumberOfActiveElectrodes")
            ref.n_active_electrodes = int(na) if na is not None else None
            nt = _field(pd, "TotalNumberOfElectrodes")
            ref.n_total_electrodes = int(nt) if nt is not None else None
        except Exception as e:
            ref.load_warnings.append(f"ProcessedData.mat: {e}")

    # --- RawData (optional metadata) ---
    if "RawData.mat" in present:
        try:
            d = loadmat(ref_dir / "RawData.mat")
            rd = _get_top(d, "RawData")
            ref._raw_data = rd
            if ref.fs is None:
                adf = _field(rd, "ADFrequency")
                if adf is not None:
                    ref.fs = float(adf)
        except Exception as e:
            ref.load_warnings.append(f"RawData.mat: {e}")

    # --- Correlograms ---
    if "Correlograms.mat" in present:
        try:
            d = loadmat(ref_dir / "Correlograms.mat")
            C = _get_top(d, "Correlograms")
            bins = _field(C, "CorrelogramBins")
            if bins is not None:
                ref.correlogram_bins = np.asarray(bins, dtype=np.float64).ravel()
                ref.n_bins = int(ref.correlogram_bins.size)
            for rname in _region_fields(C):
                idx = int(rname[6:]) - 1  # Region1 → 0
                rstruct = _field(C, rname)
                probs = np.asarray(
                    _field(rstruct, "CorrelogramProbabilities"), dtype=np.float64
                )
                n_events = np.asarray(
                    _field(rstruct, "numberOfSpikesContributingToTheCorrelogram"),
                    dtype=np.float64,
                ).ravel()
                names = _as_1d_str_list(_field(rstruct, "ComparisonNames"))
                ref.correlograms[idx] = (probs, n_events, names)
        except Exception as e:
            ref.load_warnings.append(f"Correlograms.mat: {e}")

    # --- RecordingMetrics ---
    if "RecordingMetrics.mat" in present:
        try:
            d = loadmat(ref_dir / "RecordingMetrics.mat")
            RM = _get_top(d, "RecordingMetrics")
            ref._recording_metrics = RM
            CM = _field(RM, "CorrelogramMetrics")
            if CM is not None:
                for rname in _region_fields(CM):
                    idx = int(rname[6:]) - 1
                    rstruct = _field(CM, rname)
                    p_values = np.asarray(
                        _field(rstruct, "uniformityTestPValue"), dtype=np.float64
                    ).ravel()
                    uniform = np.asarray(
                        _field(rstruct, "uniformityTest"), dtype=np.uint8
                    ).ravel()
                    leader_prob = np.asarray(
                        _field(rstruct, "leaderProb"), dtype=np.float64
                    ).ravel()
                    n_peaks = np.asarray(
                        _field(rstruct, "numberOfCorrelogramPeaks"), dtype=np.int64
                    ).ravel()
                    peak_locations = _parse_peak_locations(
                        _field(rstruct, "correlogramPeakLocations")
                    )
                    ref.metrics[idx] = (
                        p_values,
                        uniform,
                        leader_prob,
                        n_peaks,
                        peak_locations,
                    )
        except Exception as e:
            ref.load_warnings.append(f"RecordingMetrics.mat: {e}")

    return ref


def inventory_text(ref: Reference) -> str:
    """Human-readable inventory for ``verify.py --stage ref``."""
    lines: List[str] = []
    lines.append(f"=== Reference inventory: {ref.recording} ===")
    lines.append(f"path: {ref.path}")
    lines.append(f"files present ({len(ref.files_present)}): {', '.join(ref.files_present)}")
    if ref.files_missing:
        lines.append(f"files missing ({len(ref.files_missing)}): {', '.join(ref.files_missing)}")
    if ref.load_warnings:
        lines.append("load warnings:")
        for w in ref.load_warnings:
            lines.append(f"  - {w}")

    n_units = ref.cell_count if ref.cell_count is not None else len(ref.cell_ids)
    lines.append("")
    lines.append("--- Units ---")
    lines.append(f"number of units: {n_units}")
    lines.append(f"CellIDs ({len(ref.cell_ids)}): {', '.join(ref.cell_ids)}")
    if ref.cell_display_names:
        lines.append(
            f"CellDisplayNames ({len(ref.cell_display_names)}): "
            f"{', '.join(ref.cell_display_names)}"
        )
    if ref.rasters:
        lengths = [len(r) for r in ref.rasters]
        lines.append(
            f"rasters: {len(ref.rasters)} arrays; "
            f"spike counts min/median/max="
            f"{min(lengths)}/{int(np.median(lengths))}/{max(lengths)}"
        )

    lines.append("")
    lines.append("--- Regions ---")
    lines.append(f"number of regions: {ref.num_regions}")
    if ref.regions_min is not None:
        lines.append("region bounds (minutes):")
        for i, (lo, hi) in enumerate(ref.regions_min):
            lines.append(f"  Region{i+1} (index {i}): [{lo}, {hi}] min")
    if ref.regions_sec is not None:
        lines.append("region bounds (seconds):")
        for i, (lo, hi) in enumerate(ref.regions_sec):
            lines.append(f"  Region{i+1} (index {i}): [{lo}, {hi}] s")

    lines.append("")
    lines.append("--- Correlograms (0-based region keys; Region1=0) ---")
    if not ref.correlograms:
        lines.append("(none loaded)")
    else:
        if ref.correlogram_bins is not None:
            lines.append(
                f"CorrelogramBins: n={ref.correlogram_bins.size}, "
                f"range=[{ref.correlogram_bins[0]}, {ref.correlogram_bins[-1]}]"
            )
        for idx in sorted(ref.correlograms):
            probs, n_events, names = ref.correlograms[idx]
            n_pairs = len(names) if names else (
                probs.shape[1] if probs.ndim == 2 else int(np.size(n_events))
            )
            lines.append(
                f"  Region{idx+1} (index {idx}): pairs={n_pairs}, "
                f"probs shape={getattr(probs, 'shape', None)}, "
                f"n_events shape={getattr(n_events, 'shape', None)}"
            )

    lines.append("")
    lines.append("--- Metrics (0-based region keys) ---")
    if not ref.metrics:
        lines.append("(none loaded)")
    else:
        for idx in sorted(ref.metrics):
            p_values, uniform, leader_prob, n_peaks, peak_locs = ref.metrics[idx]
            lines.append(
                f"  Region{idx+1} (index {idx}): "
                f"n={len(p_values)}, "
                f"uniform True={int(np.sum(uniform != 0))}/False={int(np.sum(uniform == 0))}, "
                f"n_peaks sum={int(np.sum(n_peaks))}"
            )

    lines.append("")
    lines.append("--- Saved human answers ---")
    if ref.bad_signals is not None:
        n_bad = int(np.sum(np.asarray(ref.bad_signals) != 0))
        lines.append(
            f"badSignals: shape={ref.bad_signals.shape}, dtype={ref.bad_signals.dtype}, "
            f"n_flagged={n_bad}, all_zero={n_bad == 0}"
        )
    else:
        lines.append("badSignals: (missing)")
    lines.append(f"badRegions.badRegionsIndicator: {ref.bad_regions_indicator}")
    if ref.bad_regions is not None and _is_mat_struct(ref.bad_regions):
        extra = [f for f in ref.bad_regions._fieldnames if f != "badRegionsIndicator"]
        if extra:
            lines.append(f"  additional badRegions fields: {extra}")
        else:
            lines.append(
                "  (no region table present when indicator=0 — only badRegionsIndicator)"
            )
    if ref.regions_min is not None:
        lines.append(
            f"AnalysisRegions: numRegions={ref.num_regions}, "
            f"Minutes shape={ref.regions_min.shape}, Seconds shape="
            f"{None if ref.regions_sec is None else ref.regions_sec.shape}"
        )
    if ref.injuries is not None:
        inj = ref.injuries
        lines.append(
            f"InjuryIndicies: n={inj.n}, labels={inj.labels}, "
            f"start_min={inj.start_min.tolist()}, end_min={inj.end_min.tolist()}, "
            f"start_sec={inj.start_sec.tolist()}, end_sec={inj.end_sec.tolist()}"
        )
    else:
        lines.append("InjuryIndicies: (missing)")

    lines.append("")
    lines.append("--- Recording facts ---")
    lines.append(f"fs (ExperimentSamplFreq): {ref.fs}")
    lines.append(f"duration / ExperimentEndTime (s): {ref.end_time_s}")
    lines.append(f"ExperimentEndTimestamp: {ref.end_timestamp}")
    lines.append(f"active electrodes: {ref.n_active_electrodes}")
    lines.append(f"total electrodes: {ref.n_total_electrodes}")
    lines.append(f"n_bins: {ref.n_bins}")
    if ref.plot_props is not None:
        pp = ref.plot_props
        lines.append(
            f"plotProps: bin_max={pp.correlogram_bin_max}, n_bins={pp.number_of_correlogram_bins}, "
            f"smooth_factor={pp.correlogram_smoothing_factor}, unif_p={pp.unif_p_thresh}, "
            f"region_len_min={pp.automated_region_bin_length}, "
            f"smooth_window={pp.smoothing_window_size}, "
            f"include_auto={pp.include_autocorrelograms_in_statistics}, "
            f"sparse_thresh={pp.sparse_correlogram_thresh}"
        )

    lines.append("")
    lines.append("=== end inventory ===")
    return "\n".join(lines)
