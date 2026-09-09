"""Phase blocks for the disjoint square and corrected bar."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2

from pair_search import pair_circuit
from search import truth


RECTANGLES = {
    "A": (truth(range(2, 27)), truth(range(29, 54))),
    "B_prime": (truth(range(27, 49)), truth(range(39, 44))),
}


def build(name: str) -> QuantumCircuit:
    """Return an exact phase oracle for one rectangle."""
    x_table, y_table = RECTANGLES[name]
    return pair_circuit(x_table, y_table)


def rectangle_truth(name: str, x: int, y: int) -> bool:
    x_table, y_table = RECTANGLES[name]
    return bool((x_table >> x) & 1) and bool((y_table >> y) & 1)


def main() -> None:
    metrics = {}
    for name in RECTANGLES:
        q = build(name)
        path = Path(f"artifacts/disjoint_rectangle_{name}.qasm")
        path.write_text(qasm2.dumps(q))
        metrics[name] = {
            "depth": q.depth(),
            "cx_count": q.count_ops().get("cx", 0),
            "width": q.num_qubits,
            "qasm": str(path.resolve()),
        }
    Path("artifacts/disjoint_rectangle_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
