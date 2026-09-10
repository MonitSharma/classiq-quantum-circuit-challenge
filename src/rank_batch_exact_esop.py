"""Three-term batch using exact no-ancilla MCX ESOP loaders."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import esop


def exact_pred(table, offset, target):
    q = QuantumCircuit(18)
    for mask, value in esop(table, 6):
        controls = [offset + bit for bit in range(6) if mask >> bit & 1]
        negative = [offset + bit for bit in range(6)
                    if (mask >> bit & 1) and not (value >> bit & 1)]
        q.x(negative)
        if controls:
            q.mcx(controls, target, mode="noancilla")
        else:
            q.x(target)
        q.x(negative)
    return q


def build(indices=(0, 1, 2), basis="rank_terms"):
    terms = json.loads(Path(f"artifacts/{basis}.json").read_text())
    q = QuantumCircuit(18)
    x_outputs, y_outputs = [12, 13, 14], [15, 16, 17]
    x_loads = [exact_pred(terms[i][0], 0, t) for i, t in zip(indices, x_outputs)]
    y_loads = [exact_pred(terms[i][1], 6, t) for i, t in zip(indices, y_outputs)]
    for load in x_loads + y_loads:
        q.compose(load, inplace=True)
    for x_wire, y_wire in zip(x_outputs, y_outputs):
        q.cz(x_wire, y_wire)
    for load in reversed(y_loads + x_loads):
        q.compose(load.inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


if __name__ == "__main__":
    out = build()
    path = Path("artifacts/rank_batch_exact_esop_012_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {"indices": (0, 1, 2), "depth": out.depth(),
               "cx": out.count_ops().get("cx", 0), "width": out.num_qubits,
               "qasm": str(path)}
    Path("artifacts/rank_batch_exact_esop_012_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))
