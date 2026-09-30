"""Read-only circuit audit and exact classical reduction diagnostics.

Writes a new JSON analysis report; does not synthesize or replace any oracle.
Run from the workspace root with .venv/bin/python.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import qasm2
from search import MASK
from radius import R, radius


def gf2_rank(rows):
    basis = {}
    for row in rows:
        value = int(row)
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


def packed(row):
    return sum(int(v) << i for i, v in enumerate(row))


def split_classes(patterns, bit):
    low = [y for y in range(64) if not (y >> bit) & 1]
    return {
        "selector_bit": bit,
        "classes_in_selector_0": len({patterns[y] for y in low}),
        "classes_in_selector_1": len({patterns[y | (1 << bit)] for y in low}),
        "ordered_cofactor_pair_classes": len({
            (patterns[y], patterns[y | (1 << bit)]) for y in low
        }),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    qasm = root / "artifacts/524/full_mux_feature_linear_tket_524.qasm"
    circuit = qasm2.loads(qasm.read_text())
    report = json.loads(qasm.with_suffix(".exhaustive.json").read_text())
    sha = hashlib.sha256(qasm.read_bytes()).hexdigest()
    assert sha == report["sha256"]
    assert set(circuit.count_ops()) <= {"u3", "cx"}
    touches = [0] * circuit.num_qubits
    for instruction in circuit.data:
        for qubit in instruction.qubits:
            touches[circuit.find_bit(qubit).index] += 1
    rows = [packed(row) for row in MASK]
    cols = [packed(row) for row in MASK.T]
    features = [sum(((t >> y) & 1) << i for i, t in enumerate(R))
                | (int(29 <= y <= 53) << 3)
                | (int(39 <= y <= 43) << 4)
                | (int(radius(y) > 0) << 5) for y in range(64)]
    result = {
        "kind": "exact classical analysis plus existing QASM/report hash audit",
        "best": {"qasm": str(qasm.relative_to(root)), "sha256": sha,
                 "report_hash_matches": True, "depth": circuit.depth(),
                 "cx": circuit.count_ops().get("cx", 0), "width": circuit.num_qubits,
                 "per_wire_operations": touches,
                 "fixed_gate_multiset_depth_lower_bound": max(touches)},
        "marked_pixels": int(MASK.sum()), "distinct_rows": len(set(rows)),
        "distinct_columns": len(set(cols)), "gf2_rank": gf2_rank(rows),
        "row_class_sizes": sorted(Counter(rows).values()),
        "feature_codeword_count": len(set(features)),
        "y_selector_splits": [split_classes(rows, b) for b in range(6)],
        "x_selector_splits": [split_classes(cols, b) for b in range(6)],
        "one_bit_exact_core_plus_residual": [],
    }
    for axis in ("x", "y"):
        for bit in range(6):
            base = MASK.copy()
            for coord in range(64):
                if axis == "x":
                    base[:, coord] = MASK[:, coord & ~(1 << bit)]
                else:
                    base[coord, :] = MASK[coord & ~(1 << bit), :]
            residual = MASK ^ base
            assert np.array_equal(base ^ residual, MASK)
            result["one_bit_exact_core_plus_residual"].append({
                "axis": axis, "bit": bit, "residual_pixels": int(residual.sum()),
                "core_gf2_rank": gf2_rank([packed(r) for r in base]),
                "residual_gf2_rank": gf2_rank([packed(r) for r in residual]),
                "nonempty_residual_row_patterns": len({packed(r) for r in residual} - {0}),
            })
    # Constant on each 2x2 cell; majority minimizes residual population per cell.
    base = np.zeros_like(MASK)
    for y in range(0, 64, 2):
        for x in range(0, 64, 2):
            base[y:y+2, x:x+2] = int(MASK[y:y+2, x:x+2].sum() > 2)
    residual = base ^ MASK
    assert np.array_equal(base ^ residual, MASK)
    result["two_bit_majority_core"] = {
        "discarded_bits": ["x0", "y0"], "tie_value": 0,
        "residual_pixels": int(residual.sum()),
        "core_gf2_rank": gf2_rank([packed(r) for r in base]),
        "residual_gf2_rank": gf2_rank([packed(r) for r in residual]),
        "warning": "Population and rank are not circuit depth estimates.",
    }
    path = root / "artifacts/research_structure_audit.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
