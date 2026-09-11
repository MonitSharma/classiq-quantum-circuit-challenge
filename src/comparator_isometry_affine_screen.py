"""Resource and affine-garbage screen for the 3+3-ancilla isometry idea."""

import itertools
import json
import random
from pathlib import Path

from comparator_oracle_structure import X_C, X_LVL, Y_B, Y_M


def rank2(rows):
    rows = list(rows)
    rank = 0
    for bit in range(6):
        pivot = next((i for i in range(rank, len(rows))
                      if (rows[i] >> bit) & 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            if i != rank and ((rows[i] >> bit) & 1): rows[i] ^= rows[rank]
        rank += 1
    return rank


def buckets(c0, c1):
    out = {}
    for i, key in enumerate(zip(c0, c1)):
        out.setdefault(tuple(key), []).append(i)
    return out


def projection_injective(masks, groups):
    for members in groups.values():
        values = [tuple((i & mask).bit_count() for mask in masks) for i in members]
        # Use parity, not Hamming weight, for a GF(2) linear form.
        values = [tuple((i & mask).bit_count() & 1 for mask in masks)
                  for i in members]
        if len(set(values)) != len(values): return False
    return True


def find_projection(groups, seed):
    rng = random.Random(seed)
    masks = list(range(1, 64))
    for _ in range(200000):
        candidate = rng.sample(masks, 5)
        if rank2(candidate) == 5 and projection_injective(candidate, groups):
            return candidate
    return None


def side_report(name, c0, c1, seed):
    groups = buckets(c0, c1)
    sizes = sorted(len(v) for v in groups.values())
    projection = find_projection(groups, seed)
    return {
        "side": name,
        "bucket_count": len(groups),
        "bucket_sizes": sizes,
        "max_bucket": max(sizes),
        "minimum_garbage_bits": max((size - 1).bit_length() for size in sizes),
        "affine_projection_masks": projection,
        "affine_projection_rank": rank2(projection) if projection else None,
        "affine_projection_is_injective_per_bucket": bool(projection),
        "code_plus_garbage_output_width": 9,
    }


def main():
    report = {
        "x": side_report("x", X_C, X_LVL, 20260911),
        "y": side_report("y", Y_B, Y_M, 20260912),
        "resource_identity": "6 data wires + 3 clean ancillas = 9 wires per side",
        "interpretation": "five affine garbage bits can make the fixed code embedding reversible if the nonlinear code bits are computed into the remaining four outputs",
        "status": "exact resource/affine screen; no native classifier claimed",
    }
    path = Path("artifacts/comparator_oracle/three_plus_three_affine_screen.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
