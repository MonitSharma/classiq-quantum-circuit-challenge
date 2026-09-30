"""Pilot a reversible local-coordinate transform for the two disk centers.

For y5=0 the low five bits are translated by -19 modulo 32; for y5=1 they
are translated by -9 modulo 32.  The transform preserves y5 and uses no
ancillas.  It is a loader-independent fallback experiment, not a complete
logo oracle.
"""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from vector_feature_analysis import ARTIFACTS


Y = list(range(6, 11))
Y5 = 11
SCRATCH = [15, 16, 17]


def controlled_flip(q: QuantumCircuit, controls: list[int], target: int) -> None:
    if not controls:
        q.x(target)
    elif len(controls) == 1:
        q.cx(controls[0], target)
    elif len(controls) == 2:
        q.ccx(controls[0], controls[1], target)
    else:
        q.mcx(controls, target, ancilla_qubits=SCRATCH[:len(controls) - 2],
              mode="v-chain")


def add_power_of_two(q: QuantumCircuit, branch: int, start: int) -> None:
    """Add 2**start modulo 32, controlled by branch, in-place on y0..y4."""
    for bit in range(4, start, -1):
        controlled_flip(q, [branch, *Y[start:bit]], Y[bit])
    controlled_flip(q, [branch], Y[start])


def add_constant(q: QuantumCircuit, branch: int, value: int) -> None:
    for bit in range(5):
        if value & (1 << bit):
            add_power_of_two(q, branch, bit)


def build() -> QuantumCircuit:
    q = QuantumCircuit(18)
    # Lower half: y5=0, subtract 19 == add 13 modulo 32.
    q.x(Y5)
    add_constant(q, Y5, 13)
    q.x(Y5)
    # Upper half: y5=1, subtract 9 == add 23 modulo 32.
    add_constant(q, Y5, 23)
    return q


def expected(y: int) -> int:
    low = y & 31
    center = 19 if not (y >> 5) else 9
    return ((low - center) % 32) | (y & 32)


def verify_classical_mapping() -> None:
    # The arithmetic circuit is composed only of reversible controlled bit
    # toggles. Replay its classical gates on all 64 basis values as an
    # independent check of the intended permutation.
    q = build()
    for y in range(64):
        bits = [0] * 18
        for bit in range(6):
            bits[6 + bit] = (y >> bit) & 1
        for instruction, qargs, _ in q.data:
            name = instruction.name
            indexes = [qubit._index for qubit in qargs]
            if name == "mcx_vchain":
                count = instruction.num_ctrl_qubits
                controls, target = indexes[:count], indexes[count]
            elif name == "ccx":
                controls, target = indexes[:2], indexes[2]
            elif name == "cx":
                controls, target = indexes[:1], indexes[1]
            else:
                controls, target = [], indexes[0]
            active = all(bits[index] for index in controls)
            if name == "x" and active:
                bits[target] ^= 1
            elif name in ("cx", "ccx", "mcx", "mcx_vchain") and active:
                bits[target] ^= 1
        actual = sum(bits[6 + bit] << bit for bit in range(6))
        if actual != expected(y):
            raise AssertionError((y, actual, expected(y)))


def main() -> None:
    verify_classical_mapping()
    raw = build()
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3)
    path = ARTIFACTS / "local_y_distance.qasm"
    path.write_text(qasm2.dumps(compiled))
    metrics = {
        "transform": "low5 -> low5 - (19 if y5=0 else 9) mod 32",
        "preserved": "y5",
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "classical_inputs_verified": 64,
        "ancillas": SCRATCH,
        "note": "Transform-only fallback; no radius logic or complete oracle integration.",
    }
    (ARTIFACTS / "local_y_distance_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
