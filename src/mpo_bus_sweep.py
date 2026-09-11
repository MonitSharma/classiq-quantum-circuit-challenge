"""Bounded MPO-inspired four-ancilla bus gate-sweep experiment.

The four ancillas are initialized and postselected on |0000>.  The overlap
network therefore measures the requested clean-subspace map, including
ancilla leakage: any amplitude that does not return the bus to zero is absent
from the overlap.  This is an ansatz experiment, not an automatic conversion
of TT cores into unitary gates.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import opt_einsum as oe

from mpo_gate_sweep import project_su4, target_cores, process_fidelity
from mpo_gate_sweep import haar_unitary


N_DATA = 12
N_BUS = 4
N_WIRES = N_DATA + N_BUS
_PATH_CACHE = {}


def gate_schedule(bus_qubits: int = 4, buses_per_data: int = 2) -> list[tuple[int, int]]:
    if not 1 <= bus_qubits <= N_BUS or not 1 <= buses_per_data <= bus_qubits:
        raise ValueError("invalid bus schedule")
    return [(N_DATA + bus, data) for data in range(N_DATA) for bus in range(buses_per_data)]


def _network_operands(target, schedule, gates, omit=None, replacement=None):
    # Data boundary labels 0..11 are shared by target physical legs, initial
    # circuit inputs, and final circuit outputs, enforcing the trace.
    current = list(range(N_DATA)) + [1000 + bus for bus in range(N_BUS)]
    initial_bus = list(current[N_DATA:])
    operands = []
    gate_labels = []
    next_label = 2000
    for gate_index, (wire_a, wire_b) in enumerate(schedule):
        in_a, in_b = current[wire_a], current[wire_b]
        out_a, out_b = next_label, next_label + 1
        next_label += 2
        current[wire_a], current[wire_b] = out_a, out_b
        gate = replacement if omit == gate_index else gates[gate_index]
        operands.extend((gate.reshape(2, 2, 2, 2), [out_a, out_b, in_a, in_b]))
    # Target TT physical legs connect to data input/output boundary labels.
    for slot, core in enumerate(target):
        left = 3000 if slot == 0 else 3001 + slot - 1
        right = 3000 if slot == N_DATA - 1 else 3001 + slot
        operands.extend((core, [left, slot, right]))
    for slot in range(N_DATA):
        # Close the data wire into the target physical index: final data bit
        # must equal the initial bit, while the target TT supplies its sign.
        operands.extend((np.eye(2, dtype=np.complex128), [current[slot], slot]))
    for bus in range(N_BUS):
        zero = np.asarray([1.0, 0.0], dtype=np.complex128)
        operands.extend((zero, [initial_bus[bus]]))
        operands.extend((zero, [current[N_DATA + bus]]))
    # The data input and output labels are both the physical slot labels.
    # Attach the initial data boundary by relabeling the first occurrence in
    # the schedule through current construction: a data wire starts at slot.
    return operands


def _contract(operands):
    signature = tuple((tuple(labels), tuple(array.shape)) for array, labels in zip(operands[::2], operands[1::2]))
    path = _PATH_CACHE.get(signature)
    if path is None:
        path, _ = oe.contract_path(*operands, [], optimize="greedy")
        _PATH_CACHE[signature] = path
    return complex(oe.contract(*operands, [], optimize=path))


def overlap(target, schedule, gates):
    return _contract(_network_operands(target, schedule, gates))


def environment(target, schedule, gates, index):
    result = np.empty((4, 4), dtype=np.complex128)
    for row in range(4):
        for col in range(4):
            basis = np.zeros((4, 4), dtype=np.complex128)
            basis[row, col] = 1
            result[row, col] = _contract(
                _network_operands(target, schedule, gates, omit=index, replacement=basis)
            )
    return result


def run(buses_per_data: int, sweeps: int, seed: int, initialization: str, output: str | Path) -> dict:
    schedule = gate_schedule(buses_per_data=buses_per_data)
    rng = np.random.default_rng(seed)
    if initialization == "identity":
        gates = [np.eye(4, dtype=np.complex128) for _ in schedule]
    elif initialization == "near_identity":
        gates = []
        for _ in schedule:
            h = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
            h = (h + h.conj().T) / 2
            left, _, right_h = np.linalg.svd(np.eye(4) + 0.1j * h)
            gates.append(left @ right_h)
    elif initialization == "haar":
        gates = [haar_unitary(rng) for _ in schedule]
    else:
        raise ValueError(f"unknown initialization {initialization!r}")
    target = target_cores()
    initial = process_fidelity(overlap(target, schedule, gates))
    history = []
    start = time.perf_counter()
    for sweep in range(sweeps):
        for index in range(len(gates)):
            gates[index] = project_su4(environment(target, schedule, gates, index))
        fidelity = process_fidelity(overlap(target, schedule, gates))
        history.append(fidelity)
    report = {
        "architecture": "four-ancilla MPO-inspired bus",
        "bus_qubits": 4,
        "buses_per_data": buses_per_data,
        "two_qubit_gates": len(gates),
        "sweeps": sweeps,
        "seed": seed,
        "initialization": initialization,
        "initial_clean_subspace_process_fidelity": initial,
        "final_clean_subspace_process_fidelity": history[-1] if history else initial,
        "history": history,
        "wall_time_seconds": time.perf_counter() - start,
        "ancillas_initialized_and_projected_to_zero": True,
        "promoted": False,
        "reason": "ansatz diagnostic; no native QASM promotion",
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), gates=np.asarray(gates), schedule=np.asarray(schedule))
    with Path("artifacts/mpo_native/progress.jsonl").open("a") as stream:
        stream.write(json.dumps({"kind": "bus_sweep", **report}, separators=(",", ":")) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--buses-per-data", type=int, choices=(1, 2, 3, 4), default=1)
    parser.add_argument("--sweeps", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--initialization", choices=("identity", "near_identity", "haar"), default="near_identity")
    parser.add_argument("--output", default="artifacts/mpo_native/bus_sweep.json")
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))
