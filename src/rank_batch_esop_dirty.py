"""Experimental three-term batch with five dirty scratch wires per output."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import pred


def build(indices=(0, 1, 2), basis="rank_terms"):
    terms = json.loads(Path(f"artifacts/{basis}.json").read_text())
    q = QuantumCircuit(18)
    outputs = [12, 13, 14, 15, 16, 17]
    x_out, y_out = outputs[:3], outputs[3:]
    for index, target in zip(indices, x_out):
        scratch = [wire for wire in outputs if wire != target]
        q.compose(pred(terms[index][0], 0, target, scratch), inplace=True)
    for index, target in zip(indices, y_out):
        scratch = [wire for wire in outputs if wire != target]
        q.compose(pred(terms[index][1], 6, target, scratch), inplace=True)
    for x_wire, y_wire in zip(x_out, y_out):
        q.cz(x_wire, y_wire)
    for index, target in reversed(list(zip(indices, y_out))):
        scratch = [wire for wire in outputs if wire != target]
        q.compose(pred(terms[index][1], 6, target, scratch).inverse(), inplace=True)
    for index, target in reversed(list(zip(indices, x_out))):
        scratch = [wire for wire in outputs if wire != target]
        q.compose(pred(terms[index][0], 0, target, scratch).inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


if __name__ == "__main__":
    out = build()
    path = Path("artifacts/rank_batch_esop_dirty_012_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {"indices": (0, 1, 2), "depth": out.depth(),
               "cx": out.count_ops().get("cx", 0), "width": out.num_qubits,
               "qasm": str(path)}
    Path("artifacts/rank_batch_esop_dirty_012_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))
