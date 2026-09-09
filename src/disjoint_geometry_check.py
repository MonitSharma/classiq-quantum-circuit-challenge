"""Exhaustively validate the disjoint A XOR B' XOR C XOR D identity."""

import json
from pathlib import Path

from search import logo


def rectangle_a(x, y):
    return 2 <= x <= 26 and 29 <= y <= 53


def rectangle_b_prime(x, y):
    return 27 <= x <= 48 and 39 <= y <= 43


def disk_c(x, y):
    return (x - 55) ** 2 + (y - 41) ** 2 <= 42


def disk_d(x, y):
    return (x - 40) ** 2 + (y - 19) ** 2 <= 72


def main():
    mismatches = []
    pairwise_overlaps = {}
    shapes = {"A": rectangle_a, "B_prime": rectangle_b_prime, "C": disk_c, "D": disk_d}
    for left, right in (("A", "B_prime"), ("A", "C"), ("A", "D"),
                        ("B_prime", "C"), ("B_prime", "D"), ("C", "D")):
        points = [(x, y) for y in range(64) for x in range(64) if shapes[left](x, y) and shapes[right](x, y)]
        pairwise_overlaps[f"{left}&{right}"] = points
    for y in range(64):
        for x in range(64):
            xor_value = sum(fn(x, y) for fn in shapes.values()) % 2
            if bool(xor_value) != bool(logo(x, y)):
                mismatches.append([x, y])
    result = {
        "mismatches": len(mismatches),
        "mismatch_points": mismatches,
        "pairwise_overlap_counts": {key: len(value) for key, value in pairwise_overlaps.items()},
        "pairwise_overlaps": pairwise_overlaps,
    }
    Path("artifacts/disjoint_geometry_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    assert not mismatches
    assert all(not points for points in pairwise_overlaps.values())


if __name__ == "__main__":
    main()
