"""Test deriving V=R1 OR R2 instead of loading V with a sixth UCR."""

from pathlib import Path
import random
import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from radius import R, radius, truth
from mcz import phase_cube
from pair_search import pair_circuit


def multiplexer(tables, outputs, controls, axis, seed=0):
    n = len(controls)
    count = 1 << n
    rng = random.Random(seed)
    base = list(range(n))
    rng.shuffle(base)
    shifts = list(range(n))
    rng.shuffle(shifts)
    orders = [base[s:] + base[:s] for s in shifts[:len(tables)]]
    coefficients = []
    for table, order in zip(tables, orders):
        values = np.array([
            np.pi * ((table >> sum(((k >> j) & 1) << v
                                   for j, v in enumerate(order))) & 1)
            for k in range(count)
        ])
        h = 1
        while h < count:
            for i in range(0, count, 2 * h):
                low = values[i:i + h].copy()
                high = values[i + h:i + 2 * h].copy()
                values[i:i + h] = low + high
                values[i + h:i + 2 * h] = low - high
            h *= 2
        coefficients.append(values / count)
    q = QuantumCircuit(18)
    for index in range(count):
        for coefficient, target in zip(coefficients, outputs):
            angle = float(coefficient[index ^ (index >> 1)])
            if abs(angle) > 1e-14:
                q.ry(angle, target) if axis == "y" else q.rz(angle, target)
        position = ((index + 1) & -(index + 1)).bit_length() - 1 \
            if index < count - 1 else n - 1
        for order, target in zip(orders, outputs):
            q.cx(controls[order[position]], target)
    return q


def build(seed=0, x_seed=None, relative_or=False):
    a = truth(range(29, 54))
    b = truth(range(39, 44))
    lookup = multiplexer(R + [a, b], list(range(12, 17)),
                         list(range(6, 12)), "y", seed)
    q = lookup.copy()

    # q17 is clean after the five-output lookup.
    q.cx(13, 17)
    q.cx(14, 17)
    (q.rccx if relative_or else q.ccx)(13, 14, 17)

    xs = truth(range(2, 27))
    xb = truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(17, 15)
    q.cx(17, 16)
    left = multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)),
                       "z", seed + 10000 if x_seed is None else x_seed)
    q.compose(left, inplace=True)
    q.z(17)
    q.cx(17, 16)
    q.cx(17, 15)

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
    phase_cube(q, frozenset([18, 6, 5, 15]), [])
    q.x(4)
    q.cx(11, 4)
    q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True)

    # Clear V, then reverse the five-output lookup.
    (q.rccx if relative_or else q.ccx)(13, 14, 17)
    q.cx(14, 17)
    q.cx(13, 17)
    q.compose(lookup.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def main():
    best = None
    for seed in range(32):
        q = build(seed)
        score = (q.depth(), q.count_ops().get("cx", 0))
        print(seed, score, flush=True)
        if best is None or score < best[0]:
            best = (score, q, seed)
    score, q, seed = best
    path = Path("artifacts/full_mux_derive_v.qasm")
    path.write_text(qasm2.dumps(q))
    Path("artifacts/full_mux_derive_v.metrics.json").write_text(
        '{\n'
        f'  "seed": {seed},\n  "depth": {score[0]},\n'
        f'  "cx": {score[1]},\n  "width": {q.num_qubits}\n'
        '}\n'
    )
    print({"seed": seed, "depth": score[0], "cx": score[1], "width": q.num_qubits})


if __name__ == "__main__":
    main()
