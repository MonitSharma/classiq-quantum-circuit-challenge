"""One-step screen for positive and complemented controlled swaps."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from destructive_semantic_search import (
    ALL_ONES,
    TARGET,
    affine_distance_proxy,
    exact_affine_distance,
    initial_wire_truth_tables,
)


def apply_signed_cswap(wires, control: int, negative: bool, a: int, b: int):
    predicate = ALL_ONES ^ wires[control] if negative else wires[control]
    delta = predicate & (wires[a] ^ wires[b])
    out = list(wires)
    out[a] ^= delta
    out[b] ^= delta
    return tuple(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    wires = initial_wire_truth_tables()
    best = None
    count = 0
    for control in range(18):
        for negative in (False, True):
            for a, b in itertools.combinations(
                [wire for wire in range(18) if wire != control], 2
            ):
                child = apply_signed_cswap(wires, control, negative, a, b)
                residual, combo = affine_distance_proxy(child, TARGET, 2)
                row = (residual, count, control, negative, a, b, combo, child)
                if best is None or row[:1] < best[:1]:
                    best = row
                count += 1
    assert best is not None
    exact, exact_combo = exact_affine_distance(best[-1], TARGET)
    result = {
        "experiment": "signed controlled-swap one-step semantic screen",
        "moves_checked": count,
        "target_marked_states": TARGET.bit_count(),
        "best_proxy_residual": best[0],
        "best_exact_residual": exact,
        "best_exact_combo": exact_combo,
        "best_move": {
            "control": best[2], "negative_control": best[3],
            "swap": [best[4], best[5]],
        },
        "status": "semantic_screen_only; no affine completion",
    }
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
