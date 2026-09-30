"""Compile an exact logo XAG using a heuristic clean-node pebble plan.

Two corrections to `src/xag_to_inplace_layers.py`, whose 5,131-layer result closed
this route:

1. **No accumulator.** The output is an affine form
   `f = c XOR (linear in coordinates) XOR (sum of AND roots)`, so the constant is
   a global phase, each linear term is a Z on a coordinate wire costing no CX, and
   each root only needs a Z while it happens to be live. Nothing is collected into
   one bit, so the whole circuit is one pebbling pass rather than `E Z E-dagger`.
2. **One shared pass.** Root cones overlap heavily -- for `advanced_round4` they
   sum to 134 nodes against 62 distinct gates -- so the roots are visited without
   clearing the board in between.

The planner may release a value whose operands are available and recompute it
later. Matched compute/release operations see the same logical controls and
opposite target transitions; their relative phases cancel. Intervening gates
need not be diagonal. Emitted oracles still require quantum verification.

This compiler freezes twelve input wires, leaving six clean nodes at width18.
Larger limits are width-ineligible diagnostics, not challenge candidates.
"""
import argparse
import itertools
import json
import math
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from destructive_xag import load_xag
from md_xag import mask_indices
from xag_to_inplace_layers import XAGGraph, make_toggle

ROOT = Path(__file__).resolve().parents[1]


def output_parts(parsed):
    bits = mask_indices(parsed.output_affine_mask)
    return ([s for s in bits if s >= 13],
            [s - 1 for s in bits if 1 <= s <= 12],
            0 in bits)


def predecessors(graph):
    return {v: sorted({u for f in graph.nodes[v] for u in f if u >= 13})
            for v in graph.nodes}


def plan(graph, roots, limit, order=None, rng=None):
    """Toggle sequence visiting every root with at most `limit` values live.

    A value may be released whenever its own operands are still on the board, so
    releases are not restricted to the most recent value: everything a value
    depends on was placed before it, and is still there unless it was released
    itself, in which case it is simply recomputed. Among the releasable values
    the scheduler prefers ones nothing on the board still depends on, then the
    one whose next use is farthest away.
    """
    preds = predecessors(graph)
    users = {v: set() for v in graph.nodes}
    for v, ps in preds.items():
        for u in ps:
            users[u].add(v)
    order = list(order or roots)
    board = set()
    ops = []
    marks = []
    rng = rng or random.Random(0)

    def releasable(v, pinned):
        return v not in pinned and all(u in board for u in preds[v])

    def pick(cands):
        free = [v for v in cands if not (users[v] & board)]
        pool = free or cands
        return max(pool, key=lambda v: (len(preds[v]), v))

    def make_room(pinned, depth=0):
        guard = 0
        while len(board) >= limit:
            guard += 1
            if guard > 5000:
                raise ValueError('release did not converge')
            cands = [v for v in board if releasable(v, pinned)]
            if cands:
                victim = pick(cands)
                ops.append(victim)
                board.discard(victim)
                continue
            # nothing is releasable: recompute a missing operand of some value
            if depth > 40:
                raise ValueError('release recursion too deep')
            options = [v for v in board if v not in pinned]
            if not options:
                raise ValueError('every value is pinned')
            v = min(options, key=lambda v: sum(1 for u in preds[v] if u not in board))
            missing = next(u for u in preds[v] if u not in board)
            ensure(missing, pinned | {v}, depth + 1)

    def ensure(v, pinned, depth=0):
        if v in board:
            return
        if depth > 400:
            raise ValueError('recursion too deep')
        held = set()
        for u in preds[v]:
            ensure(u, pinned | held, depth + 1)
            held.add(u)
        make_room(pinned | held)
        ops.append(v)
        board.add(v)

    for r in order:
        ensure(r, set())
        marks.append(len(ops))

    guard = 0
    while board:
        guard += 1
        if guard > 20000:
            raise ValueError('clearing did not converge')
        cands = [v for v in board if not (users[v] & board) and releasable(v, set())]
        if cands:
            victim = pick(cands)
            ops.append(victim)
            board.discard(victim)
            continue
        stuck = [v for v in board if not (users[v] & board)]
        if not stuck:
            raise ValueError('board has a dependency cycle')
        v = stuck[0]
        missing = next(u for u in preds[v] if u not in board)
        ensure(missing, {v})
    return ops, marks


def build(parsed, limit, order=None):
    roots, linear, constant = output_parts(parsed)
    graph = XAGGraph(parsed.nodes)
    ops, marks = plan(graph, roots, limit, order)
    # Larger limits are diagnostic only and cannot be challenge submissions.
    qc = QuantumCircuit(max(18,12+limit))
    if constant:
        qc.global_phase += math.pi
    for w in linear:
        qc.z(w)
    wire = {i: i for i in range(12)}
    live = set()
    free = list(range(12, 12 + limit))
    toggle = make_toggle(parsed.nodes, qc, wire, live, free)
    phase_at = {marks[i]: (order or roots)[i] for i in range(len(marks))}
    for step, v in enumerate(ops, start=1):
        toggle(v)
        if step in phase_at:
            qc.z(wire[phase_at[step]])
    assert not live, live
    return qc, len(ops)


def search(path, limit, seeds=24, seed=0):
    parsed = load_xag(Path(path))
    roots, _, _ = output_parts(parsed)
    graph = XAGGraph(parsed.nodes)
    cones = {r: graph.ancestors([{r}]) for r in roots}
    rng = random.Random(seed)
    orders = [list(roots), sorted(roots, key=lambda r: len(cones[r])),
              sorted(roots, key=lambda r: -len(cones[r]))]
    for start in roots:
        chain, rest = [start], [r for r in roots if r != start]
        while rest:
            nxt = max(rest, key=lambda r: len(cones[r] & cones[chain[-1]]))
            chain.append(nxt)
            rest.remove(nxt)
        orders.append(chain)
    for _ in range(seeds):
        shuffled = list(roots)
        rng.shuffle(shuffled)
        orders.append(shuffled)
    best = None
    for order in orders:
        try:
            qc, n = build(parsed, limit, order)
        except (ValueError, RecursionError):
            continue
        from distributed_frame_search import native as lower_native
        native = lower_native(qc)
        key = (native.depth(), native.count_ops().get('cx', 0))
        if best is None or key < best[0]:
            best = (key, native, order, n)
    return best


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--xag', type=Path,
                   default=ROOT / 'artifacts/multiplicative_depth/optimized/shared_balance.xag')
    p.add_argument('--limit', type=int, default=6)
    p.add_argument('--seeds', type=int, default=24)
    p.add_argument('--outdir', type=Path)
    a = p.parse_args()
    best = search(a.xag, a.limit, a.seeds)
    if best is None:
        raise SystemExit(json.dumps(dict(xag=str(a.xag), limit=a.limit,
                                         result='heuristic planner found no schedule at this budget')))
    (depth, cx), native, order, toggles = best
    print(json.dumps(dict(xag=str(a.xag), limit=a.limit, depth=depth, cx=cx,
                          toggles=toggles, and_gates=len(parsed_nodes)
                          if False else len(load_xag(a.xag).nodes))))
    if a.outdir:
        a.outdir.mkdir(parents=True, exist_ok=True)
        path = a.outdir / ('xag_pebble_d%d.qasm' % depth)
        path.write_text(qasm2.dumps(native))
        print('wrote', path)
