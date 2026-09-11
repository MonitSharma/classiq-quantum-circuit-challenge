"""No-uncompute v6: residual-197 two-partial continuation."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import exact_affine_distance, initial_wire_truth_tables
from high_order_affine_no_uncompute_v5 import build_candidate_v5


def build_candidate_v6():
    circuit, metrics = build_candidate_v5()

    # Form two partials and leave both in the destructive midpoint state:
    # q14 ^= ¬q4·¬q10, q17 ^= q8·q9, then q11 ^= q14·q17·q16.
    for wire in (4, 10):
        circuit.x(wire)
    circuit.append(RCCXGate(), [4, 10, 14])
    for wire in (10, 4):
        circuit.x(wire)
    circuit.append(RCCXGate(), [8, 9, 17])
    circuit.append(RC3XGate(), [14, 17, 16, 11])

    wires = _semantic_replay(circuit)
    residual, combo = exact_affine_distance(tuple(wires))
    if residual != 197 or any(wires[i] == 0 for i in (13, 14, 16, 17)):
        raise AssertionError("unexpected no-uncompute v6 semantics")

    metrics = dict(metrics)
    metrics.update({
        "experiment": "no-uncompute destructive classifier v6",
        "additional_correction": [
            [14, [[4, False], [10, False]]],
            [17, [8, 9]],
            [11, [14, 17, 16]],
        ],
        "corrected_affine_residual": residual,
        "corrected_affine_combo": combo,
        "midpoint_garbage_wires": [13, 14, 16, 17],
        "status": "best no-uncompute residual Pareto candidate; incomplete classifier",
    })
    return circuit, metrics


def _semantic_replay(circuit):
    mask = (1 << 4096) - 1
    wires = list(initial_wire_truth_tables())
    for instruction in circuit.data:
        operation = instruction.operation
        qubits = [circuit.qubits.index(qubit) for qubit in instruction.qubits]
        if operation.name == "x":
            wires[qubits[0]] ^= mask
        elif operation.name == "rccx":
            wires[qubits[2]] ^= wires[qubits[0]] & wires[qubits[1]]
        elif operation.name == "rcccx":
            wires[qubits[3]] ^= wires[qubits[0]] & wires[qubits[1]] & wires[qubits[2]]
        else:
            raise ValueError(operation.name)
    return wires


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_candidate_v6()
        compiled = transpile(
            circuit,
            basis_gates=["u3", "cx"],
            qubits_initially_zero=False,
            optimization_level=3,
        )
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
        },
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
    })
    print(json.dumps(metrics, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
