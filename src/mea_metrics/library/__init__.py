"""Plan A metric library (rate/ISI → bursts/STTC).

A1: region-aligned rate + ISI table.
A2: + max-interval bursts, STTC, basic health, thin STTC-degree topology.
"""

from .table import build_a1_table, build_a2_table, write_a1_outputs, write_a2_outputs

__all__ = ["build_a1_table", "build_a2_table", "write_a1_outputs", "write_a2_outputs"]
