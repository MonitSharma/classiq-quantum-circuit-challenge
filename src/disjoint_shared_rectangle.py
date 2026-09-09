"""Rank-2 basis variant for the disjoint rectangle phase."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from disk_only_mux import build as build_disk
from pair_search import pair_circuit
from search import truth


def build_rectangle() -> QuantumCircuit:
    """Use an equivalent GL(2,2) basis for A XOR B'."""
    a_x = truth(range(2, 27))
    b_x = truth(range(27, 49))
    a_y = truth(range(29, 54))
    b_y = truth(range(39, 44))
    q = QuantumCircuit(18)
    # (A_x A_y) XOR (B_x B_y)
    # = A_x(A_y XOR B_y) XOR (A_x XOR B_x)B_y.
    for x_table, y_table in ((a_x, a_y ^ b_y), (a_x ^ b_x, b_y)):
        q.compose(pair_circuit(x_table, y_table), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)


def build(seed: int = 2) -> QuantumCircuit:
    q = QuantumCircuit(18)
    q.compose(build_rectangle(), inplace=True)
    q.compose(build_disk(seed), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)


def main() -> None:
    q = build(2)
    path = Path("artifacts/disjoint_shared_rectangle_candidate.qasm")
    path.write_text(qasm2.dumps(q))
    metrics = {"depth": q.depth(), "cx_count": q.count_ops().get("cx", 0), "width": q.num_qubits, "disk_seed": 2, "qasm": str(path.resolve())}
    Path("artifacts/disjoint_shared_rectangle_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
