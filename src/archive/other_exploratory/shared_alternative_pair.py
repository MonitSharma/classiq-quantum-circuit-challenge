"""Joint two-root factor search with one shared reversible pebbling schedule."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from mcz import phase_cube
from xag import make_graph, plan, linear
from xag_phase import alternatives, phase_many


def build_joint(graph, choices):
    targets = tuple(f for forms in choices for f in forms)
    path = plan(graph, frozenset(), targets, max_states=50000)
    q = QuantumCircuit(18)
    wire = {v: v for v in range(12)}
    live = set()
    free = list(range(12, 18))

    def toggle(v):
        a, b = graph.nodes[v]
        pre, p, r = linear(q, a, b, wire)
        if v in live:
            t = wire[v]
        else:
            t = free.pop(0)
            wire[v] = t
        q.compose(pre, inplace=True)
        q.rccx(p, r, t)
        q.compose(pre.inverse(), inplace=True)
        if v in live:
            live.remove(v)
            free.append(wire.pop(v))
            free.sort()
        else:
            live.add(v)

    for v in path:
        toggle(v)
    for forms in choices:
        phase_many(q, forms, wire, free)
    for v in plan(graph, frozenset(live), [], max_states=50000):
        toggle(v)
    assert not live
    return transpile(
        q,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=3,
    )


def search_pair(terms, i, j):
    graph, roots = make_graph([terms[i], terms[j]])
    choices = [
        list(alternatives(graph, root, maxf=5))
        for root in roots
    ]
    best = None
    tested = 0
    for a in choices[0]:
        for b in choices[1]:
            try:
                q = build_joint(graph, [a, b])
            except (ValueError, IndexError):
                continue
            tested += 1
            score = (q.depth(), q.count_ops().get('cx', 0))
            if best is None or score < best[0]:
                best = (score, q, a, b)
                print('pair', i, j, 'tested', tested, 'best', score, flush=True)
    if best is None:
        raise ValueError('no jointly pebbleable alternatives')
    return best, tested


if __name__ == '__main__':
    terms = json.loads(Path('artifacts/rank_terms.json').read_text())
    best, tested = search_pair(terms, 1, 4)
    score, q, a, b = best
    print('final', score, 'tested', tested, flush=True)
    Path('artifacts/shared_alternative_pair_1_4.qasm').write_text(qasm2.dumps(q))
    Path('artifacts/shared_alternative_pair_1_4.meta.json').write_text(
        json.dumps({'terms': [1, 4], 'depth': score[0], 'cx': score[1], 'tested': tested}, indent=2)
    )
