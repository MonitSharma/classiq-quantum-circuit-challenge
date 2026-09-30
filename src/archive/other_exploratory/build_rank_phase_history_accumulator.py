"""Accumulator variant of the exact rank-product phase-history oracle.

Unlike the per-term seed, q14 is kept as a dirty cumulative accumulator:
each rank product toggles q14, the factor wires are cleared, and only the
final q14 value is phase-tapped. Dirty MCX synthesis preserves q14 and the
other live wires while computing each factor.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis import synth_mcx_n_dirty_i15

from search import esop


ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "artifacts" / "rank_terms.json"


def dirty_pred(table: int, offset: int, target: int,
               dirty: list[int]) -> QuantumCircuit:
    """Compute a six-input ESOP into target using arbitrary dirty helpers."""
    circuit = QuantumCircuit(18)
    for mask, value in esop(table, 6):
        controls = [offset + i for i in range(6) if mask >> i & 1]
        negative = [
            offset + i for i in range(6)
            if mask >> i & 1 and not (value >> i & 1)
        ]
        for qubit in negative:
            circuit.x(qubit)
        if not controls:
            circuit.x(target)
        elif len(controls) == 1:
            circuit.cx(controls[0], target)
        elif len(controls) == 2:
            circuit.rccx(controls[0], controls[1], target)
        else:
            synthesized = synth_mcx_n_dirty_i15(
                len(controls), relative_phase=True
            )
            helper_count = synthesized.num_qubits - len(controls) - 1
            circuit.compose(
                synthesized,
                qubits=controls + [target] + dirty[:helper_count],
                inplace=True,
            )
        for qubit in negative:
            circuit.x(qubit)
    return circuit


def build(terms_path: Path = TERMS) -> QuantumCircuit:
    terms = json.loads(terms_path.read_text())
    forward = QuantumCircuit(18)
    for x_table, y_table in terms:
        # q14 is the cumulative accumulator. The dirty helpers are allowed
        # to contain arbitrary values, including the accumulated phase bit.
        x_compute = dirty_pred(x_table, 0, 12, [13, 14, 15, 16])
        y_compute = dirty_pred(y_table, 6, 13, [12, 14, 15, 16])
        forward.compose(x_compute, inplace=True)
        forward.compose(y_compute, inplace=True)
        forward.rccx(12, 13, 14)
        forward.compose(y_compute.inverse(), inplace=True)
        forward.compose(x_compute.inverse(), inplace=True)
    circuit = QuantumCircuit(18)
    circuit.compose(forward, inplace=True)
    circuit.z(14)
    circuit.compose(forward.inverse(), inplace=True)
    return circuit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", type=Path, default=TERMS)
    parser.add_argument(
        "--out", type=Path,
        default=Path("artifacts/phase_history/rank_accumulator_seed.qasm"),
    )
    args = parser.parse_args()
    compiled = transpile(
        build(args.terms), basis_gates=["u3", "cx"],
        qubits_initially_zero=False, optimization_level=3,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(compiled))
    print(json.dumps({
        "qasm": str(args.out),
        "depth": compiled.depth(),
        "cx_count": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "terms": len(json.loads(args.terms.read_text())),
        "terms_path": str(args.terms),
        "qubits_initially_zero": False,
    }, indent=2))


if __name__ == "__main__":
    main()
