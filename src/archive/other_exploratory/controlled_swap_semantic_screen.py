"""Semantic screen for higher-order controlled swaps of current wires."""

from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

from destructive_semantic_search import (
    TARGET,
    affine_distance_proxy,
    apply_rccx_semantic,
    exact_affine_distance,
    initial_wire_truth_tables,
)


def apply_controlled_swap(wires: tuple[int, ...], controls: tuple[int, ...],
                          a: int, b: int) -> tuple[int, ...]:
    if len(set(controls) | {a, b}) != len(controls) + 2:
        raise ValueError("controlled-swap wires must be distinct")
    delta = wires[a] ^ wires[b]
    for control in controls:
        delta &= wires[control]
    out = list(wires)
    out[a] ^= delta
    out[b] ^= delta
    return tuple(out)


def generate_moves(control_size: int, preserve_inputs: bool):
    for controls in itertools.combinations(range(18), control_size):
        remaining = [wire for wire in range(18) if wire not in controls]
        for a, b in itertools.combinations(remaining, 2):
            if preserve_inputs and (a < 12 or b < 12):
                continue
            yield ("cswap", controls, a, b)
    # Include the ordinary RCCX primitive so the screen can distinguish a
    # controlled-swap effect from a nearby single-target update.
    for a, b in itertools.combinations(range(18), 2):
        for target in range(18):
            if target in (a, b) or (preserve_inputs and target < 12):
                continue
            yield ("rccx", a, b, target)


def apply_move(wires, move):
    if move[0] == "cswap":
        return apply_controlled_swap(wires, move[1], move[2], move[3])
    return apply_rccx_semantic(wires, move[1], move[2], move[3])


def run(control_size: int, beam_width: int, layers: int, seed: int,
        preserve_inputs: bool) -> dict:
    rng = random.Random(seed)
    all_moves = tuple(generate_moves(control_size, preserve_inputs))
    beam = [(initial_wire_truth_tables(), ())]
    records = []
    for layer in range(1, layers + 1):
        children = {}
        for wires, history in beam:
            order = list(all_moves)
            rng.shuffle(order)
            for move in order:
                child = apply_move(wires, move)
                children.setdefault(child, (child, history + (move,)))
        ranked = []
        for wires, history in children.values():
            residual, combo = affine_distance_proxy(wires, TARGET, 2)
            ranked.append((residual, rng.random(), combo, wires, history))
        ranked.sort(key=lambda row: (row[0], row[1]))
        beam = [(row[3], row[4]) for row in ranked[:beam_width]]
        best = beam[0]
        exact, exact_combo = exact_affine_distance(best[0], TARGET)
        records.append({
            "layer": layer,
            "candidate_states": len(children),
            "proxy_residual": ranked[0][0],
            "exact_residual": exact,
            "exact_combo": exact_combo,
            "moves": best[1],
        })
    return {
        "experiment": "higher-order controlled-swap semantic screen",
        "control_size": control_size,
        "beam_width": beam_width,
        "layers": layers,
        "seed": seed,
        "preserve_inputs": preserve_inputs,
        "move_count": len(all_moves),
        "target_marked_states": TARGET.bit_count(),
        "records": records,
        "status": "semantic_screen_only; no affine completion",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-size", type=int, default=2)
    parser.add_argument("--beam", type=int, default=16)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--preserve-inputs", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = run(args.control_size, args.beam, args.layers, args.seed,
                 args.preserve_inputs)
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
