"""Construct and cost a width-limited reversible embedding of the logo DAG.

This module is deliberately a semantic/native-cost experiment.  It does not
replace the protected oracle or emit a competition QASM file.  Six inputs are
loaded into six clean ancillas, leaving an eight-bit state register.  The
remaining six inputs select two permutations of that state register at each
layer of the exact residual-function DAG.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual_branching_program import residual_program


ORDER = (10, 5, 11, 4, 9, 8, 3, 1, 0, 2, 7, 6)
DEFAULT_STATE_BITS = 8


def _cycle_stats(permutation: list[int]) -> dict:
    seen = [False] * len(permutation)
    cycles: list[list[int]] = []
    for start in range(len(permutation)):
        if seen[start]:
            continue
        cycle = []
        current = start
        while not seen[current]:
            seen[current] = True
            cycle.append(current)
            current = permutation[current]
        cycles.append(cycle)

    hamming_transposition_cost = 0
    adjacent_transpositions = 0
    moved = 0
    for cycle in cycles:
        if len(cycle) > 1:
            moved += len(cycle)
            adjacent_transpositions += len(cycle) - 1
            pivot = cycle[0]
            for value in cycle[1:]:
                distance = (pivot ^ value).bit_count()
                # A basis-state transposition at Hamming distance d can be
                # routed through d Gray-neighbor swaps, costing 2d-1 swaps.
                hamming_transposition_cost += 2 * distance - 1
    return {
        "cycles": len(cycles),
        "adjacent_transpositions": adjacent_transpositions,
        "hamming_path_mct_cost": hamming_transposition_cost,
        "max_cycle": max(map(len, cycles), default=0),
        "moved_states": moved,
    }


def _complete_permutation(partial: dict[int, int], capacity: int) -> list[int]:
    permutation = [-1] * capacity
    used_outputs = set()
    for source, target in partial.items():
        if permutation[source] != -1 or target in used_outputs:
            raise AssertionError("partial mapping is not injective")
        permutation[source] = target
        used_outputs.add(target)

    unused_inputs = [i for i, target in enumerate(permutation) if target == -1]
    unused_outputs = [i for i in range(capacity) if i not in used_outputs]
    # Preserve as much of the identity completion as possible.
    for source in unused_inputs:
        if source in unused_outputs:
            permutation[source] = source
            unused_outputs.remove(source)
        else:
            permutation[source] = unused_outputs.pop()
    return permutation


def _choose_labels(source_labels: dict[int, list[int]], capacities: dict[int, int],
                   final_layer: bool, capacity: int) -> dict[int, list[int]]:
    """Assign disjoint state labels, favoring labels reused by both branches."""
    available = set(range(capacity))
    result: dict[int, list[int]] = {}
    for state in sorted(capacities, key=lambda item: (-capacities[item], item)):
        candidates = []
        for label in available:
            score = int(label in source_labels.get(state, []))
            if final_layer and (label & 1) != state:
                continue
            candidates.append((score, label))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        count = capacities[state]
        if len(candidates) < count:
            raise AssertionError("state-label capacity is infeasible")
        chosen = [label for _, label in candidates[:count]]
        result[state] = chosen
        available.difference_update(chosen)
    return result


def _controlled_permutation(current: dict[int, list[int]], next_labels: dict[int, list[int]],
                            transitions: list[list[int]], bit: int,
                            capacity: int) -> list[int]:
    partial: dict[int, int] = {}
    states_by_child: dict[int, list[int]] = {}
    for state in current:
        states_by_child.setdefault(transitions[state][bit], []).append(state)
    for child, states in states_by_child.items():
        outputs = list(next_labels[child])
        for state in sorted(states):
            labels = current[state]
            # First preserve labels that are still available in this child's
            # slot set, then consume distinct remaining slots for the group.
            pairs = []
            for label in labels:
                if label in outputs:
                    pairs.append((label, label))
                    outputs.remove(label)
            paired_sources = {source for source, _ in pairs}
            remaining_inputs = [label for label in labels if label not in paired_sources]
            pairs.extend(zip(remaining_inputs, outputs[:len(remaining_inputs)]))
            del outputs[:len(remaining_inputs)]
            for source, target in pairs:
                if source in partial or target in partial.values():
                    raise AssertionError("active state mapping collision")
                partial[source] = target

    permutation = _complete_permutation(partial, capacity)
    for state, labels in current.items():
        child_labels = set(next_labels[transitions[state][bit]])
        if not all(permutation[label] in child_labels for label in labels):
            raise AssertionError("permutation does not implement residual transition")
    return permutation


def build_model(order: tuple[int, ...] = ORDER,
                state_bits: int = DEFAULT_STATE_BITS,
                output_parity: bool = True) -> dict:
    if state_bits < 6:
        raise ValueError("six loaded prefix bits require at least six state bits")
    capacity = 1 << state_bits
    program = residual_program(order)
    transitions = program["transitions"]
    # Six prefix bits are represented by the first 64 state labels.
    current: dict[int, list[int]] = {}
    state = 0
    for prefix in range(1 << 6):
        state = 0
        for layer in range(6):
            state = transitions[layer][state][(prefix >> layer) & 1]
        current.setdefault(state, []).append(prefix)

    layers = []
    total_adjacent = 0
    total_hamming_cost = 0
    for layer in range(6, 12):
        child_ids = {
            transitions[layer][state][bit]
            for state in current
            for bit in (0, 1)
        }
        source_by_child = {child: [] for child in child_ids}
        for state, labels in current.items():
            for bit in (0, 1):
                child = transitions[layer][state][bit]
                source_by_child[child].extend(labels)
        capacities = {
            child: max(
                sum(len(labels) for state, labels in current.items()
                    if transitions[layer][state][bit] == child)
                for bit in (0, 1)
            )
            for child in source_by_child
        }
        source_sets = {
            child: list({label for label in labels})
            for child, labels in source_by_child.items()
        }
        next_labels = _choose_labels(source_sets, capacities,
                                     final_layer=layer == 11 and output_parity,
                                     capacity=capacity)
        permutations = []
        stats = []
        for bit in (0, 1):
            permutation = _controlled_permutation(current, next_labels,
                                                   transitions[layer], bit,
                                                   capacity)
            permutation_stats = _cycle_stats(permutation)
            permutations.append(permutation)
            stats.append(permutation_stats)
            total_adjacent += permutation_stats["adjacent_transpositions"]
            total_hamming_cost += permutation_stats["hamming_path_mct_cost"]
        layers.append({
            "residual_layer": layer,
            "state_count": len(current),
            "next_state_count": len(next_labels),
            "state_capacities": {str(k): v for k, v in capacities.items()},
            "permutation_stats": stats,
            "permutations": permutations,
        })
        current = next_labels

    final_label_values = {
        str(state): sorted(labels)
        for state, labels in current.items()
    }
    if output_parity and any((label & 1) != state
                             for state, labels in current.items()
                             for label in labels):
        raise AssertionError("final state parity does not encode the logo")
    label_to_terminal_state = {
        label: state for state, labels in current.items() for label in labels
    }

    # Replay every one of the 2^12 coordinate assignments through the six
    # loaded-prefix transitions and six controlled permutations.  This checks
    # the complete semantic embedding, rather than only checking each active
    # partial mapping locally.
    initial_labels = {}
    prefix_state = {}
    for prefix in range(1 << 6):
        state = 0
        for layer in range(6):
            state = transitions[layer][state][(prefix >> layer) & 1]
        initial_labels[prefix] = prefix
        prefix_state[prefix] = state
    for assignment in range(1 << 12):
        prefix = sum(((assignment >> bit) & 1) << offset
                     for offset, bit in enumerate(order[:6]))
        state_id = prefix_state[prefix]
        label = initial_labels[prefix]
        for layer_index, layer in enumerate(layers):
            control = (assignment >> order[6 + layer_index]) & 1
            label = layer["permutations"][control][label]
        expected = 0
        for bit_offset, bit in enumerate(order[6:]):
            expected = transitions[6 + bit_offset][state_id][
                (assignment >> bit) & 1
            ]
            state_id = expected
        if output_parity:
            if (label & 1) != expected:
                raise AssertionError("replayed state label does not encode the target")
        elif label_to_terminal_state.get(label) != expected:
            raise AssertionError("replayed state label has the wrong terminal residual")
    return {
        "status": "exact semantic embedding; native QASM pending",
        "variable_order": list(order),
        "loaded_prefix_bits": list(order[:6]),
        "remaining_control_bits": list(order[6:]),
        "state_width": state_bits,
        "state_capacity": capacity,
        "layers": layers,
        "final_state_label_values": final_label_values,
        "output_parity_encoding": output_parity,
        "total_controlled_permutation_adjacent_transpositions": total_adjacent,
        "total_gray_path_mct_cost": total_hamming_cost,
        "marked_states": program["marked_states"],
        "source_slot_peak": program["maximum_reversible_slots"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--order", nargs=12, type=int, default=list(ORDER))
    parser.add_argument("--state-bits", type=int, default=DEFAULT_STATE_BITS)
    parser.add_argument("--no-output-parity", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if sorted(args.order) != list(range(12)):
        raise SystemExit("--order must be a permutation of 0..11")
    result = build_model(tuple(args.order), state_bits=args.state_bits,
                         output_parity=not args.no_output_parity)
    compact = {key: value for key, value in result.items() if key != "layers"}
    compact["layers"] = [
        {
            "residual_layer": layer["residual_layer"],
            "state_count": layer["state_count"],
            "next_state_count": layer["next_state_count"],
            "permutation_stats": layer["permutation_stats"],
        }
        for layer in result["layers"]
    ]
    print(json.dumps(compact, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
