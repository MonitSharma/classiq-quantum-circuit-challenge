"""Three-term 3+3 rank batch using synchronized uniformly controlled rotations."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer


def build(indices=(0, 1, 2), basis="rank_terms", seed=20260909):
    terms = json.loads(Path(f"artifacts/{basis}.json").read_text())
    x_tables = [terms[i][0] for i in indices]
    y_tables = [terms[i][1] for i in indices]
    x_bank = multiplexer(x_tables, [12, 13, 14], list(range(6)), "y", seed)
    y_bank = multiplexer(y_tables, [15, 16, 17], list(range(6, 12)), "y", seed + 1)
    q = QuantumCircuit(18)
    # x and y controls are disjoint, so the two banks can be scheduled in
    # parallel by the transpiler.  The UCR inverse restores clean ancillas.
    q.compose(x_bank, inplace=True)
    q.compose(y_bank, inplace=True)
    for x_wire, y_wire in zip((12, 13, 14), (15, 16, 17)):
        q.cz(x_wire, y_wire)
    q.compose(y_bank.inverse(), inplace=True)
    q.compose(x_bank.inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


if __name__ == "__main__":
    indices = (0, 1, 2)
    out = build(indices)
    path = Path("artifacts/rank_batch_ucr_012_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {"indices": indices, "basis": "rank_terms", "seed": 20260909,
               "depth": out.depth(), "cx": out.count_ops().get("cx", 0),
               "width": out.num_qubits, "qasm": str(path)}
    Path("artifacts/rank_batch_ucr_012_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))
