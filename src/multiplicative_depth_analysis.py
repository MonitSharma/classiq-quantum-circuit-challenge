"""Exact ANF diagnostics for the 12-input logo predicate.

This is deliberately a diagnostic, not a term-by-term quantum compiler. It
reports algebraic degree and term counts that can guide shallow nonlinear
proposal generation.
"""

from __future__ import annotations

import json
from pathlib import Path

from search import logo


N = 12


def truth_vector() -> list[int]:
    return [int(logo(index & 63, (index >> 6) & 63)) for index in range(1 << N)]


def anf_coefficients(values: list[int]) -> list[int]:
    coeffs = values[:]
    for bit in range(N):
        for mask in range(1 << N):
            if mask & (1 << bit):
                coeffs[mask] ^= coeffs[mask ^ (1 << bit)]
    return coeffs


def analyze() -> dict:
    values = truth_vector()
    coeffs = anf_coefficients(values)
    by_degree: dict[int, int] = {}
    for mask, value in enumerate(coeffs):
        if value:
            degree = mask.bit_count()
            by_degree[degree] = by_degree.get(degree, 0) + 1
    return {
        "variables": N,
        "marked_points": sum(values),
        "algebraic_degree": max(by_degree),
        "nonconstant_terms": sum(count for degree, count in by_degree.items()
                                 if degree > 0),
        "terms_by_degree": {str(k): v for k, v in sorted(by_degree.items())},
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path("artifacts/phase_history/logo_anf.json"))
    args = parser.parse_args()
    result = analyze()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
