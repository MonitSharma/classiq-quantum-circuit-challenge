"""The four-wire descriptor forces a six-address lookup; keep that closure honest."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from post196_dirty_descriptor import (patterns, permutation_classes,   # noqa: E402
                                      translation_classes)
from two_stage_oracle import ROWCLS, COLCLS                            # noqa: E402


def _best(classes, width):
    best = None
    for bits in itertools.combinations(range(6), width):
        needed, _ = translation_classes(patterns(classes, bits), 6 - width)
        if best is None or needed < best:
            best = needed
    return best


def test_two_bit_residual_uses_every_permutation():
    """|AGL(2,2)| = 24 = 4!, so affine maps are all permutations of four states."""
    _, _, maps = permutation_classes(patterns(ROWCLS, (0, 1, 2, 3)), 2)
    assert maps == 24


def test_four_and_five_address_splittings_are_infeasible():
    for classes in (ROWCLS, COLCLS):
        assert _best(classes, 4) > 2 ** (4 - 2)
        assert _best(classes, 5) > 2 ** (5 - 2)


def test_six_address_splitting_is_the_one_that_fits():
    for classes in (ROWCLS, COLCLS):
        needed, _ = translation_classes(patterns(classes, (0, 1, 2, 3, 4, 5)), 0)
        assert needed == len(set(classes)) == 11
        assert needed <= 2 ** (6 - 2)
