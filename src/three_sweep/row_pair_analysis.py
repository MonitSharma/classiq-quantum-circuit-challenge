"""Reconstruct the low-y ordered row-pair classes exactly.

The experiment keeps y5 as a live coordinate bit and compresses only the
ordered pair of x masks for y=z and y=z+32.  This is deliberately independent
of the older six-input class-oracle implementation.
"""

import json
from collections import Counter, OrderedDict
from pathlib import Path

from search import logo


def row_mask(y: int) -> int:
    return sum((1 << x) for x in range(64) if logo(x, y))


def analyze() -> dict:
    classes: OrderedDict[tuple[int, int], int] = OrderedDict()
    rows = []
    for z in range(32):
        pair = (row_mask(z), row_mask(z + 32))
        pair_class = classes.setdefault(pair, len(classes))
        rows.append({
            "z": z,
            "lower_y": z,
            "upper_y": z + 32,
            "row0_mask": pair[0],
            "row1_mask": pair[1],
            "pair_class": pair_class,
        })
    multiplicities = Counter(row["pair_class"] for row in rows)
    return {
        "control_definition": "z=y&31, b=y>>5",
        "distinct_pair_count": len(classes),
        "expected_information_bits": 5,
        "rows": rows,
        "class_multiplicities": {
            str(k): v for k, v in sorted(multiplicities.items())
        },
        "classes": [
            {"pair_class": i, "row0_mask": pair[0], "row1_mask": pair[1]}
            for i, pair in enumerate(classes)
        ],
    }


def codebook(result: dict) -> dict:
    """Return a deterministic five-bit codebook, fixing class 0 at zero."""
    assignments = {str(i): i for i in range(result["distinct_pair_count"])}
    return {
        "scheme": "deterministic_class_index",
        "bits": 5,
        "class_to_code": assignments,
        "z_to_code": {
            str(row["z"]): assignments[str(row["pair_class"])]
            for row in result["rows"]
        },
    }


def write_artifacts(directory: str | Path = "artifacts/three_sweep") -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    result = analyze()
    (directory / "row_pairs.json").write_text(json.dumps(result, indent=2) + "\n")
    (directory / "codebook_deterministic.json").write_text(
        json.dumps(codebook(result), indent=2) + "\n"
    )


if __name__ == "__main__":
    write_artifacts()
    result = analyze()
    print(json.dumps({
        "distinct_pair_count": result["distinct_pair_count"],
        "class_multiplicities": result["class_multiplicities"],
    }, indent=2))

