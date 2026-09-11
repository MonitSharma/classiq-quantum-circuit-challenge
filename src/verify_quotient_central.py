"""Exhaustively verify a quotient central phase against its transformed table."""

import json
import sys
import argparse
import hashlib
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


def main(path, source_report_path):
    source_path = Path(source_report_path)
    report = json.loads(source_path.read_text())
    table = transformed_table(report)
    old_logo = exhaustive_verify.logo
    exhaustive_verify.logo = lambda x, y: bool(table[y, x])
    try:
        exhaustive_verify.exhaustive(path)
    finally:
        exhaustive_verify.logo = old_logo
    output = Path(path).with_suffix(".quotient.exhaustive.json")
    generated = Path(path).with_suffix(".exhaustive.json")
    if not generated.exists():
        raise RuntimeError("exhaustive verifier did not produce a report")
    result = json.loads(generated.read_text())
    result["provenance"] = {
        "source_report": str(source_path.resolve()),
        "source_report_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "transformed_table_sha256": hashlib.sha256(table.tobytes()).hexdigest(),
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    generated.unlink()
    print(json.dumps({"verification": str(output), "mismatches": 0,
                      "source_report_sha256": result["provenance"]["source_report_sha256"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm")
    parser.add_argument("source_report")
    args = parser.parse_args()
    main(args.qasm, args.source_report)
