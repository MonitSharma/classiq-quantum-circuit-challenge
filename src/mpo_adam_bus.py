"""Analytic Adam optimizer for a four-ancilla clean-subspace bus circuit."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
import jax.scipy as jsp

from mpo_adam_su4 import pauli_basis
from mpo_rie_state import make_probes
from mpo_target import DEFAULT_ORDER, ordered_tensor


DATA = 12
BUS = 4
WIRES = DATA + BUS
DIM = 2**DATA
FULL = 2**WIRES
PAULIS = pauli_basis()


def schedule(interactions: int) -> list[tuple[int, int]]:
    return [(DATA + bus, data) for data in range(DATA) for bus in range(interactions)]


def apply_gate(states, gate, pair):
    a, b = sorted(pair)
    tensor = states.reshape((states.shape[0],) + (2,) * WIRES)
    axes = [0] + [1 + i for i in range(WIRES) if i not in (a, b)] + [1 + a, 1 + b]
    inverse = np.argsort(axes)
    moved = jnp.transpose(tensor, axes)
    transformed = moved.reshape((-1, 4)) @ gate.T
    return jnp.transpose(transformed.reshape(moved.shape), inverse).reshape((states.shape[0], FULL))


def gates_from_params(params):
    def one(theta):
        return jsp.linalg.expm(1j * jnp.tensordot(theta, PAULIS, axes=1))

    return jax.vmap(one)(params)


def run(interactions: int, iterations: int, probes: int, seed: int, learning_rate: float, output: str | Path) -> dict:
    pairs = schedule(interactions)
    rng = np.random.default_rng(seed)
    params = jnp.asarray(rng.normal(scale=0.03, size=(len(pairs), 15)), dtype=jnp.float64)
    data_probes = jnp.asarray(make_probes(probes, seed + 30000))
    full_probes = jnp.zeros((probes, FULL), dtype=jnp.complex128)
    # Ancillas start at zero; map each 12-qubit probe into the 16-qubit state.
    full_probes = full_probes.at[:, :DIM].set(data_probes)
    signs = jnp.asarray(ordered_tensor(DEFAULT_ORDER).reshape(-1), dtype=jnp.complex128)
    diagonal_indices = jnp.arange(DIM)

    def loss_fn(current):
        states = full_probes
        for gate, pair in zip(gates_from_params(current), pairs):
            states = apply_gate(states, gate, pair)
        clean_diagonal = states[:, diagonal_indices]
        trace_estimate = jnp.sum(jnp.conj(data_probes) * (clean_diagonal * signs)) / (probes * DIM)
        return 1.0 - jnp.abs(trace_estimate) ** 2

    value_grad = jax.jit(jax.value_and_grad(loss_fn))
    first = jnp.zeros_like(params)
    second = jnp.zeros_like(params)
    history = []
    start = time.perf_counter()
    for step in range(1, iterations + 1):
        loss, grad = value_grad(params)
        first = 0.9 * first + 0.1 * grad
        second = 0.999 * second + 0.001 * grad * grad
        params = params - learning_rate * (first / (1 - 0.9**step)) / (jnp.sqrt(second / (1 - 0.999**step)) + 1e-8)
        history.append(float(1 - loss))
    report = {
        "architecture": "four-ancilla bus with analytic SU(4) Adam",
        "interactions_per_data": interactions,
        "su4_gates": len(pairs),
        "seed": seed,
        "probe_count": probes,
        "iterations": iterations,
        "learning_rate": learning_rate,
        "estimated_process_fidelity_history": history,
        "estimated_final_process_fidelity": history[-1] if history else None,
        "wall_time_seconds": time.perf_counter() - start,
        "clean_ancilla_boundary": True,
        "exact_promotion_required": True,
        "promoted": False,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), params=np.asarray(params), pairs=np.asarray(pairs))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactions", type=int, choices=(1, 2, 3, 4), default=4)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--probes", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--output", default="artifacts/mpo_native/adam_bus.json")
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))
