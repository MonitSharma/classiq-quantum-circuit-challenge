"""Disk-only C XOR D oracle using only the three radius lookup outputs."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from mcz import phase_cube
from pair_search import pair_circuit
from radius import R, radius
from search import truth


def derive_v() -> QuantumCircuit:
    """Compute V=R1 OR R2 from q13 and q14 into clean q17."""
    q = QuantumCircuit(18)
    q.cx(13, 17)
    q.cx(14, 17)
    q.ccx(13, 14, 17)
    return q


def build(seed: int = 0, optimization_level: int = 3) -> QuantumCircuit:
    """Build C XOR D, leaving q0..q11 unchanged and q12..q17 clean."""
    assert all((radius(y) > 0) == bool(((radius(y) >> 1) & 1) or ((radius(y) >> 2) & 1))
               for y in range(64))

    lookup = multiplexer(R, [12, 13, 14], list(range(6, 12)), "y", seed)
    q = lookup.copy()
    q.compose(derive_v(), inplace=True)

    # Trusted fold and comparator from full_mux.py.
    fold = QuantumCircuit(18)
    for k in range(4):
        fold.cx(11, k)
    fold.x(3)
    for k in range(3):
        fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)

    comp = QuantumCircuit(18)
    comp.x([0, 1, 2])
    carry = 3
    for i in range(3):
        comp.cx(12 + i, i)
        comp.cx(12 + i, carry)
        comp.rccx(carry, i, 12 + i)
        carry = 12 + i
    q.compose(comp, inplace=True)

    q.cx(11, 4)
    q.x(4)
    # q17=V, q5=x5, q4=(x4 XOR x5) after the fold, q14=comparison carry.
    # q15/q16 are free in this architecture; a clean helper lowers the
    # four-control phase depth without changing the compute/uncompute proof.
    phase_cube(q, frozenset([18, 6, 5, 15]), [16])
    q.x(4)
    q.cx(11, 4)

    q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True)
    q.compose(derive_v().inverse(), inplace=True)
    q.compose(lookup.inverse(), inplace=True)

    # radius() uses 7 for the radius-8 rows; restore the exact boundary.
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(
        q,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=optimization_level,
    )


def main() -> None:
    rows = []
    for seed in range(8):
        q = build(seed)
        rows.append({"seed": seed, "depth": q.depth(), "cx_count": q.count_ops().get("cx", 0), "width": q.num_qubits})
        print(rows[-1], flush=True)
    best = min(rows, key=lambda r: (r["depth"], r["cx_count"]))
    q = build(best["seed"])
    path = Path("artifacts/disk_only_mux.qasm")
    path.write_text(qasm2.dumps(q))
    Path("artifacts/disk_only_mux_metrics.json").write_text(
        json.dumps({"trials": rows, "best": best, "qasm": str(path.resolve())}, indent=2) + "\n"
    )
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
