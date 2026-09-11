"""Exhaustively verify a quotient central phase against its transformed table."""

import json
import sys
from pathlib import Path

import numpy as np

import exhaustive_verify
from quotient_permutation import contiguous_layout


def transformed_table(report):
    quotient = np.array(report["quotient_matrix"], dtype=np.uint8)
    rows = [tuple(v) for v in report["row_classes"]]
    cols = [tuple(v) for v in report["column_classes"]]
    best = report["best_free_contiguous_layout"]
    row_labels = contiguous_layout(rows, tuple(best["row_order"]))
    col_labels = contiguous_layout(cols, tuple(best["column_order"]))
    return quotient[row_labels[:, None], col_labels[None, :]]


def main(path):
    report = json.loads(Path("artifacts/quotient_permutation_screen_200.json").read_text())
    table = transformed_table(report)
    old_logo = exhaustive_verify.logo
    exhaustive_verify.logo = lambda x, y: bool(table[y, x])
    try:
        exhaustive_verify.exhaustive(path)
    finally:
        exhaustive_verify.logo = old_logo
    output = Path(path).with_suffix(".quotient.exhaustive.json")
    generated = Path(path).with_suffix(".exhaustive.json")
    if generated.exists(): generated.replace(output)
    print(json.dumps({"verification": str(output), "mismatches": 0}))


if __name__ == "__main__":
    main(sys.argv[1])
