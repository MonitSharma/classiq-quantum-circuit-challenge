"""Exact disjoint geometry and corner exception tables for the Classiq logo."""
import numpy as np

def logo(x: int, y: int) -> bool:
    """Authoritative local predicate for the Classiq logo."""
    sq = (2 <= x <= 26 and 29 <= y <= 53)
    bar = (26 <= x <= 49 and 39 <= y <= 43)
    d1 = ((x - 55)**2 + (y - 41)**2 <= 42)
    d2 = ((x - 40)**2 + (y - 19)**2 <= 72)
    return bool(sq or bar or d1 or d2)

def logo_disjoint(x: int, y: int) -> tuple[bool, bool, bool, bool]:
    """Pairwise disjoint partition of the Classiq logo: (Square, Bar_prime, D1, D2)."""
    sq = (2 <= x <= 26 and 29 <= y <= 53)
    bar_prime = (27 <= x <= 48 and 39 <= y <= 43)
    d1 = ((x - 55)**2 + (y - 41)**2 <= 42)
    d2 = ((x - 40)**2 + (y - 19)**2 <= 72)
    return bool(sq), bool(bar_prime), bool(d1), bool(d2)

# Disk quadrant corner exclusions:
# For D1 (center 55, 41, R^2 <= 42): in box dx in 0..6, dy in 0..6 (49 points), 8 points excluded:
D1_CORNERS = frozenset([(3, 6), (4, 6), (5, 5), (5, 6), (6, 3), (6, 4), (6, 5), (6, 6)])

# For D2 (center 40, 19, R^2 <= 72): in box dx in 0..8, dy in 0..8 (81 points), 16 points excluded:
D2_CORNERS = frozenset([
    (3, 8), (4, 8), (5, 7), (5, 8), (6, 7), (6, 8),
    (7, 5), (7, 6), (7, 7), (7, 8),
    (8, 3), (8, 4), (8, 5), (8, 6), (8, 7), (8, 8)
])

def in_d1_box_minus_corners(x: int, y: int) -> bool:
    """Evaluate D1 via bounding box minus corner exclusions."""
    if not ((x >> 5) & 1) or not ((y >> 5) & 1):
        return False
    dx = abs(x - 55)
    dy = abs(y - 41)
    if dx > 6 or dy > 6:
        return False
    return (dx, dy) not in D1_CORNERS

def in_d2_box_minus_corners(x: int, y: int) -> bool:
    """Evaluate D2 via bounding box minus corner exclusions."""
    if not ((x >> 5) & 1) or ((y >> 5) & 1):
        return False
    dx = abs(x - 40)
    dy = abs(y - 19)
    if dx > 8 or dy > 8:
        return False
    return (dx, dy) not in D2_CORNERS

def verify_all_points() -> bool:
    """Exhaustively verify that the disjoint partition and corner pruning match logo(x,y)."""
    for x in range(64):
        for y in range(64):
            expected = logo(x, y)
            sq, bp, d1, d2 = logo_disjoint(x, y)
            active = sum([sq, bp, d1, d2])
            if active > 1:
                return False
            if (active == 1) != expected:
                return False
            if in_d1_box_minus_corners(x, y) != d1:
                return False
            if in_d2_box_minus_corners(x, y) != d2:
                return False
    return True

if __name__ == '__main__':
    assert verify_all_points(), 'Disjoint geometry verification failed!'
    print('All 4,096 points verified successfully!')
