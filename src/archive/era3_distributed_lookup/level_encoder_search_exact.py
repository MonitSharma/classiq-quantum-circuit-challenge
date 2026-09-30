"""Exact small-operand beam search for level encoders.

This is a companion to ``level_encoder_search.py``.  It keeps the original
stochastic search unchanged, but enumerates every XOR of up to three current
registers (and its complement) at each expansion.  The first exact separating
triple is promoted immediately, so a successful result is not lost to the
heuristic residual ranking.
"""
import json
import sys
import time
from itertools import combinations
from pathlib import Path

from level_encoder_search import FULL, NESTED, VARS, reduce_basis, residual, separating_triples
from level_oracle import small_decompose


def operand_family(regs):
    vals = {0, FULL}
    for n in (1, 2, 3):
        for idxs in combinations(range(9), n):
            v = 0
            for i in idxs:
                v ^= regs[i]
            vals.add(v)
            vals.add(v ^ FULL)
    return vals


def completion_score(regs, subsets, triples):
    """Return (residual score, separating triple or None)."""
    piv = reduce_basis(list(regs) + [FULL])
    weights = [residual(v, piv).bit_count() for v in subsets]
    best = 10**9
    best_trip = None
    for a, b, c in triples:
        s = weights[a] + weights[b] + weights[c]
        if s < best:
            best, best_trip = s, (a, b, c)
            if s == 0:
                return 0, best_trip
    return best, best_trip


def search(name, seed, limit, beam=12, max_ands=12):
    # seed is retained in the interface for comparable artifact names.
    del seed
    levels = [sum(1 for s in NESTED[name] if t in s) for t in range(64)]
    indicators = [sum(1 << t for t in range(64) if levels[t] == k) for k in range(6)]
    subsets = [sum(indicators[k] for k in range(6) if S >> k & 1) for S in range(64)]
    triples = separating_triples()
    start = tuple(VARS + [0, 0, 0])
    initial, _ = completion_score(start, subsets, triples)
    states = [(initial, start, ())]
    began = time.time()
    for step in range(max_ands):
        cand = {}
        for _, regs, hist in states:
            ops = sorted(operand_family(regs))
            products = {}
            for ia, a in enumerate(ops):
                for b in ops[ia:]:
                    p = a & b
                    if p not in (0, FULL):
                        products.setdefault(p, (a, b))
            for p, pair in products.items():
                # Replacing any register by reg xor p has the same linear
                # span, but the replayability constraint depends on the host.
                span_regs = list(regs)
                span_regs[0] ^= p
                value, trip = completion_score(tuple(span_regs), subsets, triples)
                valid_hosts = []
                for k in range(9):
                    # The semantic product is useful only if emit_encoder can
                    # reconstruct both operands without using the target wire.
                    if (small_decompose(pair[0], regs, avoid=(k,)) is None or
                            small_decompose(pair[1], regs, avoid=(k,)) is None):
                        continue
                    valid_hosts.append(k)
                for k in valid_hosts:
                    nxt = list(regs)
                    nxt[k] ^= p
                    nxt = tuple(nxt)
                    if value == 0:
                        return dict(name=name, ands=step + 1, triple=list(trip),
                                    hist=[list(h) for h in hist] + [[pair[0], pair[1], k]])
                    key = tuple(sorted(nxt))
                    old = cand.get(key)
                    if old is None or value < old[0]:
                        # Find one operand pair that realizes p for replay.
                        cand[key] = (value, nxt, hist + ((pair[0], pair[1], k),))
            if time.time() - began > limit:
                return None
        if not cand:
            return None
        states = sorted(cand.values(), key=lambda z: z[0])[:beam]
        print(f"{name} exact ands={step + 1} residual={states[0][0]} "
              f"states={len(states)} t={time.time() - began:.0f}s", flush=True)
        if time.time() - began > limit:
            return None
    return None


if __name__ == "__main__":
    name = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else 1200
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path("artifacts/level_nets_exact")
    result = search(name, seed, limit)
    if result is None:
        raise SystemExit("no replayable separating network found within the limit")
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"net_{name}_{seed}.json"
    path.write_text(json.dumps(result, indent=2))
    print("wrote", path)
