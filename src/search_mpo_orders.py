"""Bounded random search for low-bond-dimension MPO axis orders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from mpo_target import DEFAULT_ORDER, ordered_tensor, tt_ranks


def search(samples: int, seed: int, output: str | Path) -> dict:
    rng = np.random.default_rng(seed)
    orders = [tuple(DEFAULT_ORDER), tuple(range(12)), tuple(reversed(range(12)))]
    orders.extend(tuple(int(x) for x in rng.permutation(12)) for _ in range(samples))
    rows = []
    for order in orders:
        ranks = tt_ranks(ordered_tensor(order))
        rows.append({"order": list(order), "ranks": ranks, "max_rank": max(ranks)})
    report = {
        "samples": samples,
        "seed": seed,
        "best_sample": min(rows, key=lambda row: row["max_rank"]),
        "results": rows,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--output", default="artifacts/mpo_native/order_search.json")
    args = parser.parse_args()
    print(json.dumps(search(args.samples, args.seed, args.output), indent=2))
