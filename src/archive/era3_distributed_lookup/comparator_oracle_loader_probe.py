"""Native probe for the exact y -> (b,m) code from comparator_oracle_structure.

This is deliberately a loader-only diagnostic.  It uses the repository's
relative-phase MCX helper with dirty x wires as temporary workspace, then
transpiles immediately with arbitrary-input semantics enabled.
"""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from comparator_oracle_structure import Y_B, Y_M
from search import pred, truth


def build_y_loader():
    q = QuantumCircuit(18)
    for target, values in zip(range(12, 16), (Y_B, *[Y_M] * 3)):
        source_bit = 0 if target == 12 else target - 13
        table = truth(y for y in range(64) if (values[y] >> source_bit) & 1)
        q.compose(pred(table, 6, target, [0, 1, 2, 3]), inplace=True)
    return q


def main():
    raw = build_y_loader()
    out = transpile(raw, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3,
                    seed_transpiler=0)
    directory = Path("artifacts/comparator_oracle/y_loader")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "y_loader_esop_probe.qasm"
    path.write_text(qasm2.dumps(out))
    metrics = {
        "qasm": str(path), "depth": out.depth(),
        "cx_count": out.count_ops().get("cx", 0),
        "width": out.num_qubits,
        "targets": "q12=b, q13..q15=m bits",
        "dirty_scratch": [0, 1, 2, 3],
        "qubits_initially_zero": False,
        "status": "loader-only native probe; not a complete oracle",
    }
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
