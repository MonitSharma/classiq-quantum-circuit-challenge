"""No-uncompute v4: use two retained partial wires for a five-literal update."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import exact_affine_distance, initial_wire_truth_tables
from high_order_affine_no_uncompute_v3 import build_candidate_v3


def build_candidate_v4():
    circuit, metrics = build_candidate_v3()

    # The four negative literals are made positive around two partial updates.
    # q13 and q14 are deliberately not restored; their resulting values are
    # midpoint garbage and may remain in the affine completion basis.
    for wire in (1, 2, 3, 4):
        circuit.x(wire)
    circuit.append(RCCXGate(), [1, 2, 14])
    circuit.append(RCCXGate(), [3, 4, 13])
    circuit.append(RC3XGate(), [14, 13, 11, 12])
    for wire in (1, 2, 3, 4):
        circuit.x(wire)

    mask = (1 << 4096) - 1
    wires = list(_semantic_state_before_v4())
    for wire in (1, 2, 3, 4):
        wires[wire] ^= mask
    wires[14] ^= wires[1] & wires[2]
    wires[13] ^= wires[3] & wires[4]
    wires[12] ^= wires[14] & wires[13] & wires[11]
    for wire in (1, 2, 3, 4):
        wires[wire] ^= mask
    residual, combo = exact_affine_distance(tuple(wires))
    if residual != 251 or wires[13] == 0 or wires[14] == 0:
        raise AssertionError("unexpected no-uncompute v4 semantics")

    metrics = dict(metrics)
    metrics.update({
        "experiment": "no-uncompute destructive classifier v4",
        "additional_correction": [
            12,
            [[1, False], [2, False], [3, False], [4, False], 11],
        ],
        "corrected_affine_residual": residual,
        "corrected_affine_combo": combo,
        "midpoint_garbage_wires": [13, 14, 17],
        "status": "best no-uncompute depth/residual Pareto candidate; incomplete classifier",
    })
    return circuit, metrics


def _semantic_state_before_v4():
    """Replay v3's monomial circuit without importing its private state."""
    from high_order_affine_no_uncompute_v3 import build_candidate_v3

    circuit, _ = build_candidate_v3()
    mask = (1 << 4096) - 1
    wires = list(initial_wire_truth_tables())
    for instruction in circuit.data:
        operation = instruction.operation
        qubits = [circuit.qubits.index(qubit) for qubit in instruction.qubits]
        if operation.name == "x":
            wires[qubits[0]] ^= mask
        elif operation.name == "cx":
            wires[qubits[1]] ^= wires[qubits[0]]
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
        circuit, metrics = build_candidate_v4()
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
