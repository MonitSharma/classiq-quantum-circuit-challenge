"""Exact structural screen for shallow nonlinear spectral conjugations.

This module does not synthesize a quantum circuit.  It treats a reversible
coordinate change ``T`` as a permutation of the 12-bit truth table and measures
the Walsh spectrum of the phase vector ``s(z)=(-1)**g(z)`` exactly.  The first
useful falsification is recorded explicitly: because the logo has 1,097 marked
points (an odd population), every nonconstant phase-vector Walsh coefficient
is twice a nonzero odd character sum for every permutation of the truth table.
Thus ordinary Walsh support cannot collapse under any reversible coordinate
change, although coefficient concentration and related diagnostics can still
be measured.

The supported mutations are guaranteed-invertible coordinate updates
``z[target] ^= a(z) & b(z)``.  The target is excluded from both affine control
parities, so the update is an involution for every fixed assignment of the
other coordinates.  Mutations are applied to the current coordinates, making
their composition a permutation without needing a synthesis assumption.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from search import logo


N = 12
SIZE = 1 << N


def truth_table() -> np.ndarray:
    return np.array(
        [int(logo(z & 63, z >> 6)) for z in range(SIZE)], dtype=np.uint8
    )


def phase_vector(bits: np.ndarray) -> np.ndarray:
    return (1 - 2 * bits.astype(np.int64)).astype(np.int64)


def fwht(values: np.ndarray) -> np.ndarray:
    """Return the unnormalized exact Walsh-Hadamard transform."""
    out = np.asarray(values, dtype=np.int64).copy()
    width = 1
    while width < len(out):
        for start in range(0, len(out), width * 2):
            left = out[start : start + width].copy()
            right = out[start + width : start + 2 * width].copy()
            out[start : start + width] = left + right
            out[start + width : start + 2 * width] = left - right
        width *= 2
    return out


def affine_value(z: int, mask: int, constant: int) -> int:
    return ((z & mask).bit_count() ^ constant) & 1


@dataclass(frozen=True)
class Mutation:
    target: int
    mask_a: int
    const_a: int
    mask_b: int
    const_b: int

    def apply(self, mapping: np.ndarray) -> np.ndarray:
        out = mapping.copy()
        for i, z in enumerate(mapping):
            if affine_value(int(z), self.mask_a, self.const_a) and affine_value(
                int(z), self.mask_b, self.const_b
            ):
                out[i] ^= 1 << self.target
        return out

    def as_dict(self) -> dict:
        return {
            "target": self.target,
            "mask_a": self.mask_a,
            "const_a": self.const_a,
            "mask_b": self.mask_b,
            "const_b": self.const_b,
        }


def identity_mapping() -> np.ndarray:
    return np.arange(SIZE, dtype=np.int16)


def inverse_mapping(mapping: np.ndarray) -> np.ndarray:
    inverse = np.empty_like(mapping)
    inverse[mapping] = np.arange(SIZE, dtype=np.int16)
    return inverse


def spectrum(mapping: np.ndarray, bits: np.ndarray) -> dict:
    inverse = inverse_mapping(mapping)
    transformed = bits[inverse]
    coefficients = fwht(phase_vector(transformed))
    support = np.flatnonzero(coefficients)
    weights = np.array([int(i).bit_count() for i in support], dtype=np.int16)
    absolute = np.abs(coefficients)
    order = np.argsort(absolute)[::-1]
    top_k = 32
    return {
        "walsh_support": int(len(support)),
        "walsh_support_fraction": float(len(support) / SIZE),
        "nonconstant_support": int(np.count_nonzero(coefficients[1:])),
        "weighted_support": int(weights.sum()),
        "parity_weight_histogram": {
            str(w): int(np.count_nonzero(weights == w)) for w in range(N + 1)
        },
        "wire_participation": [int(np.count_nonzero(support & (1 << bit))) for bit in range(N)],
        "max_abs_walsh": int(absolute.max()),
        "top32_abs_mass": int(absolute[order[:top_k]].sum()),
        "total_abs_mass": int(absolute.sum()),
        "mapping_is_bijective": bool(np.unique(mapping).size == SIZE),
        "marked_population": int(bits.sum()),
    }


def mutation_cost(m: Mutation) -> dict:
    controls = m.mask_a.bit_count() + m.mask_b.bit_count()
    # A deliberately transparent proxy, not a native-gate estimate.
    return {"control_parity_weight": controls, "abstract_mutation_cost": 1 + controls}


def candidate_score(metrics: dict) -> tuple:
    # Support and weighted support are invariants here, but remain first so a
    # future non-permutation representation cannot silently change the goal.
    return (
        metrics["walsh_support"],
        metrics["weighted_support"],
        -metrics["top32_abs_mass"],
        -metrics["max_abs_walsh"],
    )


def random_mutation(rng: random.Random, max_weight: int = 2) -> Mutation:
    target = rng.randrange(N)
    allowed = [bit for bit in range(N) if bit != target]

    def form() -> tuple[int, int]:
        weight = rng.randint(1, max_weight)
        mask = 0
        for bit in rng.sample(allowed, weight):
            mask |= 1 << bit
        return mask, rng.randrange(2)

    mask_a, const_a = form()
    mask_b, const_b = form()
    return Mutation(target, mask_a, const_a, mask_b, const_b)


def run(samples: int, mutations: int, seed: int, max_weight: int) -> dict:
    bits = truth_table()
    baseline = spectrum(identity_mapping(), bits)
    rng = random.Random(seed)
    best = None
    seen = set()
    for _ in range(samples):
        mapping = identity_mapping()
        chain = []
        for _ in range(mutations):
            for _attempt in range(100):
                mutation = random_mutation(rng, max_weight)
                if mutation not in seen:
                    seen.add(mutation)
                    break
            mapping = mutation.apply(mapping)
            chain.append(mutation)
        metrics = spectrum(mapping, bits)
        record = {
            "mutations": [m.as_dict() for m in chain],
            "mutation_cost": sum((mutation_cost(m)["abstract_mutation_cost"] for m in chain)),
            "metrics": metrics,
            "score": list(candidate_score(metrics)),
        }
        if best is None or tuple(record["score"]) < tuple(best["score"]):
            best = record
    return {
        "n_variables": N,
        "truth_table_size": SIZE,
        "baseline": baseline,
        "best_sampled_candidate": best,
        "samples": samples,
        "mutation_count": mutations,
        "max_affine_control_weight": max_weight,
        "seed": seed,
        "invariant_note": (
            "The phase vector is s(z)=(-1)^g(z). For every nonzero Walsh mask S, "
            "W_s(S)=-2*sum_{g(z)=1}(-1)^(S·z). The inner sum has 1,097 terms, "
            "so it is odd and nonzero; hence W_s(S) is 2 mod 4 up to sign. "
            "At S=0, W_s(0)=4096-2*1097=1902. Ordinary Walsh support is "
            "therefore exactly 4096 for every reversible coordinate change."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--mutations", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-weight", type=int, default=2)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run(args.samples, args.mutations, args.seed, args.max_weight)
    output = args.output or Path(
        f"artifacts/nonlinear_spectral_screen_m{args.mutations}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
