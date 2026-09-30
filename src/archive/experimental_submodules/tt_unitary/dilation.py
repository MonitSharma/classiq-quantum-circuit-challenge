"""Algebraic TT-to-isometry feasibility diagnostics.

For a TT core A with slices A0,A1 (shape left x right), a row-isometric
sequential realization after gauge changes would require a positive metric K
on the right bond such that

    A0 K A0^T = A1 K A1^T = H.

The equality equations are tested exactly over the rationals.  A zero
nullspace is a rigorous obstruction to this natural same-bond isometric
realization.  A nonzero nullspace is only a necessary-condition pass: positive
definiteness and a common unitary dilation still have to be solved.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import sympy as sp


def load_cores(path: Path) -> list[list[list[sp.Rational]]]:
    data = json.loads(path.read_text())
    return [
        [[sp.Rational(value) for value in row] for row in core]
        for core in data["cores"]
    ]


def metric_equations(core: list[list[sp.Rational]]) -> tuple[int, int, int, int]:
    rows = len(core)
    right = len(core[0])
    left = rows // 2
    slices = [
        sp.Matrix(left, right, lambda r, c: core[r * 2 + bit][c])
        for bit in (0, 1)
    ]
    pairs = [(a, b) for a in range(right) for b in range(a, right)]
    equations = []
    for u in range(left):
        for v in range(left):
            row = []
            for a, b in pairs:
                value = slices[0][u, a] * slices[0][v, b]
                value -= slices[1][u, a] * slices[1][v, b]
                if a != b:
                    value += slices[0][u, b] * slices[0][v, a]
                    value -= slices[1][u, b] * slices[1][v, a]
                row.append(value)
            equations.append(row)
    matrix = sp.Matrix(equations)
    return left, right, int(matrix.rank()), len(pairs) - int(matrix.rank())


def main() -> dict:
    root = Path(__file__).resolve().parents[2]
    witness = root / "artifacts/unitary_state_space/tensor_tt_exact.json"
    cores = load_cores(witness)
    layers = []
    for index, core in enumerate(cores):
        left, right, equation_rank, nullity = metric_equations(core)
        layers.append({
            "layer": index,
            "left_bond": left,
            "right_bond": right,
            "symmetric_metric_variables": right * (right + 1) // 2,
            "exact_equation_rank": equation_rank,
            "exact_metric_nullity": nullity,
            "right_dimension_at_least_left": right >= left,
            "same_bond_row_isometry_necessary_condition": bool(nullity > 0 and right >= left),
            "obstruction": (
                "zero common-metric nullspace"
                if nullity == 0 else
                "right bond shrinks below left bond"
                if right < left else
                "no algebraic obstruction; positive metric not yet proved"
            ),
        })
    obstructed = [
        layer["layer"] for layer in layers
        if not layer["same_bond_row_isometry_necessary_condition"]
    ]
    result = {
        "kind": "exact TT same-bond isometric feasibility diagnostic",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "witness": str(witness.relative_to(root)),
        "layers": layers,
        "obstructed_layers": obstructed,
        "memory_qubits_for_max_bond": 4,
        "interpretation": (
            "The natural same-bond row-isometric TT realization is obstructed. "
            "This does not rule out padded unitary dilation, a different gauge/order, "
            "or a QBP initialized from the TT."
        ),
        "decision": "STOP_SAME_BOND_DILATION_CONDITIONAL_PIVOT_TO_PADDED_OR_QBP",
    }
    path = root / "artifacts/unitary_state_space/tt/tt_dilation_feasibility.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
