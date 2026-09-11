"""Cross-check the local MPO process contraction against dense Qiskit output."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from scipy.stats import unitary_group

from mpo_contract import apply_layer, identity_mpo, process_fidelity, target_mpo
from mpo_objective import process_metrics
from mpo_target import DEFAULT_ORDER


def run(output: str | Path = "artifacts/mpo_native/contraction_smoke.json") -> dict:
    rng = np.random.default_rng(20260911)
    gates = {slot: unitary_group.rvs(4, random_state=rng) for slot in range(0, 12, 2)}

    # Qiskit places the first matrix factor on the second listed qubit.  The
    # reversal makes the matrix's first factor correspond to TT slot `slot`.
    dense = QuantumCircuit(12)
    for slot, gate in gates.items():
        dense.append(
            UnitaryGate(gate),
            [DEFAULT_ORDER[slot + 1], DEFAULT_ORDER[slot]],
        )

    mpo_value = process_fidelity(apply_layer(identity_mpo(), gates), target_mpo())
    dense_value = process_metrics(dense)["process_fidelity"]
    report = {
        "seed": 20260911,
        "mpo_process_fidelity": mpo_value,
        "dense_process_fidelity": dense_value,
        "absolute_difference": abs(mpo_value - dense_value),
        "verified": bool(abs(mpo_value - dense_value) < 1e-10),
    }
    if not report["verified"]:
        raise AssertionError(report)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
