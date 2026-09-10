"""Direct ESOP-to-clean-output pair compiler using relative-phase MCX blocks."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import pred


def compile_pair(x, y):
    q = QuantumCircuit(18)
    q.compose(pred(x, 0, 12, [14, 15, 16, 17]), inplace=True)
    q.compose(pred(y, 6, 13, [14, 15, 16, 17]), inplace=True)
    q.cz(12, 13)
    q.compose(pred(y, 6, 13, [14, 15, 16, 17]).inverse(), inplace=True)
    q.compose(pred(x, 0, 12, [14, 15, 16, 17]).inverse(), inplace=True)
    return q


def main():
    terms = json.loads(Path("artifacts/pair_terms.json").read_text())
    q = QuantumCircuit(18)
    for x, y in terms:
        q.compose(compile_pair(x, y), inplace=True)
    out = transpile(q, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3)
    metrics = {"depth": out.depth(), "cx_count": out.count_ops().get("cx", 0),
               "width": out.num_qubits}
    Path("artifacts/dirty_esop_pair.qasm").write_text(qasm2.dumps(out))
    Path("artifacts/dirty_esop_pair_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
