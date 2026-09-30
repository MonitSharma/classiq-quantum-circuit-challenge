"""Feasibility of a two-frame distributed lookup: codes that ignore a coordinate.

`structured_ucry` needs four frames because, in frame `f`, host `i` can only
carry Walsh masks whose high part lies in `{shift_i, h_i ^ shift_i}`.  Running
only the first two frames restricts output `i` to masks whose high part lies in
`span{h_i, h_{i+1}}`, i.e. to code bits that do not depend on the transformed
coordinate `h_{i+2}` at all.  A loader built from two frames instead of four is
roughly half as deep, which is the largest single term in this oracle.

So the question is combinatorial: are there three independent directions
`v_0, v_1, v_2` and three loaded bits, with `g_i` invariant under `v_i`, whose
values together with one raw parity still determine the row (or column) class?
This module answers that with SAT, one instance per direction triple.
"""
import argparse
import itertools
import json
from pathlib import Path

from pysat.formula import IDPool
from pysat.solvers import Cadical153

from two_stage_oracle import ROWCLS, COLCLS


def independent(vectors):
    piv = {}
    for v in vectors:
        x = v
        while x:
            i = x.bit_length() - 1
            if i in piv:
                x ^= piv[i]
            else:
                piv[i] = x
                break
        else:
            return False
    return True


def conflict_pairs(cls, rho):
    pairs = []
    for a in range(64):
        for b in range(a + 1, 64):
            if cls[a] != cls[b] and ((a & rho).bit_count() & 1) == ((b & rho).bit_count() & 1):
                pairs.append((a, b))
    return pairs


def feasible(cls, rho, directions, pairs, solver_cls=Cadical153):
    """SAT: g_i invariant under directions[i], and the joint code separates classes."""
    pool = IDPool()

    def bit(i, v):
        # one variable per coset of {0, v_i}: invariance is enforced by naming
        rep = min(v, v ^ directions[i])
        return pool.id(('g', i, rep))

    clauses = []
    for a, b in pairs:
        lits = []
        for i in range(3):
            if bit(i, a) == bit(i, b):
                continue                      # this bit cannot separate the pair
            d = pool.id(('d', i, a, b))
            x, y = bit(i, a), bit(i, b)
            clauses += [[-d, x, y], [-d, -x, -y], [d, -x, y], [d, x, -y]]
            lits.append(d)
        if not lits:
            return None                       # pair unseparable for these directions
        clauses.append(lits)
    with solver_cls(bootstrap_with=clauses) as solver:
        if not solver.solve():
            return False
        model = set(l for l in solver.get_model() if l > 0)
        codes = []
        for v in range(64):
            codes.append(sum(((bit(i, v) in model) << i) for i in range(3)))
        seen = {}
        for v in range(64):
            key = (((v & rho).bit_count() & 1), codes[v])
            if seen.setdefault(key, cls[v]) != cls[v]:
                raise AssertionError('SAT model does not separate the classes')
        return codes


def scan(cls, rho, limit=None):
    pairs = conflict_pairs(cls, rho)
    triples = [t for t in itertools.combinations(range(1, 64), 3) if independent(t)]
    found, tested = [], 0
    for t in triples:
        tested += 1
        got = feasible(cls, rho, t, pairs)
        if got:
            found.append((list(t), got))
            if limit and len(found) >= limit:
                break
    return found, tested, len(triples)


def run(outdir, limit):
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, cls, rhos in (('y', ROWCLS, [32]), ('x', COLCLS, [16, 48, 6, 60])):
        entries = []
        for rho in rhos:
            found, tested, total = scan(cls, rho, limit)
            print(name, 'rho', rho, 'solutions', len(found), 'of', tested, 'tested /', total,
                  flush=True)
            for directions, codes in found:
                entries.append(dict(rho=rho, directions=directions, codes=codes))
        report[name] = entries
    (outdir / 'two_frame_codes.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--limit', type=int, default=40)
    a = p.parse_args()
    run(a.outdir, a.limit)
