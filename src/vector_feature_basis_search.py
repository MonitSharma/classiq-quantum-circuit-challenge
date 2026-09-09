"""Screen affine output encodings for the five-output feature loader.

The search is intentionally staged: score all generated encodings using exact
ANF support, then run ABC on the strongest distinct candidates.  It does not
claim a reversible implementation; its purpose is to choose representations
for the later pebbling compiler.
"""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from vector_feature_analysis import ARTIFACTS, FEATURES, output_inventory, truth_rows

ROOT = Path(__file__).resolve().parents[1]
ABC = ROOT / "experiments/abc/abc"
BASE = output_inventory(truth_rows())[0]
BASE_TT = [BASE[name]["truth_table"] for name in FEATURES]
FULL = (1 << 64) - 1


def rank(rows: tuple[int, ...]) -> bool:
    rows = list(rows)
    rank = 0
    for bit in range(5):
        pivot = next((i for i in range(rank, 5) if rows[i] & (1 << bit)), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(5):
            if i != rank and rows[i] & (1 << bit):
                rows[i] ^= rows[rank]
        rank += 1
    return rank == 5


def transform(tt: list[int], rows: tuple[int, ...], offset: int) -> list[int]:
    return [
        (offset >> out) & 1 ^ sum(
            ((rows[out] >> inp) & 1) * ((tt[inp] >> y) & 1)
            for inp in range(5)
        ) % 2
        for out in range(5)
        for y in []
    ]


def transformed_truth_tables(rows: tuple[int, ...], offset: int) -> list[int]:
    result = []
    for out in range(5):
        value = FULL if (offset >> out) & 1 else 0
        for inp in range(5):
            if rows[out] & (1 << inp):
                value ^= BASE_TT[inp]
        result.append(value)
    return result


def anf_support(value: int) -> set[int]:
    coeff = [(value >> i) & 1 for i in range(64)]
    for bit in range(6):
        step = 1 << bit
        for i in range(64):
            if i & step:
                coeff[i] ^= coeff[i ^ step]
    return {i for i, item in enumerate(coeff) if item}


def score(rows: tuple[int, ...], offset: int) -> dict:
    tables = transformed_truth_tables(rows, offset)
    supports = [anf_support(value) for value in tables]
    union = set().union(*supports)
    return {
        "matrix_rows": list(rows),
        "offset": offset,
        "anf_union": len(union),
        "anf_terms": sum(len(s) for s in supports),
        "max_degree": max((m.bit_count() for m in union), default=0),
        "output_term_counts": [len(s) for s in supports],
    }


def elementary_matrices() -> list[tuple[int, ...]]:
    identity = tuple(1 << i for i in range(5))
    matrices = {identity}
    for target in range(5):
        for control in range(5):
            if target == control:
                continue
            row = list(identity)
            row[target] ^= 1 << control
            matrices.add(tuple(row))
    return sorted(matrices)


def random_matrix(rng: random.Random) -> tuple[int, ...]:
    rows = [1 << i for i in range(5)]
    for _ in range(rng.randint(2, 14)):
        target, control = rng.sample(range(5), 2)
        rows[target] ^= 1 << control
    return tuple(rows)


def write_pla(tables: list[int], path: Path) -> None:
    lines = [".i 6", ".o 5", ".ilb y0 y1 y2 y3 y4 y5",
             ".ob " + " ".join(FEATURES)]
    for y in range(64):
        lines.append("".join(str((y >> bit) & 1) for bit in range(6)) + " " +
                     "".join(str((table >> y) & 1) for table in tables))
    lines.append(".e")
    path.write_text("\n".join(lines) + "\n")


def abc_metrics(candidate: dict, index: int) -> dict:
    tables = transformed_truth_tables(tuple(candidate["matrix_rows"]), candidate["offset"])
    pla = ARTIFACTS / f"vector_basis_{index:03d}.pla"
    write_pla(tables, pla)
    bench = ARTIFACTS / f"vector_basis_{index:03d}.bench"
    script = f"read_pla {pla}; strash; balance; rewrite; refactor; resub; balance; ps; write_bench {bench}"
    result = subprocess.run([str(ABC), "-c", script], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    line = next((line for line in result.stdout.splitlines() if "i/o =" in line), "")
    fields = line.replace("=", " ").split()
    and_count = int(fields[fields.index("and") + 1]) if "and" in fields else None
    level = int(fields[fields.index("lev") + 1]) if "lev" in fields else None
    return {**candidate, "abc_and": and_count, "abc_level": level,
            "abc_returncode": result.returncode}


def main() -> None:
    rng = random.Random(531)
    matrices = set(elementary_matrices())
    while len(matrices) < 256:
        matrices.add(random_matrix(rng))
    candidates = []
    for matrix in sorted(matrices):
        for offset in range(32):
            candidates.append(score(matrix, offset))
    candidates.sort(key=lambda item: (item["anf_union"], item["anf_terms"], item["max_degree"]))
    # Keep the natural basis plus a broad set of distinct high-scoring encodings.
    selected = []
    seen = set()
    for item in candidates:
        key = (tuple(item["matrix_rows"]), item["offset"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= 64:
            break
    abc = [abc_metrics(item, index) for index, item in enumerate(selected)]
    result = {
        "generated_matrices": len(matrices),
        "affine_encodings_scored": len(candidates),
        "abc_candidates": len(abc),
        "natural_basis": score(tuple(1 << i for i in range(5)), 0),
        "best_by_anf": selected[0],
        "best_by_abc": min(abc, key=lambda item: (
            item["abc_and"] if item["abc_and"] is not None else 10**9,
            item["abc_level"] if item["abc_level"] is not None else 10**9,
        )),
        "candidates": abc,
        "note": "ANF and ABC scores are irreversible screening metrics; no loader or oracle score is claimed.",
    }
    (ARTIFACTS / "vector_feature_basis_search.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({
        "generated_matrices": len(matrices),
        "encodings_scored": len(candidates),
        "abc_candidates": len(abc),
        "natural": result["natural_basis"],
        "best_by_anf": result["best_by_anf"],
        "best_by_abc": result["best_by_abc"],
    }, indent=2))


if __name__ == "__main__":
    main()
