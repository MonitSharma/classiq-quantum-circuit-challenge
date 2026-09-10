"""Measure strict baseline costs for the semantic feature mappings.

This is a strict reference, not a claim of semantic synthesis: it compiles
the existing Walsh multiplexer for each selected output subset and reports the
cost that a care-set replacement must beat.  A semantic backend can consume
the mappings emitted by semantic_window.py later.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import transpile

from full_mux import multiplexer
from search import truth
from radius import R, radius
import bqskit


FEATURES = {
    "R0": R[0], "R1": R[1], "R2": R[2],
    "A": truth(range(29, 54)), "B": truth(range(39, 44)),
    "V": truth(y for y in range(64) if radius(y) > 0),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    groups = [("R0", "R1"), ("R1", "R2"), ("A", "B"), ("A", "B", "V")]
    rows = []
    for names in groups:
        tables = [FEATURES[name] for name in names]
        outputs = list(range(12, 12 + len(names)))
        circuit = multiplexer(tables, outputs, list(range(6, 12)), "y", seed=94)
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             optimization_level=3, qubits_initially_zero=False)
        rows.append({"features": list(names), "depth": compiled.depth(),
                     "cx": compiled.count_ops().get("cx", 0),
                     "width": compiled.num_qubits,
                     "mode": "strict_walsh_reference",
                     "semantic_synthesis": "not_attempted_bqskit_1.2.1_available"})
    args.output.write_text(json.dumps({"rows": rows}, indent=2) + "\n")
    print(json.dumps({"rows": rows}, indent=2))


if __name__ == "__main__":
    main()
