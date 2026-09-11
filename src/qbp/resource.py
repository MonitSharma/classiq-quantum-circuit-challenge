"""Native-cost calibration for finite-group width-2 QBP transitions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate

from qbp.finite_group import ELEMENTS, MULTIPLY, GROUP_ORDER


def quaternion_matrix(q: tuple[float, ...]) -> np.ndarray:
    """Map a unit quaternion to its SU(2) fundamental representation."""
    w, x, y, z = q
    return np.array(
        [[w - 1j * z, -y - 1j * x], [y - 1j * x, w + 1j * z]],
        dtype=complex,
    )


def unitary_product(left: int, right: int) -> np.ndarray:
    return quaternion_matrix(ELEMENTS[left]) @ quaternion_matrix(ELEMENTS[right])


def measure(matrix: np.ndarray, controlled: bool) -> dict:
    circuit = QuantumCircuit(2 if controlled else 1)
    gate = UnitaryGate(matrix)
    if controlled:
        circuit.append(gate.control(1), [0, 1])
    else:
        circuit.append(gate, [0])
    lowered = transpile(
        circuit,
        basis_gates=["u3", "cx"],
        optimization_level=0,
        qubits_initially_zero=False,
    )
    return {
        "depth": lowered.depth(),
        "cx": lowered.count_ops().get("cx", 0),
        "ops": dict(lowered.count_ops()),
    }


def main() -> dict:
    root = Path(__file__).resolve().parents[2]
    single = [measure(quaternion_matrix(element), False) for element in ELEMENTS]
    relative = []
    for left in range(GROUP_ORDER):
        for right in range(GROUP_ORDER):
            # U_left^dagger U_right is represented by group multiplication
            # inverse(left) * right; the matrix route keeps this calibration
            # independent of a chosen Euler-angle convention.
            matrix = quaternion_matrix(ELEMENTS[left]).conj().T @ quaternion_matrix(ELEMENTS[right])
            relative.append(measure(matrix, True))
    result = {
        "kind": "finite-group QBP native transition calibration",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "group": "binary_icosahedral",
        "group_order": GROUP_ORDER,
        "single_qubit": {
            "max_depth": max(item["depth"] for item in single),
            "max_cx": max(item["cx"] for item in single),
            "distinct_depths": sorted({item["depth"] for item in single}),
        },
        "controlled_relative": {
            "max_depth": max(item["depth"] for item in relative),
            "max_cx": max(item["cx"] for item in relative),
            "distinct_depths": sorted({item["depth"] for item in relative}),
            "distinct_cx": sorted({item["cx"] for item in relative}),
        },
        "interpretation": "A QBP instruction can be factored into an uncontrolled base and a controlled relative unitary; this is only a transition estimate, not a complete clean phase oracle.",
    }
    path = root / "artifacts/unitary_state_space/qbp/native_transition_calibration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
