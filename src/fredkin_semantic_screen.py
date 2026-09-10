"""Bounded semantic screen for destructive controlled-swap (Fredkin) moves.

Fredkin is a reversible monomial primitive not represented by an RCCX update:
controlled on the current content of ``c``, it swaps the current contents of
``a`` and ``b``.  It is lowered as CX(b,a), RCCX(c,a,b), CX(b,a), with the
exact inverse used by any eventual C-dagger-Z-C oracle.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

from destructive_semantic_search import (
    TARGET,
    affine_distance_proxy,
    exact_affine_distance,
    initial_wire_truth_tables,
)


ALL_ONES = (1 << 4096) - 1


def apply_fredkin(wires: tuple[int, ...], control: int, a: int,
                  b: int) -> tuple[int, ...]:
    if len({control, a, b}) != 3:
        raise ValueError("Fredkin wires must be distinct")
    out = list(wires)
    delta = wires[control] & (wires[a] ^ wires[b])
    out[a] ^= delta
    out[b] ^= delta
    return tuple(out)


@dataclass(frozen=True)
class State:
    wires: tuple[int, ...]
    moves: tuple[tuple[int, int, int], ...]


def moves(preserve_inputs: bool):
    for control in range(18):
        for a in range(18):
            for b in range(a + 1, 18):
                if control in (a, b):
                    continue
                if preserve_inputs and (a < 12 or b < 12):
                    continue
                yield control, a, b


def screen(beam_width: int, layers: int, seed: int,
           preserve_inputs: bool) -> dict:
    rng = random.Random(seed)
    beam = [State(initial_wire_truth_tables(), ())]
    records = []
    all_moves = tuple(moves(preserve_inputs))
    for layer in range(1, layers + 1):
        candidates: dict[tuple[int, ...], State] = {}
        for state in beam:
            # Full enumeration is small enough for the bounded screen.  A
            # deterministic shuffle prevents low-index physical wires from
            # dominating ties without changing the candidate set.
            order = list(all_moves)
            rng.shuffle(order)
            for control, a, b in order:
                child_wires = apply_fredkin(state.wires, control, a, b)
                if child_wires in candidates:
                    continue
                candidates[child_wires] = State(
                    child_wires, state.moves + ((control, a, b),)
                )
        ranked = []
        for state in candidates.values():
            residual, combo = affine_distance_proxy(state.wires, TARGET, 2)
            ranked.append((residual, len(state.moves), rng.random(), combo, state))
        ranked.sort(key=lambda row: (row[0], row[1], row[2]))
        beam = [row[-1] for row in ranked[:beam_width]]
        best = beam[0]
        exact, exact_combo = exact_affine_distance(best.wires, TARGET)
        records.append({
            "layer": layer,
            "candidate_states": len(candidates),
            "proxy_residual": ranked[0][0],
            "exact_residual": exact,
            "exact_combo": exact_combo,
            "estimated_forward_depth": 9 * layer,
            "moves": best.moves,
        })
    return {
        "experiment": "destructive Fredkin semantic beam screen",
        "seed": seed,
        "beam_width": beam_width,
        "layers": layers,
        "preserve_inputs": preserve_inputs,
        "move_count": len(all_moves),
        "target_marked_states": TARGET.bit_count(),
        "records": records,
        "status": "semantic_screen_only; no affine completion",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beam", type=int, default=32)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--preserve-inputs", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = screen(args.beam, args.layers, args.seed, args.preserve_inputs)
    print(json.dumps(result, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
