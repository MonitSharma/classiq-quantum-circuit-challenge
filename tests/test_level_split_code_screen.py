"""Independent checks for the split-code exclusion (no quantum claim)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pysat.solvers import Solver
from level_degree3_codes import CNF, MONOMIALS, level_table
from level_split_code_screen import linear_screen


def test_v2_only_one_split_pair_survives_linear_screen():
    from itertools import combinations
    survivors = [pair for pair in combinations(range(6), 2)
                 if linear_screen('v2', pair)[3] is None]
    assert survivors == [(1, 5)]


def test_v2_remaining_case_raw_polynomials_independent_solver():
    # Do not use the quotient-space reduction from the production solver.
    # Use explicit polynomial coefficients and a different SAT backend.
    levels = level_table('v2')
    cnf = CNF()
    cnf.solver.delete()
    cnf.solver = Solver(name='glucose3')
    coeff = [[cnf.var() for _ in MONOMIALS] for _ in range(3)]
    values = [[cnf.parity_var(coeff[b][i] for i, m in enumerate(MONOMIALS)
                              if m & p == m) for p in range(64)] for b in range(3)]
    for level in (0, 2, 3, 4):
        points = [p for p in range(64) if levels[p] == level]
        for p in points[1:]:
            for b in range(3):
                cnf.xor([values[b][points[0]], values[b][p]], 0)
    for level, code in zip((0, 2, 3), (0, 1, 2)):
        for b in range(3):
            cnf.xor([values[b][levels.index(level)]], code >> b & 1)
    for p in range(64):
        for q in range(p):
            if levels[p] != levels[q]:
                cnf.solver.add_clause([cnf.parity_var([values[b][p], values[b][q]]) for b in range(3)])
    try:
        assert cnf.solver.solve() is False
    finally:
        cnf.solver.delete()


def test_linear_exclusion_witnesses_are_in_constraint_span():
    # Independently use low-pivot elimination on raw equality constraints.
    from itertools import combinations
    levels = level_table('v2')
    rows = [sum(1 << i for i, m in enumerate(MONOMIALS) if m & p == m) for p in range(64)]
    for split in combinations(range(6), 2):
        collision = linear_screen('v2', split)[3]
        if collision is None:
            continue
        basis = {}
        for level in set(range(6)) - set(split):
            points = [p for p in range(64) if levels[p] == level]
            for p in points[1:]:
                r = rows[p] ^ rows[points[0]]
                while r:
                    bit = r & -r
                    if bit in basis:
                        r ^= basis[bit]
                    else:
                        basis[bit] = r
                        break
        p, q = collision
        assert levels[p] != levels[q]
        r = rows[p] ^ rows[q]
        while r:
            bit = r & -r
            assert bit in basis
            r ^= basis[bit]
