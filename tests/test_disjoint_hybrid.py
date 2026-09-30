"""Tests for disjoint hybrid geometry and corner pruning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from disjoint_hybrid_geometry import (
    logo,
    logo_disjoint,
    in_d1_box_minus_corners,
    in_d2_box_minus_corners,
    verify_all_points,
)

def test_all_points_verified():
    assert verify_all_points()

def test_pairwise_disjoint():
    for x in range(64):
        for y in range(64):
            sq, bp, d1, d2 = logo_disjoint(x, y)
            assert sum([sq, bp, d1, d2]) <= 1

def test_corner_pruning():
    for x in range(64):
        for y in range(64):
            _, _, d1, d2 = logo_disjoint(x, y)
            assert in_d1_box_minus_corners(x, y) == d1
            assert in_d2_box_minus_corners(x, y) == d2
