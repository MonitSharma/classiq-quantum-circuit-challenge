"""Comparator-free threshold-shell experiment.

This candidate is deliberately separate from ``full_mux`` and ``shell_mux``.
It stores operation-specific radius flags, uses the folded x bits to select
distance shells directly, and represents the radius-8 D2 points explicitly.
The exact exported QASM must be exhaustively verified before being considered.
"""

from pathlib import Path
import random

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from mcz import phase_cube
from search import truth
from radius import radius


def feature_table(predicate):
    return truth(y for y in range(64) if predicate(y))


def threshold_tables():
    """Return V,L,T,P,E tables over the six y bits."""
    return [
        feature_table(lambda y: radius(y) > 0),
        feature_table(lambda y: radius(y) >= 4),
        feature_table(lambda y: radius(y) >= 6),
        feature_table(lambda y: radius(y) & 1),
        feature_table(lambda y: 17 <= y <= 21),
    ]


def exact_bits(value, positions):
    """Signed cube for selected bit positions equal to ``value``."""
    return [
        pos + 1 if (value >> bit) & 1 else -(pos + 1)
        for bit, pos in enumerate(positions)
    ]


def branch_cube(y5, b3, magnitude, feature_controls):
    """Cube for one folded-distance branch and feature condition."""
    # The phase guard is x5=1 and x4==y5.  The folded low bits encode the
    # magnitude differently on each side of the two disk centers.
    cube = [6]  # x5
    cube.append(12 if y5 else -12)  # y5
    cube.append(5 if y5 else -5)  # x4 == y5
    cube.append(4 if b3 else -4)  # folded x3 branch
    cube.extend(exact_bits(magnitude, [0, 1, 2]))
    cube.extend(feature_controls)
    return cube


def disk_phase(q):
    """Apply the exact disk phase using threshold-controlled shells.

    After the existing fold, the guarded x region has these distance maps:

      either y5,b3=0: d=m+1       either y5,b3=1: d=m

    The threshold flags encode the radius test by distance shell.  The terms
    are disjoint in the folded-coordinate portion; the three ESOP terms for
    T OR P are parity-equivalent on every valid feature row.
    """
    # Feature controls are q12=V, q13=L, q14=T, q15=P, q16=E.
    for d in range(8):
        if d <= 2:
            conditions = [[13]]  # V
        elif d <= 4:
            conditions = [[14]]  # L
        elif d == 5:
            # T OR P = T XOR P XOR (T AND P).
            conditions = [[15], [16], [15, 16]]
        elif d == 6:
            conditions = [[15]]  # T
        else:
            conditions = [[15, 16]]  # T AND P

        branches = []
        branches.append((0, 1, d))
        branches.append((1, 1, d))
        if d >= 1:
            branches.append((0, 0, d - 1))
            branches.append((1, 0, d - 1))
        for y5, b3, magnitude in branches:
            for condition in conditions:
                phase_cube(q, frozenset(branch_cube(y5, b3, magnitude, condition)), [])

    # The only d=8 points are the left edge of the D2 guard, selected by E.
    phase_cube(q, frozenset(branch_cube(0, 0, 7, [17])), [])
    # x=48 is the right boundary excluded by the ordinary x4==y5 guard;
    # retain it as the second exact radius-eight point.
    phase_cube(q, frozenset([6, -12, 5, -4, 1, 2, 3, 17]), [])


def build(seed=0):
    # Load threshold features, apply the shell phase, then clear them before
    # reusing q15..q17 for the left-shape phase.
    thresholds = multiplexer(threshold_tables(), list(range(12, 17)), list(range(6, 12)), 'y', seed)
    q = thresholds.copy()

    fold = QuantumCircuit(18)
    for k in range(4):
        fold.cx(11, k)
    fold.x(3)
    for k in range(3):
        fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)
    disk_phase(q)
    q.compose(fold.inverse(), inplace=True)
    q.compose(thresholds.inverse(), inplace=True)

    # Load the already-transformed left flags directly.  q15=A xor V and
    # q16=B xor V; q17=V.  This removes the four temporary CNOTs in full_mux.
    a = feature_table(lambda y: 29 <= y <= 53)
    b = feature_table(lambda y: 39 <= y <= 43)
    v = threshold_tables()[0]
    av = a ^ v
    bv = b ^ v
    left_load = multiplexer([av, bv, v], [15, 16, 17], list(range(6, 12)), 'y', seed + 100)
    q.compose(left_load, inplace=True)

    xs = truth(range(2, 27))
    xb = truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    left_phase = multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)), 'z', seed + 10000)
    q.compose(left_phase, inplace=True)
    q.z(17)
    q.compose(left_load.inverse(), inplace=True)

    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                      optimization_level=3, seed_transpiler=seed)


if __name__ == '__main__':
    best = None
    for seed in range(1, 5):
        candidate = build(seed)
        print(seed, candidate.depth(), candidate.count_ops(), flush=True)
        if best is None or (candidate.depth(), candidate.count_ops().get('cx', 0)) < (best.depth(), best.count_ops().get('cx', 0)):
            best = candidate
            Path(f'artifacts/threshold_shell_seed{seed}.qasm').write_text(qasm2.dumps(candidate))
