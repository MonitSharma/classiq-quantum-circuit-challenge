"""Bounded continuous width-4 QBP phase-process search.

This is a feasibility probe only.  A numerical width-4 process is not an
oracle candidate until it is algebraically/exhaustively exactified and lowered
to the challenge's standalone u3/cx model.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import jax
import jax.numpy as jnp
import jax.scipy.linalg
import numpy as np

jax.config.update("jax_enable_x64", True)

N_INPUTS = 4096
ORDER_BASE = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)
INPUTS = jnp.asarray(np.arange(N_INPUTS, dtype=np.int64))


def target_signs() -> np.ndarray:
    from search import logo
    return np.asarray([1.0 if not logo(x, y) else -1.0
                       for y in range(64) for x in range(64)], dtype=np.float64)


TARGET = jnp.asarray(target_signs())


def unitary4(params: jnp.ndarray) -> jnp.ndarray:
    """Exponentiate a 16-real-parameter Hermitian matrix."""
    h = jnp.zeros(params.shape[:-1] + (4, 4), dtype=jnp.complex128)
    for i in range(4):
        h = h.at[..., i, i].set(params[..., i])
    cursor = 4
    for i in range(4):
        for j in range(i + 1, 4):
            value = params[..., cursor] + 1j * params[..., cursor + 1]
            h = h.at[..., i, j].set(value)
            h = h.at[..., j, i].set(jnp.conj(value))
            cursor += 2
    return jax.scipy.linalg.expm(1j * h)


def forward(params: jnp.ndarray, order: tuple[int, ...]) -> jnp.ndarray:
    matrices = unitary4(params)
    state = jnp.zeros((N_INPUTS, 4), dtype=jnp.complex128).at[:, 0].set(1.0)
    for position, bit in enumerate(order):
        branch = ((INPUTS >> bit) & 1).astype(jnp.int32)
        selected = matrices[position, branch]
        state = jnp.einsum("bij,bj->bi", selected, state)
    return state


def loss(params: jnp.ndarray, order: tuple[int, ...]) -> jnp.ndarray:
    state = forward(params, order)
    desired = TARGET.astype(jnp.complex128)
    error = state[:, 0] - desired
    return jnp.mean(
        jnp.real(error * jnp.conj(error))
        + jnp.sum(jnp.real(state[:, 1:] * jnp.conj(state[:, 1:])), axis=1)
    )


def optimize(length: int, steps: int, seed: int, learning_rate: float) -> dict:
    order = tuple(ORDER_BASE[i % len(ORDER_BASE)] for i in range(length))
    params = 0.15 * jax.random.normal(
        jax.random.PRNGKey(seed), (length, 2, 16), dtype=jnp.float64
    )
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
    return {
        "length": length,
        "steps": steps,
        "seed": seed,
        "order": list(order),
        "loss": best_loss,
        "minimum_target_real_amplitude": float(np.min(target * state[:, 0].real)),
        "maximum_target_amplitude_error": float(np.max(np.abs(target * state[:, 0].real - 1.0))),
        "maximum_memory_leakage": float(np.max(np.linalg.norm(state[:, 1:], axis=1))),
        "runtime_seconds": time.time() - started,
        "status": "numerical_only",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=8)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=0.02)
    parser.add_argument("--out", type=Path, default=Path("artifacts/unitary_state_space/qbp/continuous_width4_checkpoint.json"))
    args = parser.parse_args()
    result = optimize(args.length, args.steps, args.seed, args.learning_rate)
    result.update({
        "kind": "continuous width-4 SU(4) QBP phase-process search",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
