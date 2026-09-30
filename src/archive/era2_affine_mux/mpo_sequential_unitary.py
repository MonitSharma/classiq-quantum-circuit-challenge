"""Sequential MPO-memory unitary block optimizer.

This is distinct from the earlier SU(4)-bus experiment.  Each data site is
coupled to a four-qubit memory by one arbitrary 32x32 unitary block.  The
target TT gives exact left/right environments, so a polar update optimizes
each block without forming the 16-qubit candidate operator.  The result is
only an abstract block circuit; decomposition and exhaustive verification are
required before it can be considered a candidate.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from mpo_gate_sweep import haar_unitary
from mpo_target import DEFAULT_ORDER, ordered_tensor, tt_svd


N = 12
MEMORY = 16
PHYSICAL = 2
BLOCK = MEMORY * PHYSICAL


def target_cores():
    cores, _ = tt_svd(ordered_tensor(DEFAULT_ORDER))
    return cores


def project_unitary(environment: np.ndarray) -> np.ndarray:
    left, _, right_h = np.linalg.svd(environment.conj(), full_matrices=False)
    unitary = left @ right_h
    unitary *= np.exp(-1j * np.angle(np.linalg.det(unitary)) / BLOCK)
    return unitary


def transfer(core: np.ndarray, block: np.ndarray) -> np.ndarray:
    """Return T[left,input_memory,right,output_memory]."""
    tensor = block.reshape(MEMORY, PHYSICAL, MEMORY, PHYSICAL)
    return np.einsum("lzr,oziz->liro", core, tensor)


def forward_environments(cores, blocks):
    forward = [np.zeros((cores[0].shape[0], MEMORY), dtype=np.complex128)]
    forward[0][0, 0] = 1
    for core, block, left in zip(cores, blocks, forward):
        forward.append(np.einsum("li,liro->ro", left, transfer(core, block)))
    return forward


def backward_environments(cores, blocks):
    backward = [None] * (N + 1)
    backward[N] = np.zeros((cores[-1].shape[2], MEMORY), dtype=np.complex128)
    backward[N][0, 0] = 1
    for i in range(N - 1, -1, -1):
        tensor = blocks[i].reshape(MEMORY, PHYSICAL, MEMORY, PHYSICAL)
        backward[i] = np.einsum(
            "lzr,oziz,ro->li", cores[i], tensor, backward[i + 1]
        )
    return backward


def overlap(cores, blocks) -> complex:
    return complex(forward_environments(cores, blocks)[-1][0, 0])


def local_environment(core, left, right) -> np.ndarray:
    """Environment E with overlap = sum(E[row,col] * block[row,col])."""
    environment = np.zeros((BLOCK, BLOCK), dtype=np.complex128)
    for bit in range(PHYSICAL):
        # E[output_memory,input_memory] for the diagonal physical element.
        values = np.einsum("la,lr,ro->oa", left, core[:, bit, :], right)
        for output_memory in range(MEMORY):
            for input_memory in range(MEMORY):
                row = output_memory * PHYSICAL + bit
                col = input_memory * PHYSICAL + bit
                environment[row, col] = values[output_memory, input_memory]
    return environment


def initialize(seed: int, mode: str) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    if mode == "identity":
        return [np.eye(BLOCK, dtype=np.complex128) for _ in range(N)]
    if mode == "haar":
        return [haar_unitary(rng, BLOCK) for _ in range(N)]
    if mode == "near_identity":
        blocks = []
        for _ in range(N):
            h = rng.normal(size=(BLOCK, BLOCK)) + 1j * rng.normal(size=(BLOCK, BLOCK))
            h = (h + h.conj().T) / 2
            left, _, right_h = np.linalg.svd(np.eye(BLOCK) + 0.05j * h)
            blocks.append(left @ right_h)
        return blocks
    raise ValueError(f"unknown initialization {mode!r}")


def run(sweeps: int, seed: int, initialization: str, output: str | Path) -> dict:
    cores = target_cores()
    blocks = initialize(seed, initialization)
    initial = abs(overlap(cores, blocks)) ** 2 / (2**N) ** 2
    history = []
    start = time.perf_counter()
    for _ in range(sweeps):
        forward = forward_environments(cores, blocks)
        backward = backward_environments(cores, blocks)
        for i in range(N):
            blocks[i] = project_unitary(
                local_environment(cores[i], forward[i], backward[i + 1])
            )
            # Refresh the left environment immediately so the sweep is truly
            # coordinate-ascent rather than using stale blocks.
            forward[i + 1] = np.einsum(
                "li,liro->ro", forward[i], transfer(cores[i], blocks[i])
            )
        fidelity = float(abs(overlap(cores, blocks)) ** 2 / (2**N) ** 2)
        history.append(fidelity)
    report = {
        "architecture": "sequential four-ancilla memory with 32x32 unitary blocks",
        "memory_dimension": MEMORY,
        "blocks": N,
        "block_dimension": BLOCK,
        "seed": seed,
        "initialization": initialization,
        "sweeps": sweeps,
        "initial_process_fidelity": float(initial),
        "final_process_fidelity": history[-1] if history else float(initial),
        "history": history,
        "wall_time_seconds": time.perf_counter() - start,
        "clean_memory_boundary": True,
        "promoted": False,
        "reason": "abstract 32x32 block ansatz; no two-qubit decomposition or verification",
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(output.with_suffix(".npz"), blocks=np.asarray(blocks))
    with Path("artifacts/mpo_native/progress.jsonl").open("a") as stream:
        stream.write(json.dumps({"kind": "sequential_block_sweep", **report}, separators=(",", ":")) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweeps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--initialization", choices=("identity", "near_identity", "haar"), default="near_identity")
    parser.add_argument("--output", default="artifacts/mpo_native/sequential_block_sweep.json")
    args = parser.parse_args()
    print(json.dumps(run(**vars(args)), indent=2))
