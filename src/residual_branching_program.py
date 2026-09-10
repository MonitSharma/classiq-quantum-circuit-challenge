"""Extract the exact residual-function branching program of the logo.

This is a structural diagnostic for a destructive reversible implementation.
After consuming a prefix of the chosen coordinate order, each prefix is
represented by the remaining Boolean truth table.  Equal residual tables are
merged.  The resulting layered DAG is not itself reversible, but it exposes
the state count and transition pattern that a reversible embedding must carry.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from search import logo


DEFAULT_ORDER = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)


def target_table() -> tuple[int, ...]:
    return tuple(
        int(logo(x, y))
        for y in range(64)
        for x in range(64)
    )


def residual_program(order: tuple[int, ...] = DEFAULT_ORDER) -> dict:
    values = target_table()
    layers: list[dict[tuple[int, ...], int]] = []
    for consumed in range(len(order) + 1):
        remaining = order[consumed:]
        layer: dict[tuple[int, ...], int] = {}
        for prefix in range(1 << consumed):
            table = []
            for suffix in range(1 << len(remaining)):
                full_index = 0
                for offset, coordinate_bit in enumerate(order[:consumed]):
                    full_index |= ((prefix >> offset) & 1) << coordinate_bit
                for offset, coordinate_bit in enumerate(remaining):
                    full_index |= ((suffix >> offset) & 1) << coordinate_bit
                table.append(values[full_index])
            key = tuple(table)
            if key not in layer:
                layer[key] = len(layer)
        layers.append(layer)

    transitions: list[list[list[int]]] = []
    for consumed in range(len(order)):
        current = layers[consumed]
        next_layer = layers[consumed + 1]
        layer_transitions: list[list[int]] = []
        for table in sorted(current, key=current.get):
            children = []
            for bit_value in (0, 1):
                # The consumed bit is offset zero in the table index.
                child = tuple(table[bit_value + 2 * suffix]
                              for suffix in range(1 << (len(order) - consumed - 1)))
                children.append(next_layer[child])
            layer_transitions.append(children)
        transitions.append(layer_transitions)

    max_fanin_by_layer = []
    for layer in transitions:
        fixed_bit_fanins = []
        for bit_value in (0, 1):
            counts: dict[int, int] = {}
            for children in layer:
                child = children[bit_value]
                counts[child] = counts.get(child, 0) + 1
            fixed_bit_fanins.append(max(counts.values(), default=1))
        max_fanin_by_layer.append(max(fixed_bit_fanins, default=1))

    reachable_slot_counts = [1]
    slot_mass = {0: 1}
    for layer in transitions:
        next_mass: dict[int, int] = {}
        for bit_value in (0, 1):
            contributions: dict[int, int] = {}
            for state, count in slot_mass.items():
                child = layer[state][bit_value]
                contributions[child] = contributions.get(child, 0) + count
            for child, count in contributions.items():
                next_mass[child] = max(next_mass.get(child, 0), count)
        slot_mass = next_mass
        reachable_slot_counts.append(sum(slot_mass.values()))

    return {
        "variable_order": list(order),
        "marked_states": sum(target_table()),
        "layer_state_counts": [len(layer) for layer in layers],
        "max_layer_states": max(len(layer) for layer in layers),
        "transitions": transitions,
        "max_fanin_by_layer": max_fanin_by_layer,
        "minimum_distinguishing_garbage_bits": [
            math.ceil(math.log2(value)) if value > 1 else 0
            for value in max_fanin_by_layer
        ],
        "minimum_reversible_slot_counts": reachable_slot_counts,
        "maximum_reversible_slots": max(reachable_slot_counts),
        "terminal_values": [
            list(table)[0] for table in layers[-1]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", nargs=12, type=int, default=list(DEFAULT_ORDER))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if sorted(args.order) != list(range(12)):
        raise SystemExit("--order must be a permutation of 0..11")
    result = residual_program(tuple(args.order))
    print(json.dumps({
        key: result[key]
        for key in ("variable_order", "marked_states", "layer_state_counts",
                    "max_layer_states", "max_fanin_by_layer",
                    "minimum_distinguishing_garbage_bits",
                    "minimum_reversible_slot_counts",
                    "maximum_reversible_slots")
    }, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
