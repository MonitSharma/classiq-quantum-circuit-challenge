"""Bounded meet-in-the-middle search for exact finite-group QBPs.

This is intentionally a restricted-alphabet diagnostic.  It hashes a sampled
trajectory signature to find candidate half-program matches, then verifies any
candidate against all 4096 inputs with the exact multiplication table.
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from qbp.finite_group import IDENTITY, INVERSE, MULTIPLY, TARGET, mismatch_count


GROUP_TABLE = np.asarray(MULTIPLY, dtype=np.uint8)
INPUT_INDICES = np.arange(4096, dtype=np.int64)
TARGET_ARRAY = np.asarray(TARGET, dtype=np.uint8)


def trajectory(program: tuple[tuple[int, int, int], ...]) -> np.ndarray:
    states = np.full(4096, IDENTITY, dtype=np.uint8)
    for bit, zero, one in program:
        chosen = np.where(((INPUT_INDICES >> bit) & 1) != 0, one, zero)
        states = GROUP_TABLE[chosen, states]
    return states


def _choice_array(order: tuple[int, ...], pair_options: tuple[tuple[int, int], ...]) -> np.ndarray:
    return np.asarray(
        [choices for choices in itertools.product(pair_options, repeat=len(order))],
        dtype=np.uint8,
    )


def _batch_trajectories(choices: np.ndarray, order: tuple[int, ...]) -> np.ndarray:
    states = np.full((len(choices), 4096), IDENTITY, dtype=np.uint8)
    for position, bit in enumerate(order):
        chosen = np.where(
            ((INPUT_INDICES >> bit) & 1)[None, :],
            choices[:, position, 1, None],
            choices[:, position, 0, None],
        )
        states = GROUP_TABLE[chosen, states]
    return states


def search(
    order: tuple[int, ...],
    alphabet: tuple[int, ...],
    sample_count: int,
    batch_size: int = 256,
) -> dict:
    half = len(order) // 2
    prefix_order = order[:half]
    suffix_order = order[half:]
    pair_options = tuple(itertools.product(alphabet, repeat=2))
    sample = np.linspace(0, 4095, sample_count, dtype=np.int64)
    suffixes: dict[bytes, list[tuple[tuple[int, int, int], ...]]] = {}
    suffix_choices = _choice_array(suffix_order, pair_options)
    suffix_count = len(suffix_choices)
    for start in range(0, suffix_count, batch_size):
        batch = suffix_choices[start:start + batch_size]
        states = _batch_trajectories(batch, suffix_order)
        for offset, signature in enumerate(states[:, sample].copy()):
            choices = batch[offset]
            program = tuple(
                (bit, int(pair[0]), int(pair[1]))
                for bit, pair in zip(suffix_order, choices)
            )
            suffixes.setdefault(signature.tobytes(), []).append(program)
    prefix_count = 0
    exact_candidates = 0
    prefix_choices = _choice_array(prefix_order, pair_options)
    for start in range(0, len(prefix_choices), batch_size):
        batch = prefix_choices[start:start + batch_size]
        states = _batch_trajectories(batch, prefix_order)
        required = GROUP_TABLE[TARGET_ARRAY[None, :], np.asarray(INVERSE, dtype=np.uint8)[states]]
        for offset, signature in enumerate(required[:, sample].copy()):
            choices = batch[offset]
            program = tuple(
                (bit, int(pair[0]), int(pair[1]))
                for bit, pair in zip(prefix_order, choices)
            )
            for suffix in suffixes.get(signature.tobytes(), ()):
                exact_candidates += 1
                combined = program + suffix
                if mismatch_count(combined) == 0:
                    return {
                        "status": "exact",
                        "program": [list(item) for item in combined],
                        "checked_prefix_programs": prefix_count + offset + 1,
                        "checked_suffix_programs": suffix_count,
                        "exact_candidates": exact_candidates,
                    }
        prefix_count += len(batch)
    return {
        "status": "not_found",
        "checked_prefix_programs": prefix_count,
        "checked_suffix_programs": suffix_count,
        "exact_candidates": exact_candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=8)
    parser.add_argument("--alphabet", nargs="+", type=int, default=[1, 3, 5, 7])
    parser.add_argument("--sample-count", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.length % 2 or any(value < 0 or value >= len(MULTIPLY) for value in args.alphabet):
        raise SystemExit("length must be even and alphabet entries must be valid group indices")
    order_base = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)
    order = tuple(order_base[i % len(order_base)] for i in range(args.length))
    started = time.time()
    result = search(order, tuple(args.alphabet), args.sample_count, args.batch_size)
    result.update({
        "kind": "restricted exact finite-group QBP meet-in-the-middle",
        "group": "binary_icosahedral",
        "length": args.length,
        "order": list(order),
        "alphabet": args.alphabet,
        "sample_count": args.sample_count,
        "batch_size": args.batch_size,
        "elapsed_seconds": time.time() - started,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    })
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
