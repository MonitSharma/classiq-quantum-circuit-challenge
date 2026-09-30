"""Regression tests for the finite-state / MTBDD structural audit."""
import numpy as np
import pytest

from post185_finite_state_oracle import (
    logo, mask, row_column_classes, gf2_rank, intervals, audit,
)
from search import logo as search_logo, row_terms, nested_terms, MASK
from disjoint_hybrid_geometry import verify_all_points


def test_logo_reconstruction_exact():
    M = mask()
    assert M.shape == (64, 64)
    assert M.sum() > 0
    # every cell matches the authoritative predicate
    for y in range(64):
        for x in range(64):
            assert M[y, x] == int(logo(x, y))
            assert M[y, x] == int(search_logo(x, y))
    # symmetric reflection-free sanity: total count is positive and < 4096
    assert 0 < M.sum() < 4096


def test_disjoint_partition_matches_logo():
    assert verify_all_points()


def test_row_column_class_counts():
    M = mask()
    _, _, nrows, ncols = row_column_classes(M)
    assert nrows == 11
    assert ncols == 11


def test_row_classes_are_intervals():
    # each non-empty row class is either empty, one interval, or two intervals
    M = mask()
    rowcls, _, _, _ = row_column_classes(M)
    for y in range(64):
        iv = intervals(M[y].tolist())
        assert len(iv) <= 2, (y, iv)


def test_gf2_rank_is_ten():
    assert gf2_rank(mask()) == 10


def test_nested_and_row_terms_reproduce_logo():
    # GF(2) rectangle decompositions must XOR back to the exact logo matrix
    for terms in (row_terms(), nested_terms()):
        out = np.zeros((64, 64), dtype=np.uint8)
        for x, y in terms:
            xv = np.array([(x >> i) & 1 for i in range(64)], dtype=np.uint8)
            yv = np.array([(y >> i) & 1 for i in range(64)], dtype=np.uint8)
            out ^= np.outer(yv, xv).astype(np.uint8)
        assert np.array_equal(out, MASK)


def test_audit_output_consistent(tmp_path):
    r = audit(tmp_path)
    assert r['row_classes'] == 11
    assert r['column_classes'] == 11
    assert r['gf2_rank'] == 10
    assert r['real_phase_matrix_rank'] == 11
    # exact ANF monomial counts for representative intervals
    assert r['interval_anf_monomials']['square[2,26]'] == 32
    assert r['interval_anf_monomials']['bar[27,48]'] == 16
    assert r['interval_anf_monomials']['D2[32,48]'] == 16
    assert r['interval_anf_monomials']['D1[49,61]'] == 14
    # BDD node counts are bounded (compact decision structure)
    for name, n in r['bdd_nodes'].items():
        assert 0 < n < 200, (name, n)
    # TT ranks are small across all cuts and orders
    for name, ranks in r['tt_unfolding_ranks'].items():
        assert max(ranks) <= 40, (name, ranks)
    assert (tmp_path / 'structural_audit.json').exists()


if __name__ == '__main__':
    import sys
    sys.exit(pytest.main([__file__, '-q']))
