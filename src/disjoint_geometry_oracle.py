"""Compose the disjoint rectangle and disk phase components."""

import itertools
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from disjoint_rectangles import build as build_rectangle
from disk_only_mux import build as build_disk


def build(order=("A", "B_prime", "disk"), seed=0, raw_first=True):
    components = {
        "A": build_rectangle("A"),
        "B_prime": build_rectangle("B_prime"),
        "disk": build_disk(seed),
    }
    q = QuantumCircuit(18)
    for name in order:
        q.compose(components[name], inplace=True)
    if raw_first:
        return transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    return q


def main():
    rows = []
    for order in itertools.permutations(("A", "B_prime", "disk")):
        q = build(order, raw_first=True)
        rows.append({"mode": "raw_first", "order": order, "depth": q.depth(), "cx_count": q.count_ops().get("cx", 0), "width": q.num_qubits})
    best = min(rows, key=lambda r: (r["depth"], r["cx_count"]))
    q = build(best["order"], raw_first=True)
    path = Path(f"artifacts/disjoint_geometry_{best['depth']}.qasm")
    path.write_text(qasm2.dumps(q))
    Path("artifacts/disjoint_geometry_order_search.json").write_text(
        json.dumps({"trials": rows, "best": best, "qasm": str(path.resolve())}, indent=2) + "\n"
    )
    print(json.dumps({"best": best, "qasm": str(path.resolve())}, indent=2))


if __name__ == "__main__":
    main()
