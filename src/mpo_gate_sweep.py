"""Gatewise Procrustes optimization for MPO-target matching circuits.

The overlap is contracted as one tensor network containing the exact target TT
and every two-qubit gate in a fixed matching circuit.  For one selected gate,
the rest of the network is contracted 16 times with matrix-unit gates to form
its exact linear environment.  A polar/SVD update then gives the unitary gate
that maximizes the local overlap.  No finite-difference gradient and no dense
4096-by-4096 candidate unitary are used.

This is a research optimizer.  Its outputs are abstract U(4) gates and must
go through native compilation and exhaustive verification before promotion.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import opt_einsum as oe

from mpo_target import DEFAULT_ORDER, ordered_tensor, tt_svd
from mpo_topologies import round_robin_matchings, tt_brickwall_layers, xy_matchings


N = 12
D = 2
D2 = 4
_PATH_CACHE: dict[tuple[tuple[tuple[int, ...], tuple[int, ...]], ...], object] = {}


def slot_pairs(layers: Sequence[Sequence[tuple[int, int]]]) -> list[list[tuple[int, int]]]:
    """Map physical-qubit matching layers into TT slots."""
    inverse = {physical: slot for slot, physical in enumerate(DEFAULT_ORDER)}
    return [
        [tuple(sorted((inverse[a], inverse[b]))) for a, b in layer]
        for layer in layers
    ]


def topology_layers(
    name: str, layers: int, sequence: Sequence[int] | None = None
) -> list[list[tuple[int, int]]]:
    if name == "round_robin":
        source = round_robin_matchings()
        selected = list(sequence) if sequence is not None else list(range(layers))
        if len(selected) != layers or any(index < 0 or index >= len(source) for index in selected):
            raise ValueError("round-robin sequence must contain valid matching indices")
        if len(set(selected)) != len(selected):
            raise ValueError("round-robin sequence must not repeat a matching")
        if layers > len(source):
            raise ValueError("round_robin has only 11 matching layers")
        return slot_pairs([source[index] for index in selected])
    if name == "tt":
        base = tt_brickwall_layers()
        return slot_pairs([base[i % 2] for i in range(layers)])
    if name == "xy":
        base = xy_matchings()
        return slot_pairs([base[i % 2] for i in range(layers)])
    raise ValueError(f"unknown topology {name!r}")


def target_cores() -> list[np.ndarray]:
    cores, _ = tt_svd(ordered_tensor(DEFAULT_ORDER))
    return cores


def _wire_label(layer: int, slot: int, n_layers: int) -> int:
    """Label between layers, with negative labels reserved for boundaries."""
    if layer == 0 or layer == n_layers:
        return slot
    return N + (layer - 1) * N + slot


def _network_operands(
    target: Sequence[np.ndarray],
    layers: Sequence[Sequence[tuple[int, int]]],
    gates: Sequence[np.ndarray],
    omit: tuple[int, int] | None = None,
    replacement: np.ndarray | None = None,
) -> list[object]:
    """Build operands for the target/circuit overlap tensor network."""
    n_layers = len(layers)
    operands: list[object] = []
    # Target TT carries the target sign and its physical index is shared with
    # both circuit boundaries, enforcing the trace V[z,z].
    for slot, core in enumerate(target):
        left_bond = 100 if slot == 0 else 101 + slot - 1
        right_bond = 100 if slot == N - 1 else 101 + slot
        operands.extend((core, [left_bond, slot, right_bond]))

    gate_index = 0
    for layer, pairs in enumerate(layers):
        used = set()
        for local_index, (first, second) in enumerate(pairs):
            used.update((first, second))
            gate = replacement if omit == (layer, local_index) else gates[gate_index]
            # Gate list is global layer-major; the labels use the actual
            # wire at the layer boundary.  Each gate has (out_a,out_b,in_a,in_b).
            in_a = _wire_label(layer, first, n_layers)
            in_b = _wire_label(layer, second, n_layers)
            out_a = _wire_label(layer + 1, first, n_layers)
            out_b = _wire_label(layer + 1, second, n_layers)
            operands.extend((gate.reshape(2, 2, 2, 2), [out_a, out_b, in_a, in_b]))
            gate_index += 1
        # The alternating TT matching has two idle endpoints.  They are
        # explicit identity wires, not omitted tensors; omitting them would
        # leave those circuit indices uncontracted and inflate the objective.
        identity = np.eye(2, dtype=np.complex128)
        for slot in sorted(set(range(N)) - used):
            operands.extend(
                (identity, [_wire_label(layer + 1, slot, n_layers), _wire_label(layer, slot, n_layers)])
            )
    return operands


def _contract_scalar(operands: list[object]) -> complex:
    signature = tuple(
        (tuple(np.asarray(labels).tolist()), tuple(np.asarray(array).shape))
        for array, labels in zip(operands[::2], operands[1::2])
    )
    path = _PATH_CACHE.get(signature)
    if path is None:
        path, _ = oe.contract_path(*operands, [], optimize="greedy")
        _PATH_CACHE[signature] = path
    return complex(oe.contract(*operands, [], optimize=path))


def overlap(
    target: Sequence[np.ndarray],
    layers: Sequence[Sequence[tuple[int, int]]],
    gates: Sequence[np.ndarray],
) -> complex:
    operands = _network_operands(target, layers, gates)
    return _contract_scalar(operands)


def environment(
    target: Sequence[np.ndarray],
    layers: Sequence[Sequence[tuple[int, int]]],
    gates: Sequence[np.ndarray],
    layer: int,
    gate_index: int,
) -> np.ndarray:
    """Return E with overlap = sum(E[r,c] * G[r,c]) for the selected gate."""
    result = np.empty((D2, D2), dtype=np.complex128)
    for row in range(D2):
        for col in range(D2):
            basis = np.zeros((D2, D2), dtype=np.complex128)
            basis[row, col] = 1.0
            result[row, col] = _contract_scalar(
                _network_operands(target, layers, gates, omit=(layer, gate_index), replacement=basis)
            )
    return result


def haar_unitary(rng: np.random.Generator, dimension: int = D2) -> np.ndarray:
    matrix = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    q, r = np.linalg.qr(matrix)
    phases = np.diag(r)
    q = q @ np.diag(np.conj(phases) / np.maximum(np.abs(phases), 1e-15))
    return q


def project_su4(environment_matrix: np.ndarray) -> np.ndarray:
    """Polar update for E:G, with a harmless determinant-one gauge."""
    left, _, right_h = np.linalg.svd(environment_matrix.conj(), full_matrices=False)
    gate = left @ right_h
    determinant = np.linalg.det(gate)
    gate *= np.exp(-0.25j * np.angle(determinant))
    return gate


def process_fidelity(value: complex) -> float:
    return float(abs(value) ** 2 / (2**N) ** 2)


def initialize_gates(layers: Sequence[Sequence[tuple[int, int]]], seed: int, mode: str) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    count = sum(len(layer) for layer in layers)
    if mode == "identity":
        return [np.eye(D2, dtype=np.complex128) for _ in range(count)]
    if mode == "near_identity":
        gates = []
        for _ in range(count):
            h = rng.normal(size=(D2, D2)) + 1j * rng.normal(size=(D2, D2))
            h = (h + h.conj().T) / 2
            left, _, right_h = np.linalg.svd(np.eye(D2) + 0.1j * h)
            gates.append(left @ right_h)
        return gates
    if mode == "haar":
        return [haar_unitary(rng) for _ in range(count)]
    raise ValueError(f"unknown initialization {mode!r}")


def run(
    topology: str,
    layers_count: int,
    sweeps: int,
    seed: int,
    initialization: str,
    output: str | Path,
    sequence: Sequence[int] | None = None,
) -> dict:
    layers = topology_layers(topology, layers_count, sequence=sequence)
    target = target_cores()
    gates = initialize_gates(layers, seed, initialization)
    initial = process_fidelity(overlap(target, layers, gates))
    history = []
    start = time.perf_counter()
    for sweep in range(sweeps):
        for layer in range(layers_count):
            offset = sum(len(item) for item in layers[:layer])
            for local_index in range(len(layers[layer])):
                global_index = offset + local_index
                env = environment(target, layers, gates, layer, local_index)
                gates[global_index] = project_su4(env)
        fidelity = process_fidelity(overlap(target, layers, gates))
        history.append({"sweep": sweep + 1, "process_fidelity": fidelity})
        if len(history) > 2 and abs(history[-1]["process_fidelity"] - history[-2]["process_fidelity"]) < 1e-14:
            break
    elapsed = time.perf_counter() - start
    report = {
        "topology": topology,
        "matching_sequence": list(sequence) if sequence is not None else None,
        "layers": layers_count,
        "su4_gates": len(gates),
        "seed": seed,
        "initialization": initialization,
        "sweeps_requested": sweeps,
        "sweeps_completed": len(history),
        "initial_process_fidelity": initial,
        "final_process_fidelity": history[-1]["process_fidelity"] if history else initial,
        "final_process_infidelity": 1.0 - (history[-1]["process_fidelity"] if history else initial),
        "history": history,
        "wall_time_seconds": elapsed,
        "optimizer": "exact tensor-network gatewise Procrustes sweep",
        "not_promoted": True,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), gates=np.asarray(gates), layers=np.asarray(layers, dtype=object))
    with Path("artifacts/mpo_native/progress.jsonl").open("a") as stream:
        stream.write(json.dumps({"kind": "gate_sweep", **report}, separators=(",", ":")) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", choices=("tt", "round_robin", "xy"), default="round_robin")
    parser.add_argument("--layers", dest="layers_count", type=int, default=2)
    parser.add_argument("--sweeps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--initialization", choices=("identity", "near_identity", "haar"), default="near_identity")
    parser.add_argument("--output", default="artifacts/mpo_native/gate_sweep.json")
    parser.add_argument("--sequence", help="comma-separated round-robin matching indices")
    args = parser.parse_args()
    args.sequence = [int(value) for value in args.sequence.split(",")] if args.sequence else None
    print(json.dumps(run(**vars(args)), indent=2))
