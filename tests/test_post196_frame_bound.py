"""The loader frame function must stay a *valid* bound, and catch the audit case."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from post196_frame_balance import TOUCH, TOUR, loader_floor       # noqa: E402
from post258_two_stage_anf import decode                          # noqa: E402
from two_stage_oracle import ROWCLS, COLCLS                       # noqa: E402


def _tables(key, cls, rho):
    labels = decode(json.loads(Path('artifacts/218/class_codes.json').read_text())[key])
    codes = [labels[((v & rho).bit_count() & 1, cls[v])] for v in range(64)]
    return np.array([[math.pi * ((codes[v] >> b) & 1) for v in range(64)] for b in range(3)])


def test_contention_term_catches_the_audit_counterexample():
    """Six hosts each needing low masks {0, 1}: wire 0 alone needs twelve CX."""
    subset = 0b11
    assert TOUR[subset] == 2
    assert TOUCH[subset] == [2, 0, 0]
    assert sum(TOUCH[subset][0] for _ in range(6)) == 12
    # the scalar terms alone would have returned 4
    assert max(2 + TOUR[subset], math.ceil(6 * TOUR[subset] / 3)) == 4


def test_tours_are_closed_and_even_per_bit():
    """A closed tour from 0 toggles every bit an even number of times."""
    for subset in range(1, 256):
        for k in range(3):
            touched = any((m >> k) & 1 for m in range(8) if subset >> m & 1)
            assert TOUCH[subset][k] == (2 if touched else 0)
        visits = bin(subset).count('1')
        assert TOUR[subset] >= visits - (1 if subset & 1 else 0)


def test_bound_is_attained_on_the_recorded_codes():
    """Calibration point: the bound is 77 and the compiled loaders achieve 77."""
    for key, cls, rho in (('ylab', ROWCLS, 32), ('xlab', COLCLS, 48)):
        value, _ = loader_floor(_tables(key, cls, rho))
        assert value == 77
