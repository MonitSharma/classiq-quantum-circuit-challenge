"""Bounded smoke test for the pinned rqcopt-mpo Riemannian optimizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.stats import unitary_group

EXTERNAL = Path(__file__).resolve().parents[1] / "external" / "rqcopt-mpo"
sys.path.insert(0, str(EXTERNAL))

import jax.numpy as jnp  # noqa: E402
from jax import vmap  # noqa: E402

from rqcopt_mpo.adam import RieADAM  # noqa: E402
from rqcopt_mpo.tn_brickwall_methods import (  # noqa: E402
    compute_full_gradient,
)
from rqcopt_mpo.util import (  # noqa: E402
    get_identity_layers,
    inner_product,
    project_unitary_tangent,
    retract_unitary,
)

from mpo_contract import target_mpo  # noqa: E402
from mpo_target import DEFAULT_ORDER  # noqa: E402


def make_layers(n_layers: int) -> tuple[jnp.ndarray, list[bool]]:
    odd = True
    chunks = []
    parity = []
    for _ in range(n_layers):
        chunks.append(get_identity_layers(12, 1, odd))
        parity.append(odd)
        odd = not odd
    return jnp.concatenate(chunks), parity


def run(
    n_layers: int,
    iterations: int,
    lr: float,
    output: str | Path,
    initialization: str = "random",
    warm_start: str | None = None,
    order: tuple[int, ...] = DEFAULT_ORDER,
) -> dict:
    target = [jnp.asarray(core) for core in target_mpo(order)]
    initial, parity = make_layers(n_layers)
    # The upstream ADAM implementation stores each gate as a 4x4 matrix for
    # its per-gate second moment.  Convert to tensor form only at the MPO
    # contraction boundary.
    initial = initial.reshape((-1, 4, 4))
    if warm_start is not None:
        loaded = np.load(warm_start)["gates"]
        if loaded.ndim != 3 or loaded.shape[1:] != (4, 4):
            raise ValueError("warm start must contain a gate list shaped (n,4,4)")
        expected = sum(6 if odd else 5 for odd in parity)
        if loaded.shape[0] > expected:
            raise ValueError("warm start has more gates than the requested target topology")
        identity = np.repeat(
            np.eye(4, dtype=np.complex128)[None, :, :], expected - loaded.shape[0], axis=0
        )
        initial = jnp.asarray(np.concatenate([loaded, identity], axis=0))
        initialization = "warm_start"
    elif initialization == "random":
        rng = np.random.default_rng(20260911)
        initial = jnp.asarray(
            np.asarray([unitary_group.rvs(4, random_state=rng) for _ in range(initial.shape[0])])
        )
    elif initialization == "near_identity":
        rng = np.random.default_rng(20260911)
        gates = []
        for _ in range(initial.shape[0]):
            h = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
            h = (h + h.conj().T) / 2.0
            gates.append(expm(0.1j * h))
        initial = jnp.asarray(np.asarray(gates))
    elif initialization != "identity":
        raise ValueError("initialization must be identity, near_identity, random, or warm_start")

    def objective(gates):
        gates = gates.reshape((-1, 2, 2, 2, 2))
        per_layer = []
        pos = 0
        for odd in parity:
            count = 6 if odd else 5
            per_layer.append(gates[pos : pos + count])
            pos += count
        gradient, overlap = compute_full_gradient(
            target, per_layer, parity, max_bondim=64, compute_overlap=True
        )
        dimension = 2**12
        magnitude = jnp.abs(overlap)
        phase = jnp.where(magnitude > 0, overlap / magnitude, 1.0 + 0.0j)
        # compute_full_gradient returns the Euclidean overlap derivative.
        # Align it with the current overlap before projecting to the SU(4)
        # tangent space; this differentiates |overlap| rather than Re(overlap).
        aligned = (jnp.conj(phase) * gradient).reshape((-1, 4, 4))
        current = gates.reshape((-1, 4, 4))
        projected = vmap(
            lambda u, z: project_unitary_tangent(u, z, use_TN=False)
        )(current, aligned)
        cost = 2.0 - 2.0 * magnitude / dimension
        return cost, (-projected)

    def overlap_for(gates):
        tensor_gates = gates.reshape((-1, 2, 2, 2, 2))
        per_layer = []
        pos = 0
        for odd in parity:
            count = 6 if odd else 5
            per_layer.append(tensor_gates[pos : pos + count])
            pos += count
        _, overlap = compute_full_gradient(
            target, per_layer, parity, max_bondim=64, compute_overlap=True
        )
        return overlap

    initial_overlap = overlap_for(initial)

    retract = vmap(lambda v, eta: retract_unitary(v, eta, use_TN=False))
    project = vmap(lambda u, z: project_unitary_tangent(u, z, use_TN=False))
    metric = vmap(lambda v, x, y: inner_product(v, x, y, use_TN=False))

    optimizer = RieADAM(maxiter=iterations, lr=lr)
    result, evaluations, losses = optimizer.minimize(
        function=objective,
        initial_point=initial,
        retract=retract,
        projection=project,
        metric=metric,
    )
    _, final_overlap = objective(result)
    # objective returns the gradient as its second component; recompute the
    # scalar overlap directly to avoid reporting the gradient here.
    result_tensor = result.reshape((-1, 2, 2, 2, 2))
    per_layer = []
    pos = 0
    for odd in parity:
        count = 6 if odd else 5
        per_layer.append(result_tensor[pos : pos + count])
        pos += count
    _, overlap = compute_full_gradient(
        target, per_layer, parity, max_bondim=64, compute_overlap=True
    )
    report = {
        "n_layers": n_layers,
        "iterations_requested": iterations,
        "evaluations": evaluations,
        "learning_rate": lr,
        "initialization": initialization,
        "warm_start": warm_start,
        "order": list(order),
        "initial_overlap_real": float(jnp.real(initial_overlap)),
        "initial_overlap_imag": float(jnp.imag(initial_overlap)),
        "initial_process_fidelity": float(abs(complex(initial_overlap)) ** 2 / 4096**2),
        "final_overlap_real": float(jnp.real(overlap)),
        "final_overlap_imag": float(jnp.imag(overlap)),
        "final_process_fidelity": float(abs(complex(overlap)) ** 2 / 4096**2),
        "loss_history": [float(x) for x in losses],
        "external_commit": "95f0898f7baa6579de512eba8b00386bd6b05217",
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), gates=np.asarray(result))
    progress = output.parent / "progress.jsonl"
    with progress.open("a") as stream:
        stream.write(json.dumps(report) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument(
        "--initialization", choices=["identity", "near_identity", "random"], default="random"
    )
    parser.add_argument("--warm-start")
    parser.add_argument("--order", choices=["tt", "challenge", "reverse", "xy"], default="tt")
    parser.add_argument(
        "--output", default="artifacts/mpo_native/rqcopt_smoke.json"
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.layers,
                args.iterations,
                args.lr,
                args.output,
                args.initialization,
                args.warm_start,
                {
                    "tt": DEFAULT_ORDER,
                    "challenge": tuple(range(12)),
                    "reverse": tuple(reversed(range(12))),
                    "xy": tuple(sum(([i, 6 + i] for i in range(6)), [])),
                }[args.order],
            ),
            indent=2,
        )
    )
