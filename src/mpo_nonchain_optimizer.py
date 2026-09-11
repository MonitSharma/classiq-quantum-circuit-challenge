"""Small autodiff capability test for one arbitrary-pair matching layer.

The exact non-adjacent MPO contraction primitive is tested separately in
``mpo_nonadjacent_smoke.py``.  Differentiating through an MPO re-factorization
is not currently robust in the installed JAX version (QR derivatives are not
implemented and exact SVDs have repeated-singular-value gauge singularities),
so this bounded optimizer uses the exact diagonal contribution to the process
overlap for one disjoint matching.  It is intentionally a capability test,
not a claim that one layer is a competitive circuit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
from scipy.linalg import expm

from mpo_target import DEFAULT_ORDER, ordered_tensor
from mpo_topologies import round_robin_matchings


def embedded_maps(n_sites: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dimension = 2**n_sites
    rows, cols, local_rows, local_cols = [], [], [], []
    for column in range(dimension):
        bits = [(column >> (n_sites - 1 - i)) & 1 for i in range(n_sites)]
        local_column = 2 * bits[0] + bits[-1]
        for local_row in range(4):
            row_bits = bits.copy()
            row_bits[0], row_bits[-1] = local_row >> 1, local_row & 1
            row = sum(bit << (n_sites - 1 - i) for i, bit in enumerate(row_bits))
            rows.append(row)
            cols.append(column)
            local_rows.append(local_row)
            local_cols.append(local_column)
    return tuple(np.asarray(x, dtype=np.int32) for x in (rows, cols, local_rows, local_cols))


MAPS = {n: embedded_maps(n) for n in range(2, 13)}


def embed_gate(gate: jnp.ndarray, n_sites: int) -> jnp.ndarray:
    rows, cols, local_rows, local_cols = MAPS[n_sites]
    out = jnp.zeros((2**n_sites, 2**n_sites), dtype=gate.dtype)
    return out.at[rows, cols].set(gate[local_rows, local_cols])


def apply_nonadjacent_jax(mpo: list[jnp.ndarray], first: int, second: int, gate: jnp.ndarray) -> list[jnp.ndarray]:
    window = mpo[first : second + 1]
    merged = window[0]
    for core in window[1:]:
        merged = jnp.tensordot(merged, core, axes=(-1, 0))
    n_sites = second - first + 1
    block_perm = [0]
    block_perm.extend(1 + 2 * i for i in range(n_sites))
    block_perm.extend(2 + 2 * i for i in range(n_sites))
    block_perm.append(2 * n_sites + 1)
    merged = jnp.transpose(merged, block_perm)
    left, right = merged.shape[0], merged.shape[-1]
    merged = merged.reshape(left, 2**n_sites, 2**n_sites, right)
    merged = jnp.einsum("co,lior->licr", embed_gate(gate, n_sites), merged)

    merged = merged.reshape((left,) + (2,) * n_sites + (2,) * n_sites + (right,))
    interleave = [0]
    for i in range(n_sites):
        interleave.extend((1 + i, 1 + n_sites + i))
    interleave.append(2 * n_sites + 1)
    remaining = jnp.transpose(merged, interleave)
    cores = []
    bond = left
    for _ in range(n_sites - 1):
        matrix = remaining.reshape(bond * 4, -1)
        # QR avoids the repeated-singular-value derivative singularities that
        # appear when differentiating an exact SVD of a unitary matching layer.
        q, r = jnp.linalg.qr(matrix, mode="reduced")
        rank = q.shape[1]
        cores.append(q.reshape(bond, 2, 2, rank))
        remaining = r.reshape((rank,) + remaining.shape[3:])
        bond = rank
    cores.append(remaining.reshape(bond, 2, 2, right))
    return list(mpo[:first]) + cores + list(mpo[second + 1 :])


def identity_mpo(n_sites: int = 12) -> list[jnp.ndarray]:
    core = jnp.eye(2, dtype=jnp.complex128).reshape(1, 2, 2, 1)
    return [core for _ in range(n_sites)]


def overlap(target: list[jnp.ndarray], candidate: list[jnp.ndarray]) -> jnp.ndarray:
    env = jnp.ones((1, 1), dtype=jnp.complex128)
    for left, right in zip(target, candidate):
        env = jnp.einsum("ab,aioc,biod->cd", env, left.conj(), right)
    return jnp.squeeze(env)


def matching_slots(index: int = 3) -> list[tuple[int, int]]:
    inverse = {physical: slot for slot, physical in enumerate(DEFAULT_ORDER)}
    return [tuple(sorted((inverse[a], inverse[b]))) for a, b in round_robin_matchings()[index]]


def diagonal_indices(pairs: list[tuple[int, int]]) -> np.ndarray:
    """Return each gate's diagonal basis index for every ordered basis state."""
    indices = []
    for state in range(2**len(DEFAULT_ORDER)):
        bits = [(state >> (len(DEFAULT_ORDER) - 1 - i)) & 1 for i in range(len(DEFAULT_ORDER))]
        indices.append([2 * bits[first] + bits[second] for first, second in pairs])
    return np.asarray(indices, dtype=np.int32)


def run(iterations: int, learning_rate: float, output: str | Path) -> dict:
    pairs = matching_slots()
    target_signs = jnp.asarray(ordered_tensor(DEFAULT_ORDER).reshape(-1), dtype=jnp.float64)
    indices = jnp.asarray(diagonal_indices(pairs))
    rng = np.random.default_rng(20260911)
    gates = []
    for _ in pairs:
        h = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
        h = (h + h.conj().T) / 2
        gates.append(expm(0.1j * h))
    gates = jnp.asarray(np.asarray(gates))

    def loss_fn(current):
        # The matching is disjoint, so every diagonal amplitude is the
        # product of one diagonal entry from each 4x4 gate.  This is the
        # exact trace overlap with the diagonal logo operator; no state-only
        # surrogate is used.
        diagonal_entries = jnp.stack([gate.diagonal() for gate in current])
        candidate_diagonal = jnp.prod(
            jnp.take_along_axis(diagonal_entries, indices.T, axis=1), axis=0
        )
        value = jnp.sum(target_signs * candidate_diagonal)
        return 1.0 - jnp.abs(value) ** 2 / 4096**2

    losses = []
    for _ in range(iterations):
        loss, gradient = jax.value_and_grad(loss_fn)(gates)
        losses.append(float(loss))
        projected = 0.5 * gradient - 0.5 * jnp.einsum(
            "aij,akj,akl->ail", gates, gradient.conj(), gates
        )
        updated = gates - learning_rate * projected
        u, _, vh = jnp.linalg.svd(updated)
        gates = u @ vh
    final_loss = float(loss_fn(gates))
    report = {
        "pairs": [list(pair) for pair in pairs],
        "iterations": iterations,
        "learning_rate": learning_rate,
        "initial_process_fidelity": 1.0 - losses[0] if losses else None,
        "final_process_fidelity": 1.0 - final_loss,
        "loss_history": losses,
        "optimizer": "JAX autodiff of exact one-layer process overlap + per-gate polar retraction",
        "objective_scope": "exact diagonal contribution for one disjoint matching layer",
        "not_promoted": True,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), gates=np.asarray(gates))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--output", default="artifacts/mpo_native/nonchain_optimizer.json")
    args = parser.parse_args()
    print(json.dumps(run(args.iterations, args.learning_rate, args.output), indent=2))
