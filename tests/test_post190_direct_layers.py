import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import post190_direct_layers as dl


def test_quotient_has_eleven_classes_each_way():
    rows, cols = dl.classes()
    assert (len(rows), len(cols)) == (11, 11)


def test_structural_samples_are_balanced_and_unique():
    s = dl.structural_samples(24)
    assert len(s) == len(set(s)) and len(s) >= 24
    on = sum(dl.logo(v & 63, v >> 6) for v in s)
    assert 0 < on < len(s)


def test_evaluate_matches_a_hand_built_network():
    ops = [('ccx', [0, 1, 17])]
    bad = dl.evaluate(ops)
    assert len(bad) == sum(1 for v in range(4096)
                           if ((v & 1) & (v >> 1 & 1)) != int(dl.logo(v & 63, v >> 6)))


def test_ceiling_matches_the_layer_formula():
    assert (dl.ceiling(5, 3), dl.ceiling(6, 2), dl.ceiling(6, 3)) == (115, 129, 139)


def test_named_matchings_are_perfect():
    for name, m in dl.MATCHINGS.items():
        assert sorted(w for pair in m for w in pair) == list(range(12)), name
