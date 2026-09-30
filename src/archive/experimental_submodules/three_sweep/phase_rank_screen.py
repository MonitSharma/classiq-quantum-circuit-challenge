"""Rank screen for five-coordinate phase-control partitions."""

import itertools
import json
from pathlib import Path

import numpy as np

from search import logo


def gf2_rank(matrix: np.ndarray) -> int:
    rows = [sum(int(matrix[r, c]) << c for c in range(matrix.shape[1]))
            for r in range(matrix.shape[0])]
    rank = 0
    for col in range(matrix.shape[1]):
        pivot = next((r for r in range(rank, len(rows)) if (rows[r] >> col) & 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(len(rows)):
            if r != rank and ((rows[r] >> col) & 1):
                rows[r] ^= rows[rank]
        rank += 1
    return rank


def target_table() -> np.ndarray:
    # Coordinates are ordered by logical bit index: x0..x5,y0..y5.
    return np.array([
        int(logo(x, y))
        for y in range(64)
        for x in range(64)
    ], dtype=np.uint8)


def partition_matrix(table: np.ndarray, chosen: tuple[int, ...]) -> np.ndarray:
    chosen = tuple(chosen)
    rest = tuple(i for i in range(12) if i not in chosen)
    matrix = np.zeros((1 << len(chosen), 1 << len(rest)), dtype=np.uint8)
    for row in range(1 << len(chosen)):
        for col in range(1 << len(rest)):
            bits = 0
            for j, bit in enumerate(chosen):
                bits |= ((row >> j) & 1) << bit
            for j, bit in enumerate(rest):
                bits |= ((col >> j) & 1) << bit
            x = bits & 0x3F
            y = (bits >> 6) & 0x3F
            matrix[row, col] = table[y * 64 + x]
    return matrix


def screen() -> dict:
    table = target_table()
    results = []
    for chosen in itertools.combinations(range(12), 5):
        matrix = partition_matrix(table, chosen)
        sign = 1 - 2 * matrix.astype(np.int8)
        results.append({
            "chosen_bits": list(chosen),
            "gf2_rank": gf2_rank(matrix),
            "real_rank": int(np.linalg.matrix_rank(matrix)),
            "sign_rank": int(np.linalg.matrix_rank(sign)),
            "distinct_rows": int(len({tuple(row) for row in matrix})),
            "distinct_columns": int(len({tuple(matrix[:, c]) for c in range(matrix.shape[1])})),
        })
    results.sort(key=lambda row: (row["sign_rank"], row["real_rank"], row["gf2_rank"]))
    return {"partitions": len(results), "results": results}


def write(path="artifacts/three_sweep/five_control_partition_screen.json"):
    report = screen()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"partitions": report["partitions"], "best": report["results"][:10]}, indent=2))
    return report


if __name__ == "__main__":
    write()

