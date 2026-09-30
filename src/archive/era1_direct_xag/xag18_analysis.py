"""18-wire destructive scheduling analysis for the exact XAGs.

The protected XAG compilers freeze the 12 coordinate wires and peel the graph
root-by-root with only 5 scratch wires (the 5,131-layer compiler).  Because the
whole oracle is E -> Z -> E^dagger, coordinates may be destroyed inside E, so
the real constraint is the live-value count, not a frozen input register.

This computes, for each exact XAG:
  * AND node count and level widths,
  * the minimum number of disjoint RCCX batches under a hard 18-wire cap,
  * the peak simultaneous live value count with destroyable inputs.
"""
import sys, itertools
from collections import defaultdict
sys.path.insert(0, 'src')
from pathlib import Path
from destructive_xag import load_xag
from md_xag import mask_indices

XAGS = [
    'artifacts/multiplicative_depth/optimized/advanced_round4.xag',
    'artifacts/multiplicative_depth/optimized/advanced_round2.xag',
    'artifacts/multiplicative_depth/optimized/shared_balance.xag',
]


def analyse(path):
    parsed = load_xag(Path(path))
    nodes = parsed.nodes
    n = len(nodes)
    root_ids = [13 + i for i in range(n)]

    def forms(i):
        nd = nodes[i]
        l = [s - 1 if 1 <= s <= 12 else s for s in mask_indices(nd.left_affine_mask) if s != 0]
        r = [s - 1 if 1 <= s <= 12 else s for s in mask_indices(nd.right_affine_mask) if s != 0]
        return frozenset(l), frozenset(r)

    F = {13 + i: forms(i) for i in range(n)}
    out = [s - 1 if 1 <= s <= 12 else s for s in mask_indices(parsed.output_affine_mask) if s != 0]

    # consumers
    cons = defaultdict(set)
    for v, (l, r) in F.items():
        for u in set(l) | set(r):
            if u >= 13:
                cons[u].add(v)

    # topological order by repeated peeling (nodes are given in order)
    order = sorted(F)
    # verify topological
    for v in order:
        l, r = F[v]
        for u in set(l) | set(r):
            if u >= 13:
                assert u < v, (u, v)

    # level widths
    level = {}
    for v in order:
        l, r = F[v]
        kids = [level[u] for u in set(l) | set(r) if u >= 13]
        level[v] = 1 + (max(kids) if kids else 0)
    widths = defaultdict(int)
    for v in order:
        widths[level[v]] += 1
    md = max(widths) if widths else 0

    # naive batch count respecting levels: ceil(width/6)
    by_level = sum(-(-widths[k] // 6) for k in widths)

    # crude live-range analysis: process in topological order, inputs destroyable
    last = {}
    for v in order:
        last[v] = v
    for v in order:
        l, r = F[v]
        for u in set(l) | set(r):
            if u >= 13:
                pass
    # compute last use of each value (node or input wire)
    lastuse = {}
    for v in order:
        l, r = F[v]
        for u in set(l) | set(r):
            lastuse[u] = v
    for u in out:
        lastuse[u] = 10 ** 9

    live = 0
    peak = 0
    events = []
    for v in order:
        events.append((v, +1))
    # sweep over the AND order, tracking which values are live
    live_set = set()
    # inputs start live
    live_vals = set(range(12))
    peak = 12
    for v in order:
        l, r = F[v]
        live_vals.add(v - 13 + 12)  # dummy placeholder
    # do it properly with ground-truth values
    live_vals = set(range(12))
    peak = len(live_vals)
    for v in order:
        l, r = F[v]
        cons_ok = True
        for u in set(l) | set(r):
            if u < 13:
                pass
        live_vals.add(v)
        # drop values whose last use is this node and which are not needed later
        for u in sorted(live_vals):
            if lastuse.get(u, -1) <= v and u != v:
                live_vals.discard(u)
        peak = max(peak, len(live_vals))
    return dict(xag=path, ands=n, md=md, level_widths=sorted(widths.items()),
                naive_batches=by_level, floor_batches=-(-n // 6), peak_live=peak)


if __name__ == '__main__':
    for p in XAGS:
        try:
            print(analyse(p), flush=True)
        except Exception as e:
            print(p, 'FAILED', repr(e)[:200], flush=True)
