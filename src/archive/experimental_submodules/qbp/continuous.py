"""Bounded continuous SU(2) QBP search.

The objective is a phase process, not a classifier: for every input x the
single memory qubit should end at ``logo_sign(x)|0>``.  Floating-point results
are diagnostic only and are never promoted to an exact oracle.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np

jax.config.update("jax_enable_x64", True)

N_INPUTS = 4096
ORDER_BASE = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)


def target_signs() -> np.ndarray:
    from search import logo
    return np.asarray([1.0 if not logo(x, y) else -1.0
                       for y in range(64) for x in range(64)], dtype=np.float64)


INPUTS = jnp.asarray(np.arange(N_INPUTS, dtype=np.int64))
TARGET = jnp.asarray(target_signs())


def quaternion_matrices(params: jnp.ndarray) -> jnp.ndarray:
    """Normalize real quaternion parameters into SU(2) matrices."""
    q = params / (jnp.linalg.norm(params, axis=-1, keepdims=True) + 1e-15)
    w, x, y, z = [q[..., i] for i in range(4)]
    return jnp.stack((
        jnp.stack((w - 1j * z, -y - 1j * x), axis=-1),
        jnp.stack((y - 1j * x, w + 1j * z), axis=-1),
    ), axis=-2)


def forward(params: jnp.ndarray, order: tuple[int, ...]) -> jnp.ndarray:
    matrices = quaternion_matrices(params)
    state = jnp.zeros((N_INPUTS, 2), dtype=jnp.complex128).at[:, 0].set(1.0)
    for position, bit in enumerate(order):
        branch = ((INPUTS >> bit) & 1).astype(jnp.int32)
        selected = matrices[position, branch]
        state = jnp.einsum("bij,bj->bi", selected, state)
    return state


def loss(params: jnp.ndarray, order: tuple[int, ...]) -> jnp.ndarray:
    state = forward(params, order)
    desired = TARGET.astype(jnp.complex128)
    error = state[:, 0] - desired
    return jnp.mean(jnp.real(error * jnp.conj(error)) + jnp.real(state[:, 1] * jnp.conj(state[:, 1])))


def optimize(length: int, steps: int, seed: int, learning_rate: float,
             schedule_seed: int | None = None) -> dict:
    if schedule_seed is None:
        order = tuple(ORDER_BASE[i % len(ORDER_BASE)] for i in range(length))
    else:
        schedule_rng = np.random.default_rng(schedule_seed)
        order = tuple(int(value) for value in schedule_rng.integers(0, 12, size=length))
    key = jax.random.PRNGKey(seed)
    params = jax.random.normal(key, (length, 2, 4), dtype=jnp.float64)
    grad_fn = jax.jit(jax.value_and_grad(loss))
    m = jnp.zeros_like(params)
    v = jnp.zeros_like(params)
    best = (float("inf"), params)
    started = time.time()
    for step in range(1, steps + 1):
        value, gradient = grad_fn(params, order)
        m = 0.9 * m + 0.1 * gradient
        v = 0.999 * v + 0.001 * gradient * gradient
        mhat = m / (1.0 - 0.9 ** step)
        vhat = v / (1.0 - 0.999 ** step)
        params = params - learning_rate * mhat / (jnp.sqrt(vhat) + 1e-8)
        numeric = float(value)
        if numeric < best[0]:
            best = (numeric, params)
    best_loss, best_params = best
    state = np.asarray(forward(best_params, order))
    target = np.asarray(TARGET)
    amplitudes = target * state[:, 0].real
    leakage = np.abs(state[:, 1])
    return {
        "length": length,
        "steps": steps,
        "seed": seed,
        "order": list(order),
        "schedule_seed": schedule_seed,
        "loss": best_loss,
        "minimum_target_real_amplitude": float(np.min(amplitudes)),
        "maximum_target_amplitude_error": float(np.max(np.abs(amplitudes - 1.0))),
        "maximum_memory_leakage": float(np.max(leakage)),
        "runtime_seconds": time.time() - started,
        "status": "numerical_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=12)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--schedule-seed", type=int)
    parser.add_argument("--out", type=Path, default=Path("artifacts/unitary_state_space/qbp/continuous_checkpoint.json"))
    args = parser.parse_args()
    result = optimize(args.length, args.steps, args.seed, args.learning_rate, args.schedule_seed)
    result["kind"] = "continuous SU(2) QBP phase-process search"
    result["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
