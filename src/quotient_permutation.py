"""Optimistic free-layout screen for in-place quotient conjugation.

The six x bits and six y bits are treated as data registers, not as inputs to
a class-code loader.  Rows (respectively columns) with identical 64-bit
patterns are quotient classes.  This module assigns those classes to binary
addresses for free, expands the exact transformed 64x64 truth table, and
measures classical/native-oriented proxies before attempting reversible
permutation synthesis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from search import logo
from mcz import phase_cube


SIZE = 64
N = 12


def matrix() -> np.ndarray:
    return np.array(
        [[int(logo(x, y)) for x in range(SIZE)] for y in range(SIZE)], dtype=np.uint8
    )


def quotient_classes(table: np.ndarray, axis: int) -> list[tuple[int, ...]]:
    rows = table if axis == 0 else table.T
    groups: dict[tuple[int, ...], list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(tuple(int(v) for v in row), []).append(index)
    return sorted((tuple(indices) for indices in groups.values()), key=lambda c: c[0])


def quotient_data(table: np.ndarray) -> tuple[list[tuple[int, ...]], list[tuple[int, ...]], np.ndarray]:
    rows = quotient_classes(table, 0)
    columns = quotient_classes(table, 1)
    row_id = {address: i for i, group in enumerate(rows) for address in group}
    column_id = {address: i for i, group in enumerate(columns) for address in group}
    quotient = np.array(
        [[int(table[group_y[0], group_x[0]]) for group_x in columns] for group_y in rows],
        dtype=np.uint8,
    )
    assert np.array_equal(
        table,
        np.array([[quotient[row_id[y], column_id[x]] for x in range(SIZE)] for y in range(SIZE)]),
    )
    return rows, columns, quotient


def contiguous_layout(classes: list[tuple[int, ...]], order: tuple[int, ...]) -> np.ndarray:
    labels = np.empty(SIZE, dtype=np.uint8)
    cursor = 0
    for label in order:
        for _ in classes[label]:
            labels[cursor] = label
            cursor += 1
    assert cursor == SIZE
    return labels


def transformed_table(quotient: np.ndarray, row_labels: np.ndarray, column_labels: np.ndarray) -> np.ndarray:
    return quotient[row_labels[:, None], column_labels[None, :]].astype(np.uint8)


def anf_terms(table: np.ndarray) -> list[int]:
    values = np.array(
        [int(table[z >> 6, z & 63]) for z in range(1 << N)], dtype=np.uint8
    )
    for bit in range(N):
        step = 1 << bit
        for start in range(0, len(values), step * 2):
            values[start + step : start + step * 2] ^= values[start : start + step]
    return [mask for mask, value in enumerate(values) if value]


def reduced_bdd_nodes(table: np.ndarray, order: tuple[int, ...] = tuple(range(N))) -> int:
    """Count nonterminal nodes in a reduced ordered BDD for the exact table."""
    truth = tuple(int(table[z >> 6, z & 63]) for z in range(1 << N))
    unique: dict[tuple[int, int, int], int] = {}
    terminals = {0: 0, 1: 1}

    @lru_cache(None)
    def build(level: int, indices: tuple[int, ...]) -> int:
        if not indices:
            return 0
        first = truth[indices[0]]
        if all(truth[index] == first for index in indices):
            return terminals[first]
        bit = order[level]
        lo = tuple(index for index in indices if not (index & (1 << bit)))
        hi = tuple(index for index in indices if index & (1 << bit))
        low_node = build(level + 1, lo)
        high_node = build(level + 1, hi)
        if low_node == high_node:
            return low_node
        key = (bit, low_node, high_node)
        if key not in unique:
            unique[key] = len(unique) + 2
        return unique[key]

    build(0, tuple(range(1 << N)))
    return len(unique)


def dyadic_cover(table: np.ndarray) -> dict:
    """Greedily cover marked points by binary-aligned dyadic rectangles.

    This is an upper-bound proxy, not a minimum-cover claim.  Rectangles are
    restricted to subcubes in the x and y addresses, which mirrors a compact
    positive-control MCZ/ESOP term.
    """
    remaining = {(x, y) for y in range(SIZE) for x in range(SIZE) if table[y, x]}
    rectangles = []
    for wx in range(6, -1, -1):
        sx = 1 << wx
        for wy in range(6, -1, -1):
            sy = 1 << wy
            for x0 in range(0, SIZE, sx):
                for y0 in range(0, SIZE, sy):
                    points = {(x, y) for y in range(y0, y0 + sy) for x in range(x0, x0 + sx)}
                    hit = points & remaining
                    if hit == points and hit:
                        rectangles.append((len(hit), 12 - wx - wy, x0, y0, sx, sy))
    rectangles.sort(reverse=True)
    chosen = []
    for _, literals, x0, y0, sx, sy in rectangles:
        points = {(x, y) for y in range(y0, y0 + sy) for x in range(x0, x0 + sx)}
        if points <= remaining:
            remaining -= points
            chosen.append((literals, x0, y0, sx, sy))
        if not remaining:
            break
    return {
        "rectangles": len(chosen),
        "literal_cost": int(sum(item[0] for item in chosen)),
        "uncovered": len(remaining),
        "selected_rectangles": [list(item) for item in chosen],
    }


def metrics(table: np.ndarray) -> dict:
    terms = anf_terms(table)
    cover = dyadic_cover(table)
    return {
        "marked_points": int(table.sum()),
        "anf_terms": len(terms),
        "anf_literal_cost": int(sum(mask.bit_count() for mask in terms)),
        "anf_max_degree": max((mask.bit_count() for mask in terms), default=0),
        "reduced_bdd_nodes": reduced_bdd_nodes(table),
        "dyadic_cover": cover,
        "exact_table_sha256": hashlib.sha256(table.tobytes()).hexdigest(),
    }


def search_free_layouts(samples: int, seed: int) -> dict:
    table = matrix()
    rows, columns, quotient = quotient_data(table)
    row_populations = [len(group) for group in rows]
    column_populations = [len(group) for group in columns]
    base_row = tuple(range(len(rows)))
    base_col = tuple(range(len(columns)))
    baseline = metrics(table)
    rng = random.Random(seed)
    best = None
    for sample in range(samples):
        row_order = base_row if sample == 0 else tuple(rng.sample(base_row, len(base_row)))
        column_order = base_col if sample == 0 else tuple(rng.sample(base_col, len(base_col)))
        candidate = transformed_table(
            quotient,
            contiguous_layout(rows, row_order),
            contiguous_layout(columns, column_order),
        )
        result = {
            "row_order": list(row_order),
            "column_order": list(column_order),
            "metrics": metrics(candidate),
        }
        score = (
            result["metrics"]["reduced_bdd_nodes"],
            result["metrics"]["dyadic_cover"]["literal_cost"],
            result["metrics"]["anf_literal_cost"],
            result["metrics"]["anf_terms"],
        )
        if best is None or score < best[0]:
            best = (score, result)
    return {
        "class_count": {"rows": len(rows), "columns": len(columns)},
        "row_classes": [list(group) for group in rows],
        "column_classes": [list(group) for group in columns],
        "row_populations": row_populations,
        "column_populations": column_populations,
        "quotient_matrix": quotient.tolist(),
        "baseline_natural_layout": baseline,
        "best_free_contiguous_layout": best[1],
        "samples": samples,
        "seed": seed,
        "screen_note": "Class permutations are free and contiguous class blocks are an optimistic restricted layout family; no reversible permutation circuit is synthesized.",
    }


def compile_dyadic_central(table: np.ndarray, output: Path) -> dict:
    """Compile the greedy disjoint dyadic cover as an exact central diagnostic."""
    cover = dyadic_cover(table)
    q = QuantumCircuit(18)
    for literals, x0, y0, sx, sy in cover["selected_rectangles"]:
        cube = []
        for bit in range(6):
            if not (sx & (1 << bit)):
                cube.append(bit + 1 if x0 & (1 << bit) else -(bit + 1))
        for bit in range(6):
            if not (sy & (1 << bit)):
                variable = 6 + bit + 1
                cube.append(variable if y0 & (1 << bit) else -variable)
        phase_cube(q, frozenset(cube), [])
    compiled = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(qasm2.dumps(compiled))
    return {
        "depth": compiled.depth(),
        "cx_count": int(compiled.count_ops().get("cx", 0)),
        "width": compiled.num_qubits,
        "rectangles": cover["rectangles"],
        "literal_cost": cover["literal_cost"],
        "qasm": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/quotient_permutation_screen.json"))
    parser.add_argument("--compile-best-central", action="store_true")
    args = parser.parse_args()
    report = search_free_layouts(args.samples, args.seed)
    if args.compile_best_central:
        best = report["best_free_contiguous_layout"]
        rows = [tuple(group) for group in report["row_classes"]]
        columns = [tuple(group) for group in report["column_classes"]]
        quotient = np.array(report["quotient_matrix"], dtype=np.uint8)
        transformed = transformed_table(
            quotient,
            contiguous_layout(rows, tuple(best["row_order"])),
            contiguous_layout(columns, tuple(best["column_order"])),
        )
        report["best_free_contiguous_layout"]["central_compile"] = compile_dyadic_central(
            transformed, Path("artifacts/quotient_permutation_best_central.qasm")
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
