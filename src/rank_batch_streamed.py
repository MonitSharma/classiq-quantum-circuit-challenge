"""Five-factor x bank with one streamed y factor per phase interaction."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from search import pred


def build(indices=(0, 1, 2, 3, 4), basis="rank_terms", seed=20260909):
    terms = json.loads(Path(f"artifacts/{basis}.json").read_text())
    x_outputs = [12, 13, 14, 15, 16]
    y_target = 17
    x_bank = multiplexer([terms[i][0] for i in indices], x_outputs,
                         list(range(6)), "y", seed)
    q = QuantumCircuit(18)
    q.compose(x_bank, inplace=True)
    scratch = list(x_outputs)
    for index, x_wire in zip(indices, x_outputs):
        y_load = pred(terms[index][1], 6, y_target, scratch)
        q.compose(y_load, inplace=True)
        q.cz(x_wire, y_target)
        q.compose(y_load.inverse(), inplace=True)
    q.compose(x_bank.inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


if __name__ == "__main__":
    out = build()
    path = Path("artifacts/rank_batch_streamed_01234_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {"indices": (0, 1, 2, 3, 4), "depth": out.depth(),
               "cx": out.count_ops().get("cx", 0), "width": out.num_qubits,
               "qasm": str(path)}
    Path("artifacts/rank_batch_streamed_01234_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))
