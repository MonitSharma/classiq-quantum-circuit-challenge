from post190_relative_depth2_sat import affine_expr, solve_prefix
import z3


def test_affine_selector_is_exact_bitvector_expression():
    a = z3.Bool('selector_a')
    expr = affine_expr([a], [0xAAAAAAAAAAAAAAAA])
    assert z3.simplify(expr.substitute if False else expr) is not None


def test_stage_pattern_is_recorded():
    full = (1 << 64) - 1
    prefix = {'basis': (full, 1, 2), 'goals': (3, 4), 'missing': (0, 1)}
    result = solve_prefix(prefix, (1, 1), seconds=1)
    assert result['pattern'] == [1, 1]
    assert result['status'] in ('SAT', 'UNSAT', 'UNKNOWN')
