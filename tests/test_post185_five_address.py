"""Correctness boundaries for compressed descriptors and phase completion."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from post185_five_address import Completion, codes, descriptor, make_loader, parity
from distributed_ucry import rank
import two_stage_oracle as ts


def test_five_variable_labels_preserve_classes_and_both_raw_bits():
    for side, direction, selector, cls in [('y', 16, 16, ts.ROWCLS),
                                          ('x', 4, 12, ts.COLCLS),
                                          ('x', 55, 16, ts.COLCLS)]:
        d = descriptor(side, direction, selector)
        labels = [list(range(len(g))) for g in d['groups']]
        table = codes(d, labels)
        assert rank(d['frame']) == 6
        assert [parity(direction, m) for m in d['frame']] == [0, 1, 0, 0, 0, 0]
        classes = {}
        for v, word in enumerate(table):
            assert table[v] >> 2 == table[v ^ direction] >> 2
            assert classes.setdefault(word, cls[v]) == cls[v]


def test_integer_lift_satisfies_every_logo_input():
    y, x = descriptor('y', 16, 16), descriptor('x', 4, 12)
    yc = codes(y, [list(range(len(g))) for g in y['groups']])
    xc = codes(x, [list(range(len(g))) for g in x['groups']])
    p = Completion(5, 5)
    _, terms, care = p.solve(yc, xc)
    co = p.spectrum(terms)
    for word, truth in care.items():
        lifted = sum(m & ~word == 0 for m in terms)
        assert lifted % 2 == truth
        reconstructed = sum(c * (-1) ** parity(word, m) for m, c in enumerate(co))
        assert abs(reconstructed - lifted) < 1e-10
    assert len(care) < 1024


def test_native_loader_maps_all_promised_inputs():
    d = descriptor('x', 4, 12)
    labels = [list(reversed(range(len(g)))) for g in d['groups']]
    q, meta = make_loader(d, labels, seeds=2)
    assert q.num_qubits == 9
    assert set(q.count_ops()) <= {'u3', 'cx'}
    assert np.isfinite(meta['error']) and meta['error'] < 1e-10


def test_saved_care_completion_preserves_phase_on_all_reachable_words():
    from post185_five_address import care_completion, fixed_codes
    p = Completion(4, 4)
    yc, xc = fixed_codes('y'), fixed_codes('x')
    _, terms, care = p.solve(yc, xc)
    item = dict(ny=4, nx=4, ycode=yc, xcode=xc, terms=terms)
    result = care_completion(item, seconds=1, seed=9)
    assert result['history']
    co = result['co']
    for word, truth in care.items():
        phase = sum(c * (-1) ** parity(word, m) for m, c in enumerate(co))
        assert abs(np.exp(1j * np.pi * phase) - (-1) ** truth) < 1e-8
