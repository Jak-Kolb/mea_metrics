"""mea_metrics: Python port of original_mea_matlab metrics pipeline."""

__version__ = "0.0.1"

from .matref import Reference, load_reference

__all__ = ["Reference", "load_reference", "__version__"]
