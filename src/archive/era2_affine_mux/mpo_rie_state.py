"""Batched Riemannian SU(4) optimizer for a fixed matching circuit.

This is an early-search diagnostic, not a replacement for the exact MPO
objective.  It estimates the full process trace with fixed Rademacher probe
vectors while propagating state batches; it never optimizes sampled basis
classification or a state-preparation fidelity.  Any promising checkpoint
must be reevaluated with the exact tensor contraction and promotion gate.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp

from mpo_gate_sweep import haar_unitary, topology_layers
from mpo_target import DEFAULT_ORDER, ordered_tensor


N = 12
D = 2**N


def pairs_for(topology: str, layers: int):
    return topology_layers(topology, layers)


def apply_gate_batch(states: jnp.ndarray, gate: jnp.ndarray, pair: tuple[int, int]) -> jnp.ndarray:
    first, second = pair
    if first > second:
        first, second = second, first
    tensor = states.reshape((states.shape[0],) + (2,) * N)
    axes = [0] + [1 + i for i in range(N) if i not in (first, second)] + [1 + first, 1 + second]
    inverse = np.argsort(axes)
    moved = jnp.transpose(tensor, axes)
    flat = moved.reshape((-1, 4))
    transformed = flat @ gate.T
    moved = transformed.reshape(moved.shape)
    return jnp.transpose(moved, inverse).reshape((states.shape[0], D))


def circuit_states(states: jnp.ndarray, gates: jnp.ndarray, pairs: list[tuple[int, int]]) -> jnp.ndarray:
    out = states
    for gate, pair in zip(gates, pairs):
        out = apply_gate_batch(out, gate, pair)
    return out


def make_probes(batch: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.choice(np.asarray([-1.0, 1.0]), size=(batch, D)).astype(np.complex128)


def initialize(gates: int, seed: int, mode: str) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if mode == "identity":
        return np.asarray([np.eye(4, dtype=np.complex128) for _ in range(gates)])
    if mode == "haar":
        return np.asarray([haar_unitary(rng) for _ in range(gates)])
    if mode == "near_identity":
        out = []
        for _ in range(gates):
            h = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
            h = (h + h.conj().T) / 2
            left, _, right_h = np.linalg.svd(np.eye(4) + 0.1j * h)
            out.append(left @ right_h)
        return np.asarray(out)
    raise ValueError(f"unknown initialization {mode!r}")


def run(topology: str, layers: int, iterations: int, probes: int, seed: int, initialization: str, learning_rate: float, output: str | Path) -> dict:
    layer_pairs = pairs_for(topology, layers)
    pairs = [pair for layer in layer_pairs for pair in layer]
    gates = jnp.asarray(initialize(len(pairs), seed, initialization))
    probe_array = jnp.asarray(make_probes(probes, seed + 10000))
    signs = jnp.asarray(ordered_tensor(DEFAULT_ORDER).reshape(-1), dtype=jnp.complex128)

    def loss_fn(current):
        output_states = circuit_states(probe_array, current, pairs)
        overlap = jnp.sum(jnp.conj(probe_array) * (output_states * signs)) / (probes * D)
        return 1.0 - jnp.abs(overlap) ** 2

    loss_and_grad = jax.jit(jax.value_and_grad(loss_fn))
    history = []
    start = time.perf_counter()
    for _ in range(iterations):
        loss, gradient = loss_and_grad(gates)
        tangent = gradient - jnp.einsum("gij,gkj,gkl->gil", gates, gradient.conj(), gates)
        updated = gates - learning_rate * tangent
        u, _, vh = jnp.linalg.svd(updated)
        gates = u @ vh
        history.append(float(1.0 - loss))
    report = {
        "topology": topology,
        "layers": layers,
        "su4_gates": len(pairs),
        "seed": seed,
        "initialization": initialization,
        "probe_count": probes,
        "iterations": iterations,
        "learning_rate": learning_rate,
        "estimated_process_fidelity_history": history,
        "estimated_final_process_fidelity": history[-1] if history else None,
        "wall_time_seconds": time.perf_counter() - start,
        "objective": "Rademacher trace estimator for full operator overlap",
        "exact_promotion_required": True,
        "promoted": False,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), gates=np.asarray(gates), pairs=np.asarray(pairs))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", choices=("tt", "round_robin", "xy"), default="round_robin")
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--probes", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--initialization", choices=("identity", "near_identity", "haar"), default="near_identity")
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--output", default="artifacts/mpo_native/rie_state.json")
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))
