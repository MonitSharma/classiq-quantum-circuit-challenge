"""Build the strongest high-order correction found on the shallow frontier.

The base candidate leaves q17 untouched, so it is clean for this particular
construction.  Three RC3X blocks compute a five-way product into q12 through
q17, while restoring q17.  Relative phases are safe inside the eventual
exact-inverse C-dagger-Z-C construction; this file only measures the forward
classifier candidate and does not claim a complete oracle.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RC3XGate

from destructive_semantic_search import (
    TARGET,
    apply_rccx_semantic,
    build_circuit,
    initial_wire_truth_tables,
    exact_affine_distance,
)


BASE = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
    "double_seed42_b16x6_p4_depth59.json"
)


def build_corrected(base_path: Path = BASE) -> tuple[QuantumCircuit, tuple[int, ...], dict]:
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = initial_wire_truth_tables()
    for _, control_a, control_b, target in gates:
        wires = apply_rccx_semantic(wires, control_a, control_b, target)
    if wires[17] != 0:
        raise AssertionError("q17 is not clean in the selected base candidate")

    before, combo = exact_affine_distance(wires)
    q = build_circuit(gates)
    # q17 ^= q2&q3&q4; q12 ^= q17&q8&q11; uncompute q17.
    q.append(RC3XGate(), [2, 3, 4, 17])
    q.append(RC3XGate(), [17, 8, 11, 12])
    q.append(RC3XGate(), [2, 3, 4, 17])

    corrected = list(wires)
    corrected[17] ^= corrected[2] & corrected[3] & corrected[4]
    corrected[12] ^= corrected[17] & corrected[8] & corrected[11]
    corrected[17] ^= corrected[2] & corrected[3] & corrected[4]
    if corrected[17] != 0:
        raise AssertionError("correction failed to restore q17")
    after, corrected_combo = exact_affine_distance(tuple(corrected))
    if after != 387:
        raise AssertionError(f"unexpected corrected affine residual: {after}")
    return q, tuple(corrected), {
        "base_affine_residual": before,
        "base_affine_combo": combo,
        "corrected_affine_residual": after,
        "corrected_affine_combo": corrected_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancilla": 17,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, _, metrics = build_corrected()
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False,
                             optimization_level=3)
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
    })
    print(json.dumps(metrics, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
