"""Grouped y-cube phase synthesis with shared x-side factors."""

import collections
import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from factor import phase_cube, simplify
from search import esop, mcxr


def signed_cube(mask, value, offset=0):
    return tuple(offset + bit + 1 if value >> bit & 1 else -(offset + bit + 1)
                 for bit in range(6) if mask >> bit & 1)


def grouped_cubes(terms):
    groups = collections.defaultdict(set)
    for x_table, y_table in terms:
        for x_mask, x_value in esop(x_table, 6):
            x_cube = signed_cube(x_mask, x_value)
            for y_mask, y_value in esop(y_table, 6):
                key = (y_mask, y_value)
                groups[key].symmetric_difference_update((x_cube,))
    return {key: frozenset(value) for key, value in groups.items() if value}


def synth_controlled(cubes, seed=0):
    """Synthesize cubes that all include physical q17 as a phase control."""
    rng = random.Random(seed)
    q = QuantumCircuit(18)

    def recurse(current, free):
        current = set(simplify(current))
        small = [cube for cube in current if len(cube) <= 2]
        rng.shuffle(small)
        for cube in small:
            phase_cube(q, frozenset(cube), free)
            current.remove(cube)
        if not current:
            return
        if not free:
            for cube in sorted(current, key=len):
                phase_cube(q, frozenset(cube), free)
            return
        pairs = collections.Counter(
            pair for cube in current for pair in __import__("itertools").combinations(
                sorted(cube), 2
            )
        )
        options = []
        for pair, count in pairs.items():
            covered = [cube for cube in current if set(pair) <= cube]
            score = (count - 1) * 2 + sum(len(cube) - 2 for cube in covered) * 0.15
            if seed:
                score *= rng.uniform(0.6, 1.4)
            options.append((score, pair, covered))
        if not options:
            for cube in sorted(current, key=len):
                phase_cube(q, frozenset(cube), free)
            return
        _, pair, covered = max(options, key=lambda row: row[0])
        rest = current - set(covered)
        target = free[0]
        pre = QuantumCircuit(18)
        negative = [abs(literal) - 1 for literal in pair if literal < 0]
        if negative:
            pre.x(negative)
        pre.rccx(abs(pair[0]) - 1, abs(pair[1]) - 1, target - 1)
        if negative:
            pre.x(negative)
        q.compose(pre, inplace=True)
        recurse({frozenset(set(cube) - set(pair)) | {target}
                 for cube in covered}, free[1:])
        q.compose(pre.inverse(), inplace=True)
        recurse(rest, free)

    recurse(cubes, [13, 14, 15, 16, 17])
    return q


def y_compute(mask, value):
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


def build(seed=0):
    terms = json.loads(Path("artifacts/rank_terms.json").read_text())
    groups = grouped_cubes(terms)
    q = QuantumCircuit(18)
    for (y_mask, y_value), x_cubes in sorted(groups.items()):
        q.compose(y_compute(y_mask, y_value), inplace=True)
        controlled = {frozenset((*x_cube, 18)) for x_cube in x_cubes}
        q.compose(synth_controlled(controlled, seed), inplace=True)
        q.compose(y_compute(y_mask, y_value).inverse(), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed), groups


if __name__ == "__main__":
    out, groups = build()
    path = Path("artifacts/shared_y_phase_grouped_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics = {"depth": out.depth(), "cx": out.count_ops().get("cx", 0),
               "width": out.num_qubits, "phase_cubes": sum(map(len, groups.values())),
               "distinct_y_cubes": len(groups), "qasm": str(path)}
    Path("artifacts/shared_y_phase_grouped_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))
