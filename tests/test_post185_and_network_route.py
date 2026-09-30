"""Checks for the AND-network reading of the leaderboard and its measurements."""
from pathlib import Path

import pytest

import post185_and_loader as AL
import post185_xag_audit as AU
import two_stage_oracle as ts

XAGS = Path('artifacts/multiplicative_depth/optimized')
SHARED = XAGS / 'shared_balance.xag'
ROUND4 = XAGS / 'advanced_round4.xag'


def test_shared_balance_matches_the_rank_one_cost_profile():
    model = AU.cost_model(SHARED)
    assert model['ands'] == 81
    assert model['and_depth'] == 6
    assert model['routing_cx'] == 36
    # rank one on the September leaderboard is 137 depth / 561 CX
    assert abs(model['predicted_cx'] - 561) <= 5
    assert AU.is_exact(SHARED)


def test_two_affine_networks_are_not_exact():
    for name in ('affine_none', 'affine_balance_118'):
        assert not AU.is_exact(XAGS / (name + '.xag'))


def test_every_exact_network_exceeds_the_eighteen_wire_budget():
    for path in sorted(XAGS.glob('*.xag')):
        if not AU.is_exact(path):
            continue
        audit = AU.width_audit(path, restarts=40)
        # twelve coordinates must stay in the span, leaving six live AND values
        assert audit['peak_live_and_values'] > 6
        assert audit['wires_needed'] > audit['wires_available']


def test_existing_compiler_walks_the_network_several_times_over():
    report = AU.cost_of_existing_compiler(ROUND4)
    assert report['roots'] == 11
    # per-root cone rebuilds alone cost several times a single shared pass
    assert report['ratio'] > 3.0


def test_witness_networks_are_valid_class_codes():
    par = lambda v, m: bin(v & m).count('1') & 1
    for side, cls, mask in (('y', ts.ROWCLS, 32), ('x', ts.COLCLS, 48)):
        table = AL.code_table(side)
        for c in set(cls):
            assert len({table[v] for v in range(64) if cls[v] == c}) == 1
        for a in range(64):
            for b in range(a + 1, 64):
                if cls[a] != cls[b] and par(a, mask) == par(b, mask):
                    assert table[a] != table[b]


def test_min_and_loader_compiles_but_is_slower_than_the_rotation_loader():
    """Fewest AND gates is the wrong objective: the affine routing dominates."""
    data = list(range(6, 12))
    best = AL.best_side('y', data, [12, 13, 14], [15, 16, 17, 18, 19],
                        width=20, tries=60)
    assert best is not None, 'the fourteen-AND y witness needs five scratch wires'
    (depth, cx), native, logical, order = best
    AL.verify('y', logical, [12, 13, 14], data, width=20)
    # the uniformly controlled Ry loader it would replace is 78 layers / 198 CX
    assert depth > 150
