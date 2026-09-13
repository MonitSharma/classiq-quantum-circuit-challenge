"""Are there class codes cheap enough to compute with logic instead of a lookup?

The whole remaining cost of the 196 oracle is the loader: a three-output,
six-address controlled-Ry lookup, whose 174 Walsh terms force about 77 layers
however it is scheduled.  A lookup is only necessary because the code bits are
arbitrary functions of the coordinate.  If instead each loaded bit were a
Boolean polynomial of low degree with few monomials, it could be computed
directly into the clean ancilla with a handful of relative-phase Toffolis --
tens of layers rather than 77, and the compute/uncompute pair cancels the
relative phases exactly because the kernel between them is diagonal.

So the question is: do three bounded-degree polynomials of the coordinate,
together with one raw parity, still determine the row (or column) class?
Evaluating an ANF is linear in its coefficients, so `g(u) ^ g(v)` is a parity of
a known subset of the coefficient variables, and the whole question is SAT:
for every pair of coordinates in the same raw fiber whose classes differ, at
least one of the three bits must differ.
"""
import argparse
import itertools
import json
from pathlib import Path

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical153

from two_stage_oracle import ROWCLS, COLCLS


def monomials(degree, nvars=6):
    out = []
    for size in range(degree + 1):
        for combo in itertools.combinations(range(nvars), size):
            out.append(sum(1 << i for i in combo))
    return out


def evaluate(mask, value):
    return int(mask & ~value == 0)


def build(cls, rho, degree, pool):
    """Clauses for: three degree-bounded bits separate every conflicting pair."""
    mons = monomials(degree)
    coef = [[pool.id(('c', i, m)) for m in mons] for i in range(3)]
    clauses = []
    for a in range(64):
        for b in range(a + 1, 64):
            if cls[a] == cls[b]:
                continue
            if ((a & rho).bit_count() & 1) != ((b & rho).bit_count() & 1):
                continue
            support = [j for j, m in enumerate(mons)
                       if evaluate(m, a) != evaluate(m, b)]
            if not support:
                return None, None, None        # pair indistinguishable at this degree
            lits = []
            for i in range(3):
                # Tseitin chain for the parity of coef[i][j] over j in support
                acc = coef[i][support[0]]
                for j in support[1:]:
                    nxt = pool.id(('x', i, a, b, j))
                    p, q = acc, coef[i][j]
                    clauses += [[-nxt, p, q], [-nxt, -p, -q], [nxt, -p, q], [nxt, p, -q]]
                    acc = nxt
                lits.append(acc)
            clauses.append(lits)
    return clauses, coef, mons


def decode(model, coef, mons, index):
    chosen = [mons[j] for j, v in enumerate(coef[index]) if v in model]
    return chosen


def solve(cls, rho, degree, budget=None):
    pool = IDPool()
    clauses, coef, mons = build(cls, rho, degree, pool)
    if clauses is None:
        return None
    if budget is not None:
        nonlinear = [coef[i][j] for i in range(3) for j, m in enumerate(mons)
                     if m.bit_count() >= 2]
        card = CardEnc.atmost(lits=nonlinear, bound=budget, vpool=pool,
                              encoding=EncType.seqcounter)
        clauses = clauses + card.clauses
    with Cadical153(bootstrap_with=clauses) as solver:
        if not solver.solve():
            return False
        model = set(l for l in solver.get_model() if l > 0)
        bits = [decode(model, coef, mons, i) for i in range(3)]
        codes = []
        for v in range(64):
            code = ((v & rho).bit_count() & 1)
            for i in range(3):
                code |= (sum(evaluate(m, v) for m in bits[i]) & 1) << (i + 1)
            codes.append(code)
        seen = {}
        for v in range(64):
            if seen.setdefault(codes[v], cls[v]) != cls[v]:
                raise AssertionError('recovered code does not determine the class')
        return dict(rho=rho, degree=degree, monomials=[[hex(m) for m in b] for b in bits],
                    nonlinear=sum(1 for b in bits for m in b if m.bit_count() >= 2),
                    codes=codes)


def run(outdir, degrees, rhos_y, rhos_x):
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, cls, rhos in (('y', ROWCLS, rhos_y), ('x', COLCLS, rhos_x)):
        found = []
        for degree in degrees:
            for rho in rhos:
                got = solve(cls, rho, degree)
                print(name, 'degree', degree, 'rho', rho,
                      'SAT' if got else ('UNSAT' if got is False else 'pair-blocked'),
                      flush=True)
                if got:
                    best = got
                    for budget in range(got['nonlinear'] - 1, -1, -1):
                        tighter = solve(cls, rho, degree, budget)
                        if not tighter:
                            break
                        best = tighter
                        print('   tightened to', budget, 'nonlinear monomials', flush=True)
                    found.append(best)
            if found:
                break
        report[name] = found
    (outdir / 'low_degree_codes.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--degrees', type=int, nargs='+', default=[2, 3, 4])
    a = p.parse_args()
    run(a.outdir, a.degrees, [32], [16, 48])
