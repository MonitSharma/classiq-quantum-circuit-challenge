"""Sparse-Walsh UCR variant for the affine feature architecture.

The ordinary multiplexer emits every edge of the 64-vertex Gray cycle even
when a Walsh coefficient is zero.  This module visits only nonzero vertices,
uses the Hamming-path CNOTs between them, and closes the walk at zero.  It is
algebraically the same uniformly controlled rotation; the complete result is
still verified from serialized QASM.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

import feature_linear_encoding as base


def _coefficients(table: int, order: list[int], n: int) -> np.ndarray:
    size = 1 << n
    values = np.array([
        math.pi * ((table >> sum(((k >> j) & 1) << v
                                 for j, v in enumerate(order))) & 1)
        for k in range(size)
    ], dtype=float)
    h = 1
    while h < size:
        for i in range(0, size, 2 * h):
            lo = values[i:i + h].copy()
            hi = values[i + h:i + 2 * h].copy()
            values[i:i + h] = lo + hi
            values[i + h:i + 2 * h] = lo - hi
        h *= 2
    return values / size


def sparse_multiplexer(tables, outputs, controls, axis, seed=0):
    n = len(controls)
    size = 1 << n
    rng = random.Random(seed)
    base_order = list(range(n))
    rng.shuffle(base_order)
    shifts = list(range(n))
    rng.shuffle(shifts)
    orders = [base_order[s:] + base_order[:s]
              for s in shifts[:len(tables)]]

    schedules = []
    for table, order, target in zip(tables, orders, outputs):
        coeff = _coefficients(table, order, n)
        vertices = [j ^ (j >> 1) for j in range(size)
                    if abs(float(coeff[j ^ (j >> 1)])) > 1e-14]
        current = 0
        schedule = []
        for vertex in vertices:
            delta = current ^ vertex
            for bit in range(n):
                if delta & (1 << bit):
                    schedule.append(("cx", controls[order[bit]], target))
            angle = float(coeff[vertex])
            schedule.append((axis, angle, target))
            current = vertex
        for bit in range(n):
            if current & (1 << bit):
                schedule.append(("cx", controls[order[bit]], target))
        schedules.append(schedule)

    # Interleave the independent output paths.  Each path's order is fixed;
    # Qiskit's DAG depth calculation then parallelizes operations on disjoint
    # wires even though they are appended in this deterministic round order.
    q = QuantumCircuit(18)
    positions = [0] * len(schedules)
    while any(pos < len(schedule)
              for pos, schedule in zip(positions, schedules)):
        for index, schedule in enumerate(schedules):
            if positions[index] >= len(schedule):
                continue
            kind, first, second = schedule[positions[index]]
            if kind == "cx":
                q.cx(first, second)
            elif kind == "y":
                q.ry(first, second)
            else:
                q.rz(first, second)
            positions[index] += 1
    return q


def build():
    original = base.multiplexer
    base.multiplexer = sparse_multiplexer
    try:
        return base.build()
    finally:
        base.multiplexer = original


def main() -> None:
    raw = build()
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3,
                         seed_transpiler=base.TRANSPILE_SEED)
    out = Path("artifacts/sparse/full_mux_feature_linear_sparse.qasm")
    out.parent.mkdir(exist_ok=True)
    out.write_text(qasm2.dumps(compiled))
    print({"qasm": str(out), "depth": compiled.depth(),
           "cx": compiled.count_ops().get("cx", 0),
           "width": compiled.num_qubits})


if __name__ == "__main__":
    main()
