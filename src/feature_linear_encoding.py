"""Compile the winning affine encoding of the six full-mux features.

The loader computes G=M F, where F=(R0,R1,R2,A,B,V), then decodes F before
the existing comparator/phase construction.  The same decode is reversed
before loader.inverse(), so the encoded loader remains an exact compute /
phase / uncompute construction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from radius import R, radius
from search import truth
from mcz import phase_cube
from pair_search import pair_circuit


ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT = (12, 15, 14, 16, 17, 13)
MATRIX = (1, 23, 4, 8, 17, 32)
Y_ORDERS_SEED = 94
X_ORDERS_SEED = 10094
TRANSPILE_SEED = 94


def inverse_matrix(rows: tuple[int, ...], n: int = 6) -> tuple[int, ...]:
    left, right = list(rows), [1 << i for i in range(n)]
    for bit in range(n):
        pivot = next(i for i in range(bit, n) if left[i] & (1 << bit))
        left[bit], left[pivot] = left[pivot], left[bit]
        right[bit], right[pivot] = right[pivot], right[bit]
        for i in range(n):
            if i != bit and left[i] & (1 << bit):
                left[i] ^= left[bit]
                right[i] ^= right[bit]
    return tuple(right)


def matrix_ops(rows: tuple[int, ...], n: int = 6) -> list[tuple[int, int]]:
    """Return CNOTs mapping a wire vector to ``rows * vector`` over GF(2)."""
    work = list(rows)
    reduction: list[tuple[int, int]] = []
    for bit in range(n):
        pivot = next(i for i in range(bit, n) if work[i] & (1 << bit))
        if pivot != bit:
            reduction.extend(((pivot, bit), (bit, pivot), (pivot, bit)))
            work[pivot], work[bit] = work[bit], work[pivot]
        for i in range(n):
            if i != bit and work[i] & (1 << bit):
                reduction.append((bit, i))
                work[i] ^= work[bit]
    return list(reversed(reduction))


def encoded_tables() -> list[int]:
    features = R + [
        truth(range(29, 54)),
        truth(range(39, 44)),
        truth(y for y in range(64) if radius(y) > 0),
    ]
    return [
        __import__("functools").reduce(
            int.__xor__,
            (features[i] for i in range(6) if row & (1 << i)),
            0,
        )
        for row in MATRIX
    ]


def build() -> QuantumCircuit:
    r0, r1, r2, a, b, v = ASSIGNMENT
    tables = encoded_tables()
    lookup = multiplexer(tables, list(ASSIGNMENT), list(range(6, 12)), "y",
                         Y_ORDERS_SEED)
    q = lookup.copy()

    inverse = inverse_matrix(MATRIX)
    for control, target in matrix_ops(inverse):
        q.cx(ASSIGNMENT[control], ASSIGNMENT[target])

    xs, xb = truth(range(2, 27)), truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(v, a)
    q.cx(v, b)
    q.compose(multiplexer([xs, xb, xo], [a, b, v], list(range(6)), "z",
                          X_ORDERS_SEED), inplace=True)
    q.z(v)
    q.cx(v, b)
    q.cx(v, a)

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
    for i, wire in enumerate((r0, r1, r2)):
        comp.cx(wire, i)
        comp.cx(wire, carry)
        comp.rccx(carry, i, wire)
        carry = wire
    q.compose(comp, inplace=True)
    q.cx(11, 4)
    q.x(4)
    phase_cube(q, frozenset([v + 1, 6, 5, r2 + 1]), [])
    q.x(4)
    q.cx(11, 4)
    q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True)

    for control, target in reversed(matrix_ops(inverse)):
        q.cx(ASSIGNMENT[control], ASSIGNMENT[target])
    q.compose(lookup.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=TRANSPILE_SEED)


def main() -> None:
    circuit = build()
    out = ROOT / "artifacts/528/full_mux_feature_linear_528.qasm"
    out.parent.mkdir(exist_ok=True)
    out.write_text(qasm2.dumps(circuit))
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    metrics = {
        "qasm": str(out), "sha256": sha, "depth": circuit.depth(),
        "cx": circuit.count_ops().get("cx", 0), "width": circuit.num_qubits,
        "matrix_rows": list(MATRIX), "assignment": list(ASSIGNMENT),
        "qubits_initially_zero": False,
        "status": "pending_exhaustive_verification",
    }
    (out.parent / "feature_linear_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
