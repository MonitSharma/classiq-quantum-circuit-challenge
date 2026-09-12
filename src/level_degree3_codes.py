"""Exact degree-3 level-code construction.

For each encoder, find three Boolean polynomials of degree at most three such
that codeword sets for different level classes are disjoint.  A level may use
several codewords; this is the register-saving split described in
LEVEL_COMPARATOR.md.

The model is linear/XOR-CNF: polynomial evaluations are XOR clauses and the
inequality conditions are three-literal clauses over auxiliary parity outputs.
Every returned model is checked directly against the 64-point truth tables.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

from pysat.solvers import Solver

FULL = (1 << 64) - 1
MONOMIALS = [m for d in range(4) for m in range(64) if m.bit_count() == d]


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    "u1": [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    "v1": [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    "u2": [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    "v2": [
        _rng(2, 61),
        _rng(2, 26) | _rng(50, 60),
        _rng(2, 26) | _rng(51, 59),
        _rng(2, 26) | _rng(53, 57),
        _rng(2, 26),
    ],
}


class CNF:
    def __init__(self):
        self.solver = Solver(name="cadical195")
        self.next_var = 0

    def var(self):
        self.next_var += 1
        return self.next_var

    def xor(self, variables, rhs):
        variables = [v for v in variables if v]
        if not variables:
            if rhs:
                self.solver.add_clause([])
            return
        if len(variables) == 1:
            self.solver.add_clause([variables[0] if rhs else -variables[0]])
            return
        current = variables[0]
        for variable in variables[1:]:
            out = self.var()
            # out = current XOR variable.
            self.solver.add_clause([-current, -variable, -out])
            self.solver.add_clause([-current, variable, out])
            self.solver.add_clause([current, -variable, out])
            self.solver.add_clause([current, variable, -out])
            current = out
        self.solver.add_clause([current if rhs else -current])

    def parity_var(self, variables):
        out = self.var()
        self.xor(list(variables) + [out], 0)
        return out


def level_table(name):
    return [sum(t in s for s in NESTED[name]) for t in range(64)]


def solve_name(name):
    levels = level_table(name)
    cnf = CNF()
    coeff = [[cnf.var() for _ in MONOMIALS] for _ in range(3)]

    def evaluation(bit, point):
        return cnf.parity_var(
            coeff[bit][i] for i, monomial in enumerate(MONOMIALS)
            if monomial & point == monomial
        )

    values = [[evaluation(bit, point) for point in range(64)] for bit in range(3)]

    # Different level classes must have disjoint codeword sets.  This is the
    # exact semantic condition; unlike the rejected fixed-label model, it
    # permits a large class to occupy multiple unused codewords.
    for left in range(64):
        for right in range(left):
            if levels[left] == levels[right]:
                continue
            differences = [
                cnf.parity_var([values[bit][left], values[bit][right]])
                for bit in range(3)
            ]
            cnf.solver.add_clause(differences)

    status = cnf.solver.solve()
    if not status:
        cnf.solver.delete()
        return None
    model = set(v for v in cnf.solver.get_model() if v > 0)
    funcs = []
    for bit in range(3):
        truth = 0
        for point in range(64):
            value = sum(
                (1 if coeff[bit][i] in model else 0)
                for i, monomial in enumerate(MONOMIALS)
                if monomial & point == monomial
            ) & 1
            truth |= value << point
        funcs.append(truth)
    cnf.solver.delete()
    verify_code(name, funcs)
    return {
        "name": name,
        "degree": 3,
        "monomials": [
            [MONOMIALS[i] for i, variable in enumerate(coeff[bit]) if variable in model]
            for bit in range(3)
        ],
        "truth_tables": funcs,
        "level_codes": {
            str(level): sorted({
                sum(((funcs[bit] >> point) & 1) << bit for bit in range(3))
                for point in range(64) if levels[point] == level
            })
            for level in range(6)
        },
    }


def verify_code(name, funcs):
    levels = level_table(name)
    codes = [sum(((funcs[bit] >> point) & 1) << bit for bit in range(3))
             for point in range(64)]
    nonzero = {level: {codes[p] for p in range(64) if levels[p] == level}
               for level in range(1, 6)}
    sets = {level: {codes[p] for p in range(64) if levels[p] == level}
            for level in range(6)}
    assert all(sets[i].isdisjoint(sets[j]) for i in range(6) for j in range(i))
    return codes


def solve_all():
    result = {}
    for name in ("u1", "v1", "u2", "v2"):
        result[name] = solve_name(name)
        if result[name] is None:
            raise RuntimeError(f"no degree-3 code found for {name}")
    return result


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/level_degree3_codes.json")
    result = solve_all()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    for name, item in result.items():
        print(name, item["level_codes"], flush=True)
    print("wrote", out)
