"""Checks for the width-constrained synthesis attempt."""
import json
from pathlib import Path

import pytest

import post185_width_synthesis as W
import post185_xag_pebble as P
import two_stage_oracle as ts
from destructive_xag import load_xag
from post258_two_stage_anf import decode
from xag_to_inplace_layers import XAGGraph

XAGS = Path('artifacts/multiplicative_depth/optimized')


def protected_codes():
    rec = json.loads(Path('artifacts/185/class_codes.json').read_text())
    par = lambda v, m: bin(v & m).count('1') & 1
    yl, xl = decode(rec['ylab']), decode(rec['xlab'])
    return {'y': ([yl[(par(y, 32), ts.ROWCLS[y])] for y in range(64)], ts.ROWCLS, 32),
            'x': ([xl[(par(x, 48), ts.COLCLS[x])] for x in range(64)], ts.COLCLS, 48)}


def test_no_scratch_free_code_exists():
    """A zero-scratch loader needs degree <= 3; the best valid code is degree 5."""
    for side, (start, cls, mask) in protected_codes().items():
        best = W.min_degree(cls, mask, start, steps=4000, seeds=2)
        assert best is not None
        assert best[0] >= 4, 'a degree-3 code would make the loader scratch-free'


def test_protected_code_is_not_a_quadratic_cascade():
    for side, (start, cls, mask) in protected_codes().items():
        residual, last = W.cascade_residual(W.bits_of(start))
        assert residual > 0


def test_conflicts_detects_an_invalid_code():
    start, cls, mask = protected_codes()['y']
    raw = [bin(v & mask).count('1') & 1 for v in range(64)]
    assert W.conflicts(start, cls, raw) == 0
    broken = list(start)
    broken[17] = broken[0]                 # class 5 collides with class 0
    assert W.conflicts(broken, cls, raw) > 0


def test_narrowest_network_still_needs_far_more_than_six_ancillas():
    parsed = load_xag(XAGS / 'shared_balance.xag')
    graph = XAGGraph(parsed.nodes)
    roots, _, _ = P.output_parts(parsed)
    with pytest.raises(ValueError):
        P.plan(graph, roots, 6)
    ops, marks = P.plan(graph, roots, 11)
    assert len(marks) == len(roots)
    # recomputation over the ideal two passes, but a working schedule
    assert 2 * len(parsed.nodes) <= len(ops) <= 4 * len(parsed.nodes)


def test_output_is_an_affine_form_so_roots_only_need_a_z():
    parsed = load_xag(XAGS / 'shared_balance.xag')
    roots, linear, constant = P.output_parts(parsed)
    assert len(roots) == 10
    assert all(0 <= w < 12 for w in linear)
