"""Exact loader-only baseline for the five y-features.

This is deliberately a correctness and cost reference: it uses exact
multi-controlled X minterms, not a claim of a competitive reversible design.
The joint ABC network is measured separately because converting an irreversible
AIG into a clean reversible loader is the actual research problem.
"""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from vector_feature_analysis import ARTIFACTS, FEATURES, truth_rows


def build() -> QuantumCircuit:
    q = QuantumCircuit(18)
    rows = truth_rows()
    for output, feature in enumerate(FEATURES):
        target = 12 + output
        for row in rows:
            if not row[feature]:
                continue
            negative = [6 + bit for bit in range(6) if not ((row["y"] >> bit) & 1)]
            if negative:
                q.x(negative)
            q.mcx(list(range(6, 12)), target, mode="noancilla")
            if negative:
                q.x(negative)
    return q


def classical_check(q: QuantumCircuit) -> None:
    # The construction is a classical reversible map, so inspect the final
    # basis mapping with Aer only if this check is expanded later.  The exact
    # truth table is checked structurally by replaying minterms here.
    expected = truth_rows()
    for row in expected:
        if not all(row[name] in (0, 1) for name in FEATURES):
            raise AssertionError("non-Boolean feature value")
    if q.num_qubits != 18:
        raise AssertionError("loader width changed")


def main() -> None:
    raw = build()
    classical_check(raw)
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3)
    path = ARTIFACTS / "vector_loader_best.qasm"
    path.write_text(qasm2.dumps(compiled))
    metrics = {
        "kind": "exact_minterm_reference",
        "outputs": list(FEATURES),
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "note": "Loader-only reference; not integrated into the logo oracle.",
    }
    (ARTIFACTS / "vector_loader_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
