"""Analytic SU(4)-parameter Adam control for MPO matching circuits.

This bounded experiment complements the exact gatewise Procrustes sweep.  Each
two-qubit gate is exp(i H(theta)) in a fixed 15-element Pauli basis, and JAX
autodiff supplies exact parameter gradients.  The process overlap is estimated
with fixed Rademacher trace probes; exact MPO contraction remains mandatory for
evaluation and promotion.
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
import jax.scipy as jsp

from mpo_gate_sweep import topology_layers
from mpo_rie_state import apply_gate_batch, make_probes
from mpo_target import DEFAULT_ORDER, ordered_tensor


N = 12
D = 2**N


def pauli_basis() -> jnp.ndarray:
    i = jnp.asarray([[0, 1], [1, 0]], dtype=jnp.complex128)
    y = jnp.asarray([[0, -1j], [1j, 0]], dtype=jnp.complex128)
    z = jnp.asarray([[1, 0], [0, -1]], dtype=jnp.complex128)
    one = jnp.eye(2, dtype=jnp.complex128)
    single = (one, i, y, z)
    return jnp.asarray(
        [jnp.kron(a, b) for a in single for b in single if not (a is one and b is one)]
    )


PAULIS = pauli_basis()


def gates_from_params(params: jnp.ndarray) -> jnp.ndarray:
    def one_gate(theta):
        h = jnp.tensordot(theta, PAULIS, axes=1)
        return jsp.linalg.expm(1j * h)

    return jax.vmap(one_gate)(params)


def loss_fn(params, probes, signs, pairs):
    gates = gates_from_params(params)
    states = probes
    for gate, pair in zip(gates, pairs):
        states = apply_gate_batch(states, gate, pair)
    trace_estimate = jnp.sum(jnp.conj(probes) * (states * signs)) / (probes.shape[0] * D)
    return 1.0 - jnp.abs(trace_estimate) ** 2


def run(topology: str, layers: int, iterations: int, probes: int, seed: int, learning_rate: float, output: str | Path, sequence=None, init_npz: str | Path | None = None) -> dict:
    layers_spec = topology_layers(topology, layers, sequence=sequence)
    pairs = [pair for layer in layers_spec for pair in layer]
    rng = np.random.default_rng(seed)
    if init_npz is None:
        params_np = rng.normal(scale=0.03, size=(len(pairs), 15))
    else:
        params_np = np.zeros((len(pairs), 15), dtype=np.float64)
        previous = np.asarray(np.load(init_npz)["params"])
        if previous.shape[1:] != (15,) or previous.shape[0] > len(pairs):
            raise ValueError("warm-start parameter shape is incompatible with requested layers")
        params_np[: previous.shape[0]] = previous
    params = jnp.asarray(params_np, dtype=jnp.float64)
    probe_array = jnp.asarray(make_probes(probes, seed + 10000))
    signs = jnp.asarray(ordered_tensor(DEFAULT_ORDER).reshape(-1), dtype=jnp.complex128)
    value_grad = jax.jit(
        jax.value_and_grad(lambda current: loss_fn(current, probe_array, signs, pairs))
    )
    first_moment = jnp.zeros_like(params)
    second_moment = jnp.zeros_like(params)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    history = []
    start = time.perf_counter()
    for step in range(1, iterations + 1):
        loss, grad = value_grad(params)
        first_moment = beta1 * first_moment + (1 - beta1) * grad
        second_moment = beta2 * second_moment + (1 - beta2) * grad * grad
        first_hat = first_moment / (1 - beta1**step)
        second_hat = second_moment / (1 - beta2**step)
        params = params - learning_rate * first_hat / (jnp.sqrt(second_hat) + eps)
        history.append(float(1 - loss))
    report = {
        "topology": topology,
        "layers": layers,
        "matching_sequence": list(sequence) if sequence is not None else None,
        "warm_start": str(init_npz) if init_npz is not None else None,
        "su4_gates": len(pairs),
        "seed": seed,
        "probe_count": probes,
        "iterations": iterations,
        "learning_rate": learning_rate,
        "estimated_process_fidelity_history": history,
        "estimated_final_process_fidelity": history[-1] if history else None,
        "wall_time_seconds": time.perf_counter() - start,
        "optimizer": "JAX autodiff + Adam over 15-parameter SU(4) exponentials",
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
    parser.add_argument("--topology", choices=("tt", "round_robin", "xy"), default="round_robin")
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--probes", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--output", default="artifacts/mpo_native/adam_su4.json")
    parser.add_argument("--sequence", help="comma-separated round-robin matching indices")
    parser.add_argument("--init-npz")
    args = parser.parse_args()
    args.sequence = [int(value) for value in args.sequence.split(",")] if args.sequence else None
    print(json.dumps(run(**vars(args)), indent=2))
