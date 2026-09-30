"""Checks on concrete encoder construction and its dirty helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from v2_native_checkpoint import affine_solution, complete, code_candidates, frames, primitive_check
from level_degree3_codes import verify_code


def test_affine_completion_and_contradiction():
    # x0+x1=1, x1+x2=0; both assignments of the free variable work.
    rows = [0b011 | (1 << 3), 0b110]
    pivots = affine_solution(rows, 3)
    for initial in (0, 4):
        solution = complete(pivots, 3, initial)
        assert all(((row & solution).bit_count() & 1) == (row >> 3) for row in rows)
    assert affine_solution([0b001, 0b001 | (1 << 3)], 3) is None


def test_constructed_code_degree_and_frame():
    tables, _ = next(code_candidates(degree=5))
    verify_code('v2', tables)
    for table in tables:
        coefficients = [(table >> p) & 1 for p in range(64)]
        for b in range(6):
            for p in range(64):
                if p >> b & 1: coefficients[p] ^= coefficients[p ^ (1 << b)]
        assert all(not value or p.bit_count() <= 5 for p, value in enumerate(coefficients))
    transformed, _ = frames(tables)
    verify_code('v2', transformed)


def test_relative_phase_primitives_restore_arbitrary_dirty_helpers():
    for controls in (3, 4, 5):
        primitive_check(controls)
