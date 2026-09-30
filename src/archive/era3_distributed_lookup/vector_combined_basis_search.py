"""Combine the best sampled y-input basis with an invertible output basis."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows
from vector_input_basis_search import invert, transform_y

ROOT = Path(__file__).resolve().parents[1]
ABC = ROOT / "experiments/abc/abc"
INPUT_MATRIX = (1, 2, 4, 40, 16, 48)
INPUT_OFFSET = 16


def output_matrix(rng: random.Random) -> tuple[int, ...]:
    rows = [1 << i for i in range(5)]
    for _ in range(rng.randint(1, 16)):
        target, control = rng.sample(range(5), 2)
        rows[target] ^= rows[control]
    return tuple(rows)


def transformed_tables() -> dict[str, list[int]]:
    original = {name: [row[name] for row in truth_rows()] for name in FEATURES}
    inv = invert(INPUT_MATRIX)
    return {name: [original[name][transform_y(z, inv, INPUT_OFFSET)] for z in range(64)]
            for name in FEATURES}


def score(matrix: tuple[int, ...], offset: int, tables: dict[str, list[int]]) -> dict:
    features = []
    for output in range(5):
        features.append([
            (offset >> output & 1) ^ sum(
                ((matrix[output] >> source) & 1) * tables[FEATURES[source]][z]
                for source in range(5)
            ) % 2
            for z in range(64)
        ])
    supports = [set(anf_monomials(values)) for values in features]
    union = set().union(*supports)
    return {
        "matrix_rows": list(matrix),
        "offset": offset,
        "anf_union": len(union),
        "anf_terms": sum(len(item) for item in supports),
        "max_degree": max((item.bit_count() for item in union), default=0),
    }


def write_pla(candidate: dict, tables: dict[str, list[int]], path: Path) -> None:
    matrix = tuple(candidate["matrix_rows"])
    offset = candidate["offset"]
    lines = [".i 6", ".o 5", ".ilb z0 z1 z2 z3 z4 z5",
             ".ob " + " ".join(FEATURES)]
    for z in range(64):
        values = [
            (offset >> output & 1) ^ sum(
                ((matrix[output] >> source) & 1) * tables[FEATURES[source]][z]
                for source in range(5)
            ) % 2
            for output in range(5)
        ]
        lines.append("".join(str((z >> bit) & 1) for bit in range(6)) + " " +
                     "".join(map(str, values)))
    lines.append(".e")
    path.write_text("\n".join(lines) + "\n")


def run_abc(candidate: dict, tables: dict[str, list[int]], index: int) -> dict:
    pla = ARTIFACTS / f"vector_combined_basis_{index:03d}.pla"
    bench = ARTIFACTS / f"vector_combined_basis_{index:03d}.bench"
    write_pla(candidate, tables, pla)
    command = f"read_pla {pla}; strash; balance; rewrite; refactor; resub; balance; ps; write_bench {bench}"
    result = subprocess.run([str(ABC), "-c", command], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    line = next((item for item in result.stdout.splitlines() if "i/o =" in item), "")
    fields = line.replace("=", " ").split()
    and_count = int(fields[fields.index("and") + 1]) if "and" in fields else None
    level = int(fields[fields.index("lev") + 1]) if "lev" in fields else None
    return {**candidate, "abc_and": and_count, "abc_level": level,
            "abc_returncode": result.returncode}


def main() -> None:
    rng = random.Random(531)
    matrices = {tuple(1 << i for i in range(5))}
    while len(matrices) < 256:
        matrices.add(output_matrix(rng))
    tables = transformed_tables()
    candidates = [score(matrix, offset, tables)
                  for matrix in sorted(matrices) for offset in range(32)]
    candidates.sort(key=lambda item: (item["anf_union"], item["anf_terms"]))
    abc = [run_abc(item, tables, index) for index, item in enumerate(candidates[:64])]
    natural = score(tuple(1 << i for i in range(5)), 0, tables)
    result = {
        "input_matrix_rows": list(INPUT_MATRIX),
        "input_offset": INPUT_OFFSET,
        "encodings_scored": len(candidates),
        "abc_candidates": len(abc),
        "natural_output_basis": natural,
        "best_by_anf": candidates[0],
        "best_by_abc": min(abc, key=lambda item: (
            item["abc_level"] if item["abc_level"] is not None else 10**9,
            item["abc_and"] if item["abc_and"] is not None else 10**9,
        )),
        "candidates": abc,
        "note": "Exact input/output affine maps; ABC scores are irreversible screening only.",
    }
    (ARTIFACTS / "vector_combined_basis_search.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({
        "encodings_scored": len(candidates),
        "natural_output_basis": natural,
        "best_by_anf": result["best_by_anf"],
        "best_by_abc": result["best_by_abc"],
    }, indent=2))


if __name__ == "__main__":
    main()
