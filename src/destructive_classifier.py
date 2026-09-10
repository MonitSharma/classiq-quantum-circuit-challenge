"""Initial C-dagger-Z-C classifier harness.

This first version intentionally preserves the coordinate wires.  It computes
the exact logo predicate into q12 using an ESOP of the distinct row patterns,
then forms C^dagger Z C.  It is a correctness/serialization baseline for the
destructive-classifier direction, not an optimization result.

The next version will replace the row-pattern MCX expansion with destructive
register allocation and allow q[0:12] to become temporary nonlinear storage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import esop, row_terms


ROOT = Path(__file__).resolve().parents[1]
TARGET = 12
ALL_QUBITS = list(range(18))


def cube_controls(mask: int, value: int, offset: int) -> tuple[list[int], list[int]]:
    controls = [offset + bit for bit in range(6) if mask & (1 << bit)]
    negative = [offset + bit for bit in range(6)
                if mask & (1 << bit) and not (value & (1 << bit))]
    return controls, negative


def append_mcx(q: QuantumCircuit, controls: list[int], negative: list[int]) -> None:
    """Append an exact basis-state-controlled X with arbitrary dirty inputs."""
    if negative:
        q.x(negative)
    if not controls:
        q.x(TARGET)
    elif len(controls) == 1:
        q.cx(controls[0], TARGET)
    elif len(controls) == 2:
        q.ccx(controls[0], controls[1], TARGET)
    else:
        # This v0 deliberately uses Qiskit's exact no-ancilla synthesis.  The
        # later destructive compiler will replace this with phase-tolerant,
        # width-aware primitives.
        q.mcx(controls, TARGET, mode="noancilla")
    if negative:
        q.x(negative)


def build_classifier() -> QuantumCircuit:
    """Compute logo(x,y) into q12, restoring q13:q17 to zero."""
    q = QuantumCircuit(18)
    for x_table, y_table in row_terms():
        x_cubes = esop(x_table, 6)
        y_cubes = esop(y_table, 6)
        for x_mask, x_value in x_cubes:
            x_controls, x_negative = cube_controls(x_mask, x_value, 0)
            for y_mask, y_value in y_cubes:
                y_controls, y_negative = cube_controls(y_mask, y_value, 6)
                append_mcx(q, x_controls + y_controls,
                           x_negative + y_negative)
    return q


def build_oracle() -> QuantumCircuit:
    """Return the initial exact C^dagger-Z-C oracle candidate."""
    classifier = build_classifier()
    oracle = classifier.copy()
    oracle.z(TARGET)
    oracle.compose(classifier.inverse(), inplace=True)
    return transpile(oracle, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def main() -> None:
    classifier = transpile(build_classifier(), basis_gates=["u3", "cx"],
                           qubits_initially_zero=False, optimization_level=3)
    oracle = build_oracle()
    out = ROOT / "artifacts/destructive_classifier_v0.qasm"
    out.write_text(qasm2.dumps(oracle))
    metrics = {
        "candidate": str(out),
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "classifier_depth": classifier.depth(),
        "classifier_cx": classifier.count_ops().get("cx", 0),
        "oracle_depth": oracle.depth(),
        "oracle_cx": oracle.count_ops().get("cx", 0),
        "width": oracle.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "status": "pending_exhaustive_verification",
        "note": "v0 preserves inputs; destructive allocation is not implemented yet",
    }
    (ROOT / "artifacts/destructive_classifier_v0.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
