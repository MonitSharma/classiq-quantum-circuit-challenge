"""Benchmark exact QFT-based conditional 5-bit modular recentering."""
from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import QFT
from qiskit.quantum_info import Statevector


TARGET = list(range(5))
BRANCH = 5
FULL = 2**5


def controlled_add(q: QuantumCircuit, branch: int, value: int) -> None:
    q.append(QFT(5, do_swaps=False), TARGET)
    for bit in TARGET:
        q.cp(2 * 3.141592653589793 * value / (2 ** (bit + 1)), branch, bit)
    q.append(QFT(5, do_swaps=False).inverse(), TARGET)


def build_local() -> QuantumCircuit:
    q = QuantumCircuit(6)
    # y5=0: add -19 == add 13 modulo 32.
    q.x(BRANCH)
    controlled_add(q, BRANCH, 13)
    q.x(BRANCH)
    # y5=1: add -9 == add 23 modulo 32.
    controlled_add(q, BRANCH, 23)
    return q


def expected(y: int) -> int:
    low = y & 31
    center = 19 if not (y >> 5) else 9
    return ((low - center) % 32) | (y & 32)


def verify() -> None:
    q = build_local()
    for y in range(64):
        state = Statevector.from_int(y, 64).evolve(q)
        target = max(range(64), key=lambda i: abs(state.data[i]))
        if target != expected(y) or abs(abs(state.data[target]) - 1) > 1e-8:
            raise AssertionError((y, target, expected(y)))


def main() -> None:
    verify()
    local = build_local()
    full = QuantumCircuit(18)
    full.compose(local, qubits=list(range(6, 12)), inplace=True)
    compiled = transpile(full, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3)
    out = Path("artifacts/qft_recenter.qasm")
    out.write_text(qasm2.dumps(compiled))
    metrics = {"transform": "low5 -> low5 - (19 if y5=0 else 9) mod 32",
               "depth": compiled.depth(), "cx": compiled.count_ops().get("cx", 0),
               "width": compiled.num_qubits, "basis": ["u3", "cx"],
               "qubits_initially_zero": False, "classical_inputs_verified": 64,
               "decision": "continue_coordinate-coding" if compiled.depth() < 50 else "kill_coordinate-coding"}
    Path("artifacts/qft_recenter_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
