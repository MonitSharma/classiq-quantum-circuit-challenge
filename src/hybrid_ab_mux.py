"""Hybrid candidate with direct clean computations for A and B indicators."""

from pathlib import Path
from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from pair_search import pair_circuit
from pebble import smart_compute
from formula import formula, remap
from radius import R, radius
from search import truth
from mcz import phase_cube


def build(seed=94):
    a = truth(range(29, 54)); b = truth(range(39, 44))
    v = truth(y for y in range(64) if radius(y) > 0)
    direct_a = QuantumCircuit(18)
    smart_compute(direct_a, remap(formula(a, 6), range(6, 12)), 15, [12, 13, 14, 16])
    direct_b = QuantumCircuit(18)
    smart_compute(direct_b, remap(formula(b, 6), range(6, 12)), 16, [12, 13, 14])
    radius_load = multiplexer(R + [v], [12, 13, 14, 17], list(range(6, 12)), 'y', seed)
    q = QuantumCircuit(18)
    q.compose(direct_a, inplace=True); q.compose(direct_b, inplace=True)
    q.compose(radius_load, inplace=True)
    xs = truth(range(2, 27)); xb = truth(range(27, 49)); xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(17, 15); q.cx(17, 16)
    q.compose(multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)), 'z', seed + 10000), inplace=True)
    q.z(17); q.cx(17, 16); q.cx(17, 15)
    fold = QuantumCircuit(18)
    for k in range(4): fold.cx(11, k)
    fold.x(3)
    for k in range(3): fold.cx(3, k)
    fold.x(3); q.compose(fold, inplace=True)
    comp = QuantumCircuit(18); comp.x([0, 1, 2]); carry = 3
    for i in range(3):
        comp.cx(12 + i, i); comp.cx(12 + i, carry); comp.rccx(carry, i, 12 + i); carry = 12 + i
    q.compose(comp, inplace=True); q.cx(11, 4); q.x(4)
    phase_cube(q, frozenset([18, 6, 5, 15]), [])
    q.x(4); q.cx(11, 4); q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True); q.compose(radius_load.inverse(), inplace=True)
    q.compose(direct_b.inverse(), inplace=True); q.compose(direct_a.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                     optimization_level=3, seed_transpiler=seed)


if __name__ == '__main__':
    best = None
    for seed in range(8):
        q = build(seed); score = (q.depth(), q.count_ops().get('cx', 0)); print(seed, score, flush=True)
        if best is None or score < best[0]: best = (score, q)
    Path('artifacts/hybrid_ab_mux.qasm').write_text(qasm2.dumps(best[1]))
    print('best', best[0], flush=True)
