"""Deterministic bounded affine-basis screen for exact MD metrics."""

from __future__ import annotations

import json
import random
from pathlib import Path

from md_xag import N_INPUTS, N_POINTS, build_balanced_anf_xag, logo_truth_table, truth_table_sha256


ROOT = Path(__file__).resolve().parents[1]


def apply_basis(point: int, rows: list[int], offset: int) -> int:
    result = offset
    for row, mask in enumerate(rows):
        if (mask & point).bit_count() & 1:
            result ^= 1 << row
    return result


def transformed_values(rows: list[int], offset: int) -> list[int]:
    target = logo_truth_table()
    return [
        (target >> apply_basis(point, rows, offset)) & 1
        for point in range(N_POINTS)
    ]


def key(metrics: dict) -> tuple[int, int, int, int]:
    return (
        metrics["multiplicative_depth"],
        metrics["nonlinear_live_width_estimate"],
        max(metrics["and_layer_widths"], default=0),
        metrics["and_count"],
    )


def main() -> None:
    rng = random.Random(20260910)
    rows = [1 << i for i in range(N_INPUTS)]
    offset = 0
    candidates = []
    for trial in range(129):
        values = transformed_values(rows, offset)
        graph = build_balanced_anf_xag(values)
        target = sum(value << point for point, value in enumerate(values))
        metrics = graph.metrics(target)
        candidates.append({
            "trial": trial,
            "rows": rows[:],
            "offset": offset,
            "metrics": metrics,
        })
        # A bounded random walk over invertible elementary row operations.
        if trial + 1 < 129:
            if rng.random() < 0.85:
                a, b = rng.sample(range(N_INPUTS), 2)
                rows[a] ^= rows[b]
            elif rng.random() < 0.5:
                a, b = rng.sample(range(N_INPUTS), 2)
                rows[a], rows[b] = rows[b], rows[a]
            else:
                offset ^= 1 << rng.randrange(N_INPUTS)

    best = min(candidates, key=lambda candidate: key(candidate["metrics"]))
    out = {
        "seed": 20260910,
        "trials": len(candidates),
        "mutation_family": "invertible elementary row XOR, swaps, and complements",
        "target_truth_table_sha256": truth_table_sha256(logo_truth_table()),
        "best": best,
        "identity": candidates[0],
        "distinct_metric_keys": len({key(candidate["metrics"]) for candidate in candidates}),
    }
    path = ROOT / "artifacts/multiplicative_depth/affine/anf_basis_search.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
