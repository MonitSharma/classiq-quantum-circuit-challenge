"""Bounded diagnostic: compose raw pair/XAG blocks before one global rebase."""

from xag_phase import *
import mcz
import xag_phase

xag_phase.phase_cube = mcz.phase_cube


def best_raw_pair(x, y):
    """Choose a pair construction by its local exact U3/CX depth, return raw QASM circuit."""
    graph, roots = make_graph([(x, y)])
    best = None
    best_depth = 10**9
    for forms in alternatives(graph, roots[0], maxf=5):
        try:
            path = plan(graph, frozenset(), forms, max_states=10000)
            raw = make_one(graph, forms, path)
            compiled = transpile(
                raw,
                basis_gates=['u3', 'cx'],
                qubits_initially_zero=False,
                optimization_level=3,
            )
        except (ValueError, IndexError):
            continue
        if compiled.depth() < best_depth:
            best_depth = compiled.depth()
            best = raw
    if best is None:
        raise ValueError(f'no pair construction for {(x, y)}')
    return best, best_depth


def build(terms):
    raw = QuantumCircuit(18)
    local_depths = []
    for x, y in terms:
        pair, depth = best_raw_pair(x, y)
        raw.compose(pair, inplace=True)
        local_depths.append(depth)
    compiled = transpile(
        raw,
        basis_gates=['u3', 'cx'],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    return compiled, local_depths


if __name__ == '__main__':
    import json
    from pathlib import Path

    terms = json.loads(Path('artifacts/rank_terms.json').read_text())
    q, local = build(terms)
    print('local sum', sum(local), 'global', q.depth(), q.count_ops(), flush=True)
    Path('artifacts/global_pair_raw.qasm').write_text(qasm2.dumps(q))
    Path('artifacts/global_pair_raw.meta.json').write_text(
        json.dumps({'local_pair_depths': local, 'depth': q.depth(), 'cx': q.count_ops().get('cx', 0)}, indent=2)
    )
