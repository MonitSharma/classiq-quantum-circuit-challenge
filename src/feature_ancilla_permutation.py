"""Search feature-to-ancilla assignments in the verified full-mux skeleton.

The logical outputs are ``R0, R1, R2, A, B, V``.  The phase term in the
original skeleton uses the third radius wire as its carry target and the V
wire as a control; both are remapped here.  This is an architectural search,
not a replacement for exhaustive verification of the serialized winner.
"""

import itertools
import json
import time
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from full_mux import multiplexer
from mcz import phase_cube
from pair_search import pair_circuit
from radius import R, radius, truth


FEATURES = tuple(range(12, 18))


def build(assignment, seed=94):
    r0, r1, r2, a, b, v = assignment
    lookup = multiplexer(
        R + [truth(range(29, 54)), truth(range(39, 44)),
             truth(y for y in range(64) if radius(y) > 0)],
        list(assignment), list(range(6, 12)), "y", seed
    )
    q = lookup.copy()
    xs, xb = truth(range(2, 27)), truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(v, a)
    q.cx(v, b)
    q.compose(multiplexer([xs, xb, xo], [a, b, v], list(range(6)), "z",
                          seed + 10000), inplace=True)
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
    q.compose(lookup.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def search():
    best = None
    rows = []
    started = time.time()
    for assignment in itertools.permutations(FEATURES):
        q = build(assignment)
        row = (q.depth(), q.count_ops().get("cx", 0), assignment)
        rows.append(row)
        if best is None or row[:2] < best[:2]:
            best = row
    rows.sort()
    return best, rows, time.time() - started


if __name__ == "__main__":
    best, rows, elapsed = search()
    depth, cx, assignment = best
    out = Path("artifacts/530/full_mux_feature_permuted_530.qasm")
    out.write_text(qasm2.dumps(build(assignment)))
    Path("artifacts/530/feature_permutation_search.json").write_text(
        json.dumps({
            "tested": len(rows),
            "elapsed_seconds": elapsed,
            "best": {"depth": depth, "cx_count": cx,
                     "width": 18, "assignment": list(assignment),
                     "qasm": str(out.resolve())},
            "top30": [{"depth": d, "cx_count": c,
                       "assignment": list(a)} for d, c, a in rows[:30]],
        }, indent=2) + "\n"
    )
    print(json.dumps({"depth": depth, "cx_count": cx,
                      "assignment": list(assignment),
                      "elapsed_seconds": elapsed}, indent=2))
