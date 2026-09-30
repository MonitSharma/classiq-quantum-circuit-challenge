"""Generate care-state truth mappings for feature subsets.

The output is a compact, backend-neutral StateSystem-style description of the
64 legal inputs |y>|0...0>.  It records exact basis-state targets and leaves
the per-input phase unconstrained for a later semantic synthesizer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from radius import R, radius
from search import truth


FEATURES = {
    "R0": lambda y: (radius(y) >> 0) & 1,
    "R1": lambda y: (radius(y) >> 1) & 1,
    "R2": lambda y: (radius(y) >> 2) & 1,
    "A": lambda y: int(29 <= y <= 53),
    "B": lambda y: int(39 <= y <= 43),
    "V": lambda y: int(radius(y) > 0),
}


def mapping(names):
    rows = []
    for y in range(64):
        bits = [FEATURES[name](y) for name in names]
        rows.append({"y": y, "input": [y] + [0] * len(names),
                     "outputs": bits, "target": [y] + bits})
    return {"feature_names": list(names), "care_state_count": 64,
            "input_qubits": 6 + len(names), "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pairs = [("R0", "R1"), ("R1", "R2"), ("A", "B"), ("A", "B", "V")]
    result = {"source": "authoritative radius and row predicates", "mappings": [mapping(x) for x in pairs]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"mapping_count": len(pairs), "care_states_each": 64,
                      "feature_sets": [list(x) for x in pairs]}, indent=2))


if __name__ == "__main__":
    main()
