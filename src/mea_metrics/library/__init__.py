"""Plan A metric library (rate/ISI → bursts/STTC).

A1: region-aligned rate + ISI table.
A2: bursts + STTC (stubs for now).
"""

from .table import build_a1_table, write_a1_outputs

__all__ = ["build_a1_table", "write_a1_outputs"]
