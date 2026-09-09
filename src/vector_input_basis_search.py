"""Search affine changes of basis on the six y inputs for joint loading."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows

ROOT = Path(__file__).resolve().parents[1]
ABC = ROOT / "experiments/abc/abc"
INPUT_MATRIX = (1, 2, 4, 40, 16, 48)
INPUT_OFFSET = 16


def invert(rows: tuple[int, ...]) -> tuple[int, ...]:
    """Invert a 6x6 binary matrix represented by output-bit row masks."""
    work = [(rows[i], 1 << i) for i in range(6)]
    for bit in range(6):
        pivot = next(i for i in range(bit, 6) if work[i][0] & (1 << bit))
        work[bit], work[pivot] = work[pivot], work[bit]
        for i in range(6):
            if i != bit and work[i][0] & (1 << bit):
                work[i] = (work[i][0] ^ work[bit][0], work[i][1] ^ work[bit][1])
    return tuple(work[i][1] for i in range(6))


def transform_y(z: int, matrix_inverse: tuple[int, ...], offset: int) -> int:
    source = z ^ offset
    return sum(((matrix_inverse[row].bit_count() and
                 ((matrix_inverse[row] & source).bit_count() & 1)) << row)
               for row in range(6))


def matrix_random(rng: random.Random) -> tuple[int, ...]:
    rows = [1 << i for i in range(6)]
    for _ in range(rng.randint(1, 18)):
        target, control = rng.sample(range(6), 2)
        rows[target] ^= rows[control]
    return tuple(rows)


def baseline_tables() -> dict[str, list[int]]:
    rows = truth_rows()
    return {name: [row[name] for row in rows] for name in FEATURES}


def score(matrix: tuple[int, ...], offset: int, tables: dict[str, list[int]]) -> dict:
    inv = invert(matrix)
    transformed = {
        name: [tables[name][transform_y(z, inv, offset)] for z in range(64)]
        for name in FEATURES
    }
    supports = {name: set(anf_monomials(values)) for name, values in transformed.items()}
    union = set().union(*supports.values())
    return {
        "matrix_rows": list(matrix),
        "offset": offset,
        "anf_union": len(union),
        "anf_terms": sum(len(items) for items in supports.values()),
        "max_degree": max((item.bit_count() for item in union), default=0),
        "cnot_pre_post_proxy": sum(row.bit_count() - 1 for row in matrix) * 2,
    }


def write_pla(candidate: dict, tables: dict[str, list[int]], path: Path) -> None:
    inv = invert(tuple(candidate["matrix_rows"]))
    transformed = {
        name: [tables[name][transform_y(z, inv, candidate["offset"])] for z in range(64)]
        for name in FEATURES
    }
    lines = [".i 6", ".o 5", ".ilb z0 z1 z2 z3 z4 z5",
             ".ob " + " ".join(FEATURES)]
    for z in range(64):
        inputs = "".join(str((z >> bit) & 1) for bit in range(6))
        outputs = "".join(str(transformed[name][z]) for name in FEATURES)
        lines.append(f"{inputs} {outputs}")
    lines.append(".e")
    path.write_text("\n".join(lines) + "\n")


def abc_score(candidate: dict, tables: dict[str, list[int]], index: int) -> dict:
    pla = ARTIFACTS / f"vector_input_basis_{index:03d}.pla"
    bench = ARTIFACTS / f"vector_input_basis_{index:03d}.bench"
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
    matrices = {tuple(1 << i for i in range(6))}
    while len(matrices) < 256:
        matrices.add(matrix_random(rng))
    tables = baseline_tables()
    candidates = [score(matrix, offset, tables)
                  for matrix in sorted(matrices) for offset in range(64)]
    candidates.sort(key=lambda item: (item["anf_union"], item["anf_terms"],
                                      item["cnot_pre_post_proxy"]))
    selected = candidates[:64]
    abc = [abc_score(item, tables, i) for i, item in enumerate(selected)]
    natural = score(tuple(1 << i for i in range(6)), 0, tables)
    result = {
        "matrices": len(matrices),
        "affine_input_encodings_scored": len(candidates),
        "abc_candidates": len(abc),
        "natural_basis": natural,
        "best_by_anf": selected[0],
        "best_by_abc": min(abc, key=lambda item: (
            item["abc_level"] if item["abc_level"] is not None else 10**9,
            item["abc_and"] if item["abc_and"] is not None else 10**9,
        )),
        "candidates": abc,
        "note": "Irreversible screening only; pre/post linear synthesis and reversible loading remain to be compiled.",
    }
    (ARTIFACTS / "vector_input_basis_search.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({
        "matrices": len(matrices),
        "encodings": len(candidates),
        "natural": natural,
        "best_by_anf": result["best_by_anf"],
        "best_by_abc": result["best_by_abc"],
    }, indent=2))


if __name__ == "__main__":
    main()
