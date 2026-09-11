"""Mathematical screen for a shared-address descriptor architecture.

This deliberately stops before QASM generation.  It asks whether exact row
and column quotient descriptors can make the middle phase kernel small after
optimizing the binary labels of the reachable classes.
"""

import hashlib
import json
import random
from pathlib import Path

import numpy as np

from search import logo

N = 64


def table():
    return np.array([[int(logo(x, y)) for x in range(N)] for y in range(N)], dtype=np.uint8)


def classes(t, transpose=False):
    source = t.T if transpose else t
    groups = {}
    for i, row in enumerate(source):
        groups.setdefault(tuple(int(v) for v in row), []).append(i)
    return sorted((tuple(v) for v in groups.values()), key=lambda v: v[0])


def quotient_descriptors(t):
    ys, xs = classes(t), classes(t, True)
    dy = {y: i for i, group in enumerate(ys) for y in group}
    dx = {x: i for i, group in enumerate(xs) for x in group}
    return ys, xs, dy, dx


def kernel_table(t, dy, dx, row_order, col_order, completion=()):
    """Return the descriptor kernel, optionally completing unreachable cells."""
    out = np.full((256,), 255, dtype=np.uint8)
    for y in range(N):
        for x in range(N):
            address = (row_order[dy[y]] << 4) | col_order[dx[x]]
            value = int(t[y, x])
            if out[address] not in (255, value):
                raise AssertionError("quotient descriptor is not well-defined")
            out[address] = value
    out[out == 255] = 0
    for address in completion:
        if address in {((row_order[dy[y]] << 4) | col_order[dx[x]])
                       for y in range(N) for x in range(N)}:
            raise ValueError(f"completion address {address} is reachable")
        out[address] ^= 1
    return out


def anf_metrics(values):
    a = values.copy()
    for bit in range(8):
        step = 1 << bit
        for start in range(0, 256, 2 * step):
            a[start + step:start + 2 * step] ^= a[start:start + step]
    terms = [i for i, value in enumerate(a) if value]
    return {
        "anf_terms": len(terms),
        "anf_literal_cost": sum(i.bit_count() for i in terms),
        "anf_max_degree": max((i.bit_count() for i in terms), default=0),
        "anf_support_masks": terms,
    }


def metrics(values):
    out = anf_metrics(values)
    out["marked_descriptor_addresses"] = int(values.sum())
    out["walsh_nonzero_support"] = int(np.count_nonzero(
        np.array([1 - 2 * int(v) for v in values], dtype=np.int64)
    ))  # populated below with an exact FWHT
    w = np.array([1 - 2 * int(v) for v in values], dtype=np.int64)
    h = 1
    while h < 256:
        for start in range(0, 256, 2 * h):
            left, right = w[start:start + h].copy(), w[start + h:start + 2 * h].copy()
            w[start:start + h], w[start + h:start + 2 * h] = left + right, left - right
        h *= 2
    out["walsh_nonzero_support"] = int(np.count_nonzero(w))
    return out


def main(samples=2000, seed=20260911):
    t = table()
    ys, xs, dy, dx = quotient_descriptors(t)
    base_rows, base_cols = tuple(range(len(ys))), tuple(range(len(xs)))
    rng = random.Random(seed)
    best = None
    for sample in range(samples):
        rows = base_rows if sample == 0 else tuple(rng.sample(range(16), len(base_rows)))
        cols = base_cols if sample == 0 else tuple(rng.sample(range(16), len(base_cols)))
        values = kernel_table(t, dy, dx, rows, cols)
        m = metrics(values)
        key = (m["anf_literal_cost"], m["anf_terms"], m["anf_max_degree"])
        if best is None or key < best[0]:
            best = (key, {"row_order": list(rows), "column_order": list(cols),
                          "completion": [], "metrics": m})
    witness_rows = (10, 1, 4, 3, 2, 7, 9, 6, 5, 11, 15)
    witness_cols = (2, 13, 8, 3, 14, 12, 11, 15, 5, 9, 7)
    witness_completion = (186, 220, 223)
    witness_values = kernel_table(t, dy, dx, witness_rows, witness_cols, witness_completion)
    witness = {"row_order": list(witness_rows), "column_order": list(witness_cols),
               "completion": list(witness_completion), "metrics": metrics(witness_values)}
    report = {
        "descriptor": "dy=row-pattern class, dx=column-pattern class",
        "row_class_count": len(ys), "column_class_count": len(xs),
        "required_descriptor_bits": {"dy": 4, "dx": 4},
        "row_classes": [list(g) for g in ys],
        "column_classes": [list(g) for g in xs],
        "marked_pixels_original": int(t.sum()),
        "marked_descriptor_pairs": int(sum(int(v) for v in
                                            kernel_table(t, dy, dx, base_rows, base_cols))),
        "baseline_natural": {"row_order": list(base_rows), "column_order": list(base_cols),
                             "metrics": metrics(kernel_table(t, dy, dx, base_rows, base_cols))},
        "best_label_screen": best[1], "known_reachable_completion_witness": witness,
        "samples": samples, "seed": seed,
        "exact_table_sha256": hashlib.sha256(t.tobytes()).hexdigest(),
        "status": "mathematical descriptor/kernel screen; no reversible QROM circuit claimed",
    }
    path = Path("artifacts/shared_address_descriptor/descriptor_report.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"rows": len(ys), "columns": len(xs),
                      "best": best[1]["metrics"],
                      "witness": witness["metrics"], "path": str(path)}, indent=2))


if __name__ == "__main__":
    main()
