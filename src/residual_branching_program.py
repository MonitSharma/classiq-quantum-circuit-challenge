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
    layers: list[dict[tuple[int, ...], int]] = [{values: 0}]
    transitions: list[list[list[int]]] = []
    for position, bit in enumerate(order):
        current = layers[-1]
        next_layer: dict[tuple[int, ...], int] = {}
        layer_transitions: list[list[int]] = []
        remaining = order[position + 1:]
        for table, state_id in sorted(current.items(), key=lambda item: item[1]):
            children: list[int] = []
            for bit_value in (0, 1):
                child_values = []
                for remaining_index in range(1 << len(remaining)):
                    full_index = (bit_value << bit)
                    for offset, remaining_bit in enumerate(remaining):
                        full_index |= (
                            ((remaining_index >> offset) & 1) << remaining_bit
                        )
                    # The table's index is over the variables not yet
                    # consumed, in the order in which they are consumed.
                    table_index = 0
                    for offset, table_bit in enumerate(order[position:]):
                        full_value = (full_index >> table_bit) & 1
                        table_index |= full_value << offset
                    child_values.append(table[table_index])
                child = tuple(child_values)
                if child not in next_layer:
                    next_layer[child] = len(next_layer)
                children.append(next_layer[child])
            layer_transitions.append(children)
        transitions.append(layer_transitions)
        layers.append(next_layer)

    return {
        "variable_order": list(order),
        "marked_states": sum(target_table()),
        "layer_state_counts": [len(layer) for layer in layers],
        "max_layer_states": max(len(layer) for layer in layers),
        "transitions": transitions,
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
                    "max_layer_states")
    }, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
