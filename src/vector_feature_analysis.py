"""Build the exact five-output y-feature truth table and algebra inventory.

This is the first, loader-only stage of the joint reversible-loader experiment.
It deliberately does not touch the protected 531-depth artifact or construct a
complete oracle.  Truth tables use the repository's little-endian convention:
bit ``b`` of the integer row index is feature/input wire ``b``.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from radius import radius


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
N = 64
FEATURES = ("R0", "R1", "R2", "A", "B")


def truth_rows() -> list[dict[str, int]]:
    rows = []
    for y in range(N):
        r = radius(y)
        rows.append({
            "y": y,
            "R0": (r >> 0) & 1,
            "R1": (r >> 1) & 1,
            "R2": (r >> 2) & 1,
            "A": int(29 <= y <= 53),
            "B": int(39 <= y <= 43),
        })
    return rows


def anf_monomials(values: list[int]) -> list[int]:
    """Return ANF monomial masks after the in-place Möbius transform."""
    coeff = values[:]
    for bit in range(6):
        step = 1 << bit
        for base in range(N):
            if base & step:
                coeff[base] ^= coeff[base ^ step]
    return [mask for mask, value in enumerate(coeff) if value]


def truth_mask(values: list[int]) -> int:
    return sum(value << index for index, value in enumerate(values))


def monomial_name(mask: int) -> str:
    if mask == 0:
        return "1"
    return " ".join(f"y{i}" for i in range(6) if mask & (1 << i))


def output_inventory(rows: list[dict[str, int]]) -> tuple[dict, dict]:
    algebra = {}
    occurrence: Counter[int] = Counter()
    output_masks: dict[int, list[str]] = {}
    for feature in FEATURES:
        values = [row[feature] for row in rows]
        monomials = anf_monomials(values)
        for monomial in monomials:
            occurrence[monomial] += 1
            output_masks.setdefault(monomial, []).append(feature)
        algebra[feature] = {
            "truth_table": truth_mask(values),
            "on_set": [row["y"] for row in rows if row[feature]],
            "anf_monomials": monomials,
            "anf_terms": [monomial_name(m) for m in monomials],
            "anf_term_count": len(monomials),
            "algebraic_degree": max((m.bit_count() for m in monomials), default=0),
            "nonconstant_anf_term_count": sum(m != 0 for m in monomials),
        }

    shared = {
        "unique_anf_monomial_count": len(occurrence),
        "sum_scalar_anf_terms": sum(v["anf_term_count"] for v in algebra.values()),
        "occurrence_histogram": dict(sorted(Counter(occurrence.values()).items())),
        "shared_monomials": [
            {
                "mask": mask,
                "term": monomial_name(mask),
                "occurrences": count,
                "outputs": output_masks[mask],
            }
            for mask, count in sorted(occurrence.items())
            if count > 1
        ],
        "output_masks": {
            str(mask): output_masks[mask] for mask in sorted(output_masks)
        },
    }
    return algebra, shared


def main() -> None:
    rows = truth_rows()
    assert len(rows) == 64 and {row["y"] for row in rows} == set(range(64))
    algebra, shared = output_inventory(rows)
    codewords = {}
    for row in rows:
        code = "".join(str(row[name]) for name in FEATURES)
        codewords.setdefault(code, []).append(row["y"])

    table = {
        "input": "y, little-endian bits y0..y5",
        "outputs": list(FEATURES),
        "definitions": {
            "R0": "radius(y) bit 0 from src/radius.py",
            "R1": "radius(y) bit 1 from src/radius.py",
            "R2": "radius(y) bit 2 from src/radius.py",
            "A": "29 <= y <= 53",
            "B": "39 <= y <= 43",
        },
        "rows": rows,
        "distinct_output_codewords": {
            code: ys for code, ys in sorted(codewords.items())
        },
        "distinct_output_codeword_count": len(codewords),
    }
    (ARTIFACTS / "vector_feature_truth_table.json").write_text(
        json.dumps(table, indent=2) + "\n"
    )
    algebra_doc = {
        "outputs": list(FEATURES),
        "per_output": algebra,
        "joint_anf_inventory": shared,
        "note": "ANF is over GF(2), with y0 as the least-significant input variable.",
    }
    (ARTIFACTS / "vector_feature_algebra.json").write_text(
        json.dumps(algebra_doc, indent=2) + "\n"
    )
    print(json.dumps({
        "rows": len(rows),
        "distinct_codewords": len(codewords),
        "per_output": {
            name: {
                "anf_terms": value["anf_term_count"],
                "degree": value["algebraic_degree"],
            }
            for name, value in algebra.items()
        },
        "unique_anf_monomials": shared["unique_anf_monomial_count"],
        "sum_scalar_anf_terms": shared["sum_scalar_anf_terms"],
        "shared_monomials": len(shared["shared_monomials"]),
    }, indent=2))


if __name__ == "__main__":
    main()
