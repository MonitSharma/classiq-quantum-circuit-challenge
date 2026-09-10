"""Share repeated y-side ESOP cubes in a direct bilinear phase oracle.

The rank-factor expansion contains repeated y cubes.  This compiler computes
one y cube into q17, applies every associated x-side phase cube while q17 is
live, and then uncomputes q17.  Relative-phase compute is safe here because
the same compute is inverted around the diagonal phase block.
"""

import collections
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from mcz import phase_cube
from search import esop, mcxr


def signed_cube(mask, value, offset=0):
    return tuple(
        offset + bit + 1 if value >> bit & 1 else -(offset + bit + 1)
        for bit in range(6) if mask >> bit & 1
    )


def grouped_cubes(terms):
    """Return y-cube -> parity set of x-cubes for the bilinear expansion."""
    groups = collections.defaultdict(set)
    for x_table, y_table in terms:
        for x_mask, x_value in esop(x_table, 6):
            x_cube = signed_cube(x_mask, x_value, 0)
            for y_mask, y_value in esop(y_table, 6):
                y_cube = (y_mask, y_value)
                if x_cube in groups[y_cube]:
                    groups[y_cube].remove(x_cube)
                else:
                    groups[y_cube].add(x_cube)
    return {key: frozenset(value) for key, value in groups.items() if value}


def y_compute(mask, value):
    """Compute one six-input y monomial into q17, restoring q12..q16."""
    q = QuantumCircuit(18)
    controls = [6 + bit for bit in range(6) if mask >> bit & 1]
    negative = [6 + bit for bit in range(6)
                if (mask >> bit & 1) and not (value >> bit & 1)]
    if negative:
        q.x(negative)
    mcxr(q, controls, 17, [12, 13, 14, 15, 16])
    if negative:
        q.x(negative)
    return q


def x_compute(mask, value):
    """Compute one six-input x monomial into q17, restoring q12..q16."""
    q = QuantumCircuit(18)
    controls = [bit for bit in range(6) if mask >> bit & 1]
    negative = [bit for bit in range(6)
                if (mask >> bit & 1) and not (value >> bit & 1)]
    if negative:
        q.x(negative)
    mcxr(q, controls, 17, [12, 13, 14, 15, 16])
    if negative:
        q.x(negative)
    return q


def grouped_x_cubes(terms):
    """Return x-cube -> parity set of y-cubes for the transposed schedule."""
    groups = collections.defaultdict(set)
    for x_table, y_table in terms:
        for x_mask, x_value in esop(x_table, 6):
            x_cube = (x_mask, x_value)
            for y_mask, y_value in esop(y_table, 6):
                y_cube = signed_cube(y_mask, y_value, 6)
                if y_cube in groups[x_cube]:
                    groups[x_cube].remove(y_cube)
                else:
                    groups[x_cube].add(y_cube)
    return {key: frozenset(value) for key, value in groups.items() if value}


def build(seed=0):
    terms = json.loads(Path("artifacts/rank_terms.json").read_text())
    groups = grouped_cubes(terms)
    q = QuantumCircuit(18)
    for (y_mask, y_value), x_cubes in sorted(groups.items()):
        load = y_compute(y_mask, y_value)
        q.compose(load, inplace=True)
        for x_cube in sorted(x_cubes, key=lambda cube: (len(cube), cube)):
            phase_cube(q, frozenset((*x_cube, 18)), [])
        q.compose(load.inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed), groups


def build_transposed(seed=0):
    terms = json.loads(Path("artifacts/rank_terms.json").read_text())
    groups = grouped_x_cubes(terms)
    q = QuantumCircuit(18)
    for (x_mask, x_value), y_cubes in sorted(groups.items()):
        load = x_compute(x_mask, x_value)
        q.compose(load, inplace=True)
        for y_cube in sorted(y_cubes, key=lambda cube: (len(cube), cube)):
            phase_cube(q, frozenset((*y_cube, 18)), [])
        q.compose(load.inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed), groups


def main():
    out, groups = build()
    path = Path("artifacts/shared_y_phase_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {
        "depth": out.depth(),
        "cx": out.count_ops().get("cx", 0),
        "width": out.num_qubits,
        "rank_terms": 10,
        "phase_cubes": sum(len(cubes) for cubes in groups.values()),
        "distinct_y_cubes": len(groups),
        "qasm": str(path),
    }
    Path("artifacts/shared_y_phase_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))

    transposed, x_groups = build_transposed()
    transposed_path = Path("artifacts/shared_x_phase_development.qasm")
    transposed_path.write_text(qasm2.dumps(transposed))
    transposed_metrics = {
        "depth": transposed.depth(),
        "cx": transposed.count_ops().get("cx", 0),
        "width": transposed.num_qubits,
        "phase_cubes": sum(len(cubes) for cubes in x_groups.values()),
        "distinct_x_cubes": len(x_groups),
        "qasm": str(transposed_path),
    }
    Path("artifacts/shared_x_phase_development.metrics.json").write_text(
        json.dumps(transposed_metrics, indent=2)
    )
    print(json.dumps(transposed_metrics, indent=2))


if __name__ == "__main__":
    main()
