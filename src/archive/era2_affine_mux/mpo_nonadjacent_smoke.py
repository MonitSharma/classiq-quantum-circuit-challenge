"""Cross-check a genuinely non-chain matching layer against dense Qiskit."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from scipy.stats import unitary_group

from mpo_contract import apply_nonadjacent_gate, identity_mpo, process_fidelity, target_mpo
from mpo_objective import process_metrics
from mpo_target import DEFAULT_ORDER
from mpo_topologies import round_robin_matchings


def run(output: str | Path = "artifacts/mpo_native/nonadjacent_smoke.json") -> dict:
    rng = np.random.default_rng(20260911)
    physical_to_slot = {physical: slot for slot, physical in enumerate(DEFAULT_ORDER)}
    matching = round_robin_matchings()[3]
    mpo = identity_mpo()
    dense = QuantumCircuit(12)
    for physical_a, physical_b in matching:
        slot_a, slot_b = sorted((physical_to_slot[physical_a], physical_to_slot[physical_b]))
        gate = unitary_group.rvs(4, random_state=rng)
        mpo = apply_nonadjacent_gate(mpo, slot_a, slot_b, gate)
        # Reverse the list because Qiskit's first matrix factor acts on the
        # second listed qubit; this makes factors match MPO slots.
        dense.append(
            UnitaryGate(gate),
            [DEFAULT_ORDER[slot_b], DEFAULT_ORDER[slot_a]],
        )
    mpo_value = process_fidelity(mpo, target_mpo())
    dense_value = process_metrics(dense)["process_fidelity"]
    report = {
        "seed": 20260911,
        "physical_matching": [list(pair) for pair in matching],
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
