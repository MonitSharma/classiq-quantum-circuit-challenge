"""Semantic search for a destructive reversible logo classifier.

The search state stores the Boolean function currently carried by every
physical wire over all 4096 coordinate inputs.  RCCX is treated as a
relative-phase monomial update during search; the exact inverse is responsible
for cancelling its phase in the eventual C-dagger-Z-C oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import random
import time
from dataclasses import dataclass, replace
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import logo


N_INPUTS = 4096
N_WIRES = 18
ALL_ONES = (1 << N_INPUTS) - 1
TARGET_WIRE = 12
# Calibrated with Qiskit 2.5.2, basis_gates=["u3", "cx"],
# qubits_initially_zero=False, optimization_level=3: one RCCX is depth 7,
# three CXs; two wire-disjoint RCCXs remain depth 7.
RCCX_ESTIMATED_DEPTH = 7
BIAFFINE_RCCX_ESTIMATED_DEPTH = 9
PROXY_ORDER = 2
FULL_PROXY_SHORTLIST_MULTIPLIER = 32


def input_truth_tables() -> tuple[int, ...]:
    return tuple(
        sum(1 << index for index in range(N_INPUTS) if (index >> bit) & 1)
        for bit in range(12)
    )


def logo_truth_table() -> int:
    return sum(
        1 << (y * 64 + x)
        for y in range(64)
        for x in range(64)
        if logo(x, y)
    )


TARGET = logo_truth_table()


def initial_wire_truth_tables() -> tuple[int, ...]:
    return input_truth_tables() + (0,) * 6


def apply_x_semantic(wires: tuple[int, ...], target: int) -> tuple[int, ...]:
    out = list(wires)
    out[target] ^= ALL_ONES
    return tuple(out)


def apply_cx_semantic(wires: tuple[int, ...], control: int, target: int) -> tuple[int, ...]:
    if control == target:
        raise ValueError("CX control and target must differ")
    out = list(wires)
    out[target] ^= out[control]
    return tuple(out)


def apply_rccx_semantic(
    wires: tuple[int, ...], control_a: int, control_b: int, target: int
) -> tuple[int, ...]:
    if len({control_a, control_b, target}) != 3:
        raise ValueError("RCCX wires must be distinct")
    out = list(wires)
    out[target] ^= out[control_a] & out[control_b]
    return tuple(out)


def apply_biaffine_semantic(
    wires: tuple[int, ...], a: int, mix_a: int, b: int, mix_b: int,
    target: int,
) -> tuple[int, ...]:
    if len({a, mix_a, b, mix_b, target}) != 5:
        raise ValueError("biaffine RCCX wires must be distinct")
    out = list(wires)
    out[target] ^= (wires[a] ^ wires[mix_a]) & (
        wires[b] ^ wires[mix_b]
    )
    return tuple(out)


def affine_span_solution(wires: tuple[int, ...], target: int = TARGET):
    """Return target = constant XOR selected wires, or None.

    The elimination coefficient bit i denotes wire i; bit N_WIRES denotes the
    all-ones constant.  A highest-set-bit pivot representation keeps the
    operation linear over GF(2) while each signal is a 4096-bit Python int.
    """
    basis: dict[int, tuple[int, int]] = {}

    def insert(value: int, coeff: int) -> None:
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                old_value, old_coeff = basis[pivot]
                value ^= old_value
                coeff ^= old_coeff
            else:
                basis[pivot] = (value, coeff)
                return

    insert(ALL_ONES, 1 << N_WIRES)
    for index, value in enumerate(wires):
        if value:
            insert(value, 1 << index)

    value, coeff = target, 0
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            return None
        old_value, old_coeff = basis[pivot]
        value ^= old_value
        coeff ^= old_coeff

    return {
        "constant": int(bool(coeff & (1 << N_WIRES))),
        "wires": [i for i in range(N_WIRES) if coeff & (1 << i)],
    }


def affine_distance_proxy(wires: tuple[int, ...], target: int = TARGET,
                          max_order: int = 2):
    """Cheap residual distance using constants and small wire combinations."""
    best = target.bit_count()
    best_combo: tuple[int, ...] = ()
    values = [(0, 0), (ALL_ONES, -1)]
    values.extend((value, index) for index, value in enumerate(wires))
    for value, index in values:
        distance = (target ^ value).bit_count()
        if distance < best:
            best, best_combo = distance, (() if index == -1 else (index,))
    for i in range(N_WIRES):
        for j in range(i + 1, N_WIRES):
            distance = (target ^ wires[i] ^ wires[j]).bit_count()
            if distance < best:
                best, best_combo = distance, (i, j)
            distance = (target ^ ALL_ONES ^ wires[i] ^ wires[j]).bit_count()
            if distance < best:
                best, best_combo = distance, (-1, i, j)
    if max_order >= 3:
        for i in range(N_WIRES):
            for j in range(i + 1, N_WIRES):
                ij = wires[i] ^ wires[j]
                for k in range(j + 1, N_WIRES):
                    distance = (target ^ ij ^ wires[k]).bit_count()
                    if distance < best:
                        best, best_combo = distance, (i, j, k)
                    distance = (target ^ ALL_ONES ^ ij ^ wires[k]).bit_count()
                    if distance < best:
                        best, best_combo = distance, (-1, i, j, k)
    return best, best_combo


def exact_affine_distance(wires: tuple[int, ...], target: int = TARGET):
    """Exact minimum Hamming residual over the 18-wire affine span.

    The two nine-wire halves give 512 combinations each. The constant is
    checked as a final toggle, so the search performs 262,144 4096-bit
    popcounts without enumerating a 2^18 Python list.
    """
    combinations: list[list[tuple[int, int]]] = []
    for offset in (0, 9):
        half: list[tuple[int, int]] = []
        for mask in range(1 << 9):
            value = 0
            for bit in range(9):
                if mask & (1 << bit):
                    value ^= wires[offset + bit]
            half.append((value, mask))
        combinations.append(half)
    best = target.bit_count()
    best_combo: tuple[int, ...] = ()
    for left, left_mask in combinations[0]:
        for right, right_mask in combinations[1]:
            base = target ^ left ^ right
            distance = base.bit_count()
            if distance < best:
                best = distance
                best_combo = tuple(i for i in range(9) if left_mask & (1 << i))
                best_combo += tuple(i + 9 for i in range(9)
                                    if right_mask & (1 << i))
            distance = (base ^ ALL_ONES).bit_count()
            if distance < best:
                best = distance
                best_combo = (-1,)
                best_combo += tuple(i for i in range(9) if left_mask & (1 << i))
                best_combo += tuple(i + 9 for i in range(9)
                                    if right_mask & (1 << i))
    return best, best_combo


def semantic_hash(wires: tuple[int, ...]) -> str:
    h = hashlib.blake2b(digest_size=16)
    for value in wires:
        h.update(value.to_bytes((N_INPUTS + 7) // 8, "little"))
    return h.hexdigest()


@dataclass
class State:
    wires: tuple[int, ...]
    arrivals: tuple[int, ...]
    gates: tuple[tuple[str, int, int, int], ...]
    estimated_depth: int
    residual: int
    combo: tuple[int, ...]


def initial_state() -> State:
    wires = initial_wire_truth_tables()
    residual, combo = affine_distance_proxy(wires, max_order=PROXY_ORDER)
    return State(wires, (0,) * N_WIRES, (), 0, residual, combo)


def apply_rccx_state(state: State, a: int, b: int, target: int) -> State | None:
    wires = apply_rccx_semantic(state.wires, a, b, target)
    if wires == state.wires:
        return None
    start = max(state.arrivals[a], state.arrivals[b], state.arrivals[target])
    end = start + RCCX_ESTIMATED_DEPTH
    arrivals = list(state.arrivals)
    arrivals[a] = arrivals[b] = arrivals[target] = end
    residual, combo = affine_distance_proxy(wires, max_order=PROXY_ORDER)
    return State(
        wires,
        tuple(arrivals),
        state.gates + (("rccx", a, b, target),),
        max(state.estimated_depth, end),
        residual,
        combo,
    )


def apply_rccx_layer_state(
    state: State, gates: tuple[tuple[int, int, int], ...]
) -> State | None:
    """Apply wire-disjoint RCCXs as one conceptual native-depth layer."""
    touched: set[int] = set()
    for a, b, target in gates:
        if touched.intersection((a, b, target)):
            raise ValueError("RCCX layer is not wire-disjoint")
        touched.update((a, b, target))
    child = state
    for a, b, target in gates:
        child = apply_rccx_state(child, a, b, target)
        if child is None:
            return None
    return child


def apply_double_rccx_state(
    state: State, first: tuple[int, int, int],
    second: tuple[int, int, int],
) -> State | None:
    """Apply two serial RCCXs as one lookahead search move."""
    child = apply_rccx_state(state, *first)
    if child is None:
        return None
    return apply_rccx_state(child, *second)


def apply_affine_rccx_state(
    state: State, a: int, mix: int, b: int, target: int
) -> State | None:
    """Apply CX(mix,a), RCCX(a,b,target), CX(mix,a).

    Semantically this toggles the target by `(W[a] XOR W[mix]) AND W[b]`
    while restoring wire `a`. The complete sandwich is reversible and can use
    an original coordinate wire as any role.
    """
    if len({a, mix, b, target}) != 4:
        raise ValueError("affine RCCX wires must be distinct")
    term = (state.wires[a] ^ state.wires[mix]) & state.wires[b]
    if not term:
        return None
    wires = list(state.wires)
    wires[target] ^= term
    arrivals = list(state.arrivals)
    pre_end = max(arrivals[mix], arrivals[a]) + 1
    arrivals[a] = pre_end
    rccx_end = max(arrivals[a], arrivals[b], arrivals[target]) + RCCX_ESTIMATED_DEPTH
    arrivals[a] = rccx_end + 1
    arrivals[target] = rccx_end
    residual, combo = affine_distance_proxy(tuple(wires), max_order=PROXY_ORDER)
    gates = state.gates + (
        ("cx", mix, a, -1),
        ("rccx", a, b, target),
        ("cx", mix, a, -1),
    )
    return State(tuple(wires), tuple(arrivals), gates,
                 max(state.estimated_depth, rccx_end + 1), residual, combo)


def apply_biaffine_rccx_state(
    state: State, a: int, mix_a: int, b: int, mix_b: int, target: int
) -> State | None:
    """Apply two temporary affine-control changes around one RCCX.

    The reversible block temporarily maps each control to an XOR with a
    second live wire, applies RCCX, and restores both controls. Its net
    semantic update is
    ``W[target] ^= (W[a] XOR W[mix_a]) AND (W[b] XOR W[mix_b])``.
    """
    if len({a, mix_a, b, mix_b, target}) != 5:
        raise ValueError("biaffine RCCX wires must be distinct")
    wires = apply_biaffine_semantic(
        state.wires, a, mix_a, b, mix_b, target
    )
    term = state.wires[target] ^ wires[target]
    if not term:
        return None
    arrivals = list(state.arrivals)
    start = max(arrivals[a], arrivals[mix_a], arrivals[b],
                arrivals[mix_b], arrivals[target])
    end = start + BIAFFINE_RCCX_ESTIMATED_DEPTH
    for wire in (a, mix_a, b, mix_b, target):
        arrivals[wire] = end
    residual, combo = affine_distance_proxy(wires, max_order=PROXY_ORDER)
    gates = state.gates + (
        ("biaffine", a, mix_a, b, mix_b, target),
    )
    return State(wires, tuple(arrivals), gates,
                 max(state.estimated_depth, end), residual, combo)


def complete_affine(state: State, target_wire: int = TARGET_WIRE) -> State | None:
    solution = affine_span_solution(state.wires)
    if solution is None:
        return None
    wires = state.wires
    arrivals = list(state.arrivals)
    gates = list(state.gates)
    depth = state.estimated_depth
    if solution["constant"]:
        wires = apply_x_semantic(wires, target_wire)
        start = arrivals[target_wire]
        depth = max(depth, start + 1)
        arrivals[target_wire] = start + 1
        gates.append(("x", target_wire, -1, -1))
    for source in solution["wires"]:
        if source == target_wire:
            continue
        wires = apply_cx_semantic(wires, source, target_wire)
        start = max(arrivals[source], arrivals[target_wire])
        depth = max(depth, start + 1)
        arrivals[target_wire] = start + 1
        gates.append(("cx", source, target_wire, -1))
    if wires[target_wire] != TARGET:
        raise AssertionError("affine completion failed")
    return State(tuple(wires), tuple(arrivals), tuple(gates), depth, 0, ())


def build_circuit(gates: tuple[tuple, ...]) -> QuantumCircuit:
    q = QuantumCircuit(N_WIRES)
    for gate in gates:
        kind = gate[0]
        if kind == "biaffine":
            _, a, mix_a, b, mix_b, target = gate
            q.cx(mix_a, a)
            q.cx(mix_b, b)
            q.rccx(a, b, target)
            q.cx(mix_b, b)
            q.cx(mix_a, a)
            continue
        _, a, b, target = gate
        if kind == "x":
            q.x(a)
        elif kind == "cx":
            q.cx(a, b)
        elif kind == "rccx":
            q.rccx(a, b, target)
        else:
            raise ValueError(kind)
    return q


def score_state(state: State) -> tuple[int, int, int, str]:
    exact = 0 if affine_span_solution(state.wires) is not None else 1
    return exact, state.residual, state.estimated_depth, semantic_hash(state.wires)


def pareto_select(states: list[State], limit: int) -> list[State]:
    """Keep residual/depth non-dominated states, then fill by normal score."""
    if len(states) <= limit:
        return sorted(states, key=score_state)
    ordered = sorted(states, key=score_state)
    pareto: list[State] = []
    for state in ordered:
        dominated = any(
            other.residual <= state.residual
            and other.estimated_depth <= state.estimated_depth
            and (other.residual < state.residual
                 or other.estimated_depth < state.estimated_depth)
            for other in pareto
        )
        if not dominated:
            pareto.append(state)
    if len(pareto) >= limit:
        return sorted(pareto, key=score_state)[:limit]
    selected = {semantic_hash(state.wires) for state in pareto}
    for state in ordered:
        if len(pareto) >= limit:
            break
        if semantic_hash(state.wires) not in selected:
            pareto.append(state)
            selected.add(semantic_hash(state.wires))
    return sorted(pareto, key=score_state)


def proposal_gates(
    state: State,
    preserve_inputs: bool,
    limit: int,
    rng: random.Random,
    evaluate_proxy: bool = False,
):
    proposals = []
    for a in range(N_WIRES):
        for b in range(a + 1, N_WIRES):
            term = state.wires[a] & state.wires[b]
            if not term:
                continue
            for target in range(N_WIRES):
                if target in (a, b) or (preserve_inputs and target < 12):
                    continue
                new_value = state.wires[target] ^ term
                if new_value == state.wires[target]:
                    continue
                direct = (TARGET ^ new_value).bit_count()
                pair_hint = min(
                    (TARGET ^ new_value ^ state.wires[i]).bit_count()
                    for i in range(N_WIRES) if i != target
                )
                proposals.append((min(direct, pair_hint), rng.random(),
                                  a, b, target, new_value))
    proposals.sort()
    if evaluate_proxy:
        # Full order-3 scoring is useful but expensive. Keep the cheap
        # direct/pair shortlist bounded before evaluating all triples.
        shortlist = proposals[:max(limit * FULL_PROXY_SHORTLIST_MULTIPLIER, 256)]
        rescored = []
        for _, tie, a, b, target, new_value in shortlist:
            candidate_wires = list(state.wires)
            candidate_wires[target] = new_value
            heuristic, _ = affine_distance_proxy(
                tuple(candidate_wires), max_order=PROXY_ORDER
            )
            rescored.append((heuristic, tie, a, b, target))
        rescored.sort()
        return [(a, b, target)
                for _, _, a, b, target in rescored[:limit]]
    return [(a, b, target) for _, _, a, b, target, _ in proposals[:limit]]


def proposal_layers(
    state: State, preserve_inputs: bool, limit: int, max_parallel: int,
    rng: random.Random, evaluate_proxy: bool = False,
) -> list[tuple[tuple[int, int, int], ...]]:
    singles = proposal_gates(
        state, preserve_inputs, max(limit * 2, 32), rng, evaluate_proxy
    )
    layers: list[tuple[tuple[int, int, int], ...]] = []
    seen: set[tuple[tuple[int, int, int], ...]] = set()
    for index, primary in enumerate(singles):
        candidate = [primary]
        used = set(primary)
        for extra in singles[index + 1:]:
            if used.isdisjoint(extra):
                candidate.append(extra)
                used.update(extra)
                if len(candidate) >= max_parallel:
                    break
        for width in range(1, len(candidate) + 1):
            layer = tuple(candidate[:width])
            if layer not in seen:
                seen.add(layer)
                layers.append(layer)
    rng.shuffle(layers)
    layers.sort(key=lambda layer: (-len(layer), layer))
    return layers[:limit]


def proposal_affine_operations(
    state: State, preserve_inputs: bool, limit: int, rng: random.Random
):
    """Rank affine-control RCCX sandwiches using the cheap residual proxy."""
    base = proposal_gates(state, preserve_inputs, max(limit, 32), rng)
    proposals = []
    for a, b, target in base:
        for mix in range(N_WIRES):
            if mix in (a, b, target):
                continue
            term = (state.wires[a] ^ state.wires[mix]) & state.wires[b]
            if not term:
                continue
            new_value = state.wires[target] ^ term
            direct = (TARGET ^ new_value).bit_count()
            pair_hint = min(
                (TARGET ^ new_value ^ state.wires[i]).bit_count()
                for i in range(N_WIRES) if i != target
            )
            proposals.append((min(direct, pair_hint), rng.random(),
                              a, mix, b, target))
    proposals.sort()
    return [(a, mix, b, target)
            for _, _, a, mix, b, target in proposals[:limit]]


def proposal_biaffine_operations(
    state: State, preserve_inputs: bool, limit: int, rng: random.Random
):
    """Rank two-sided affine-control RCCX proposals by the proxy."""
    base = proposal_gates(state, preserve_inputs, max(limit, 32), rng)
    proposals = []
    for a, b, target in base:
        for mix_a in range(N_WIRES):
            if mix_a in (a, b, target):
                continue
            for mix_b in range(N_WIRES):
                if mix_b in (a, mix_a, b, target):
                    continue
                term = (state.wires[a] ^ state.wires[mix_a]) & (
                    state.wires[b] ^ state.wires[mix_b]
                )
                if not term:
                    continue
                candidate_wires = list(state.wires)
                candidate_wires[target] ^= term
                heuristic, _ = affine_distance_proxy(
                    tuple(candidate_wires), max_order=PROXY_ORDER
                )
                proposals.append((heuristic, rng.random(), a, mix_a, b,
                                  mix_b, target))
    proposals.sort()
    return [(a, mix_a, b, mix_b, target)
            for _, _, a, mix_a, b, mix_b, target in proposals[:limit]]


def proposal_double_operations(
    state: State, preserve_inputs: bool, limit: int, rng: random.Random
):
    """Find short synergistic RCCX pairs using a bounded two-step lookahead."""
    firsts = proposal_gates(
        state, preserve_inputs, max(limit * 8, 32), rng, False
    )
    proposals = []
    for first in firsts:
        intermediate = apply_rccx_state(state, *first)
        if intermediate is None:
            continue
        seconds = proposal_gates(
            intermediate, preserve_inputs, max(limit * 8, 32), rng, False
        )
        for second in seconds:
            child = apply_rccx_state(intermediate, *second)
            if child is None:
                continue
            heuristic, _ = affine_distance_proxy(
                child.wires, max_order=PROXY_ORDER
            )
            proposals.append((heuristic, rng.random(), first, second))
    proposals.sort()
    return [(first, second)
            for _, _, first, second in proposals[:limit]]


def refine_exact_leaders(states: list[State], count: int) -> list[State]:
    """Replace the proxy residual on the leading states with exact distance."""
    if count <= 0:
        return states
    ordered = sorted(states, key=score_state)
    leaders = {semantic_hash(state.wires): state for state in ordered[:count]}
    refined = []
    for state in states:
        replacement = leaders.get(semantic_hash(state.wires))
        if replacement is None:
            refined.append(state)
            continue
        distance, combo = exact_affine_distance(state.wires)
        refined.append(replace(state, residual=distance, combo=combo))
    return refined


def search(beam_width: int, layers: int, seed: int, preserve_inputs: bool,
           checkpoint_dir: Path | None = None, proposal_limit: int = 128,
           max_parallel: int = 1, exact_top: int = 0,
           affine_controls: bool = False, full_proxy_proposals: bool = False,
           resume: Path | None = None, biaffine_controls: bool = False,
           double_rccx: bool = False, pareto_beam: bool = False):
    rng = random.Random(seed)
    start_layer = 0
    if resume is None:
        beam = [initial_state()]
        best = beam[0]
    else:
        with resume.open("rb") as handle:
            saved = pickle.load(handle)
        if not isinstance(saved, dict) or "beam" not in saved or "best" not in saved:
            raise ValueError("resume checkpoint must contain beam and best")
        beam = saved["beam"]
        best = saved["best"]
        start_layer = int(saved.get("layer", 0))
        if not beam:
            raise ValueError("resume checkpoint contains an empty beam")
        if start_layer >= layers:
            raise ValueError("resume checkpoint is already at or beyond --layers")
    for layer in range(start_layer + 1, layers + 1):
        children: dict[str, State] = {}
        for state in beam:
            if (affine_controls or biaffine_controls) and max_parallel == 1:
                operations = []
                if affine_controls:
                    operations.extend(
                        ("affine", op) for op in proposal_affine_operations(
                            state, preserve_inputs, proposal_limit, rng)
                    )
                if biaffine_controls:
                    operations.extend(
                        ("biaffine", op) for op in proposal_biaffine_operations(
                            state, preserve_inputs, proposal_limit, rng)
                    )
                operations.extend(("plain", op) for op in proposal_gates(
                    state, preserve_inputs, proposal_limit, rng,
                    full_proxy_proposals))
                for kind, operation in operations:
                    if kind == "affine":
                        child = apply_affine_rccx_state(state, *operation)
                    elif kind == "biaffine":
                        child = apply_biaffine_rccx_state(state, *operation)
                    else:
                        child = apply_rccx_state(state, *operation)
                    if child is None:
                        continue
                    key = semantic_hash(child.wires)
                    old = children.get(key)
                    if old is None or score_state(child) < score_state(old):
                        children[key] = child
            elif double_rccx and max_parallel == 1:
                operations = proposal_double_operations(
                    state, preserve_inputs, proposal_limit, rng
                )
                for first, second in operations:
                    child = apply_double_rccx_state(state, first, second)
                    if child is None:
                        continue
                    key = semantic_hash(child.wires)
                    old = children.get(key)
                    if old is None or score_state(child) < score_state(old):
                        children[key] = child
            else:
                layer_candidates = proposal_layers(
                    state, preserve_inputs, proposal_limit, max_parallel, rng,
                    full_proxy_proposals)
                for layer_gates in layer_candidates:
                    child = apply_rccx_layer_state(state, layer_gates)
                    if child is None:
                        continue
                    key = semantic_hash(child.wires)
                    old = children.get(key)
                    if old is None or score_state(child) < score_state(old):
                        children[key] = child
            if len(children) > beam_width * 32:
                if pareto_beam:
                    kept = pareto_select(list(children.values()), beam_width * 16)
                else:
                    kept = sorted(children.values(), key=score_state)[:beam_width * 16]
                children = {semantic_hash(item.wires): item for item in kept}
        candidates = refine_exact_leaders(list(children.values()), exact_top)
        beam = (pareto_select(candidates, beam_width) if pareto_beam
                else sorted(candidates, key=score_state)[:beam_width])
        if not beam:
            break
        if score_state(beam[0]) < score_state(best):
            best = beam[0]
        completed = next((complete_affine(s) for s in beam
                          if affine_span_solution(s.wires) is not None), None)
        print(json.dumps({
            "layer": layer,
            "beam": len(beam),
            "best_residual": beam[0].residual,
            "best_depth_estimate": beam[0].estimated_depth,
            "best_exact_span": affine_span_solution(beam[0].wires) is not None,
        }), flush=True)
        if checkpoint_dir is not None:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            with (checkpoint_dir / f"layer_{layer:03d}.pkl").open("wb") as handle:
                pickle.dump({"layer": layer, "beam": beam, "best": best}, handle,
                            protocol=pickle.HIGHEST_PROTOCOL)
        if completed is not None:
            return completed, layer
    return best, layers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beam", type=int, default=64)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=524)
    parser.add_argument("--preserve-inputs", action="store_true")
    parser.add_argument("--proposal-limit", type=int, default=128)
    parser.add_argument("--max-parallel", type=int, default=1)
    parser.add_argument("--exact-top", type=int, default=0)
    parser.add_argument("--affine-controls", action="store_true")
    parser.add_argument(
        "--full-proxy-proposals",
        action="store_true",
        help="rank plain RCCX mutations by the complete configured proxy",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        help="resume from a layer checkpoint produced by this search",
    )
    parser.add_argument(
        "--biaffine-controls",
        action="store_true",
        help="allow two-sided temporary affine-control RCCX blocks",
    )
    parser.add_argument(
        "--double-rccx",
        action="store_true",
        help="use bounded two-RCCX lookahead moves",
    )
    parser.add_argument(
        "--pareto-beam",
        action="store_true",
        help="retain residual/depth non-dominated beam states",
    )
    parser.add_argument("--proxy-order", type=int, choices=[2, 3], default=2)
    parser.add_argument("--out", default="artifacts/destructive_semantic")
    args = parser.parse_args()

    global PROXY_ORDER
    PROXY_ORDER = args.proxy_order

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(exist_ok=True)
    if TARGET.bit_count() != 1097:
        raise AssertionError(TARGET.bit_count())
    started = time.time()
    result, completed_layer = search(
        args.beam, args.layers, args.seed, args.preserve_inputs,
        out / "checkpoints", args.proposal_limit, args.max_parallel,
        args.exact_top, args.affine_controls, args.full_proxy_proposals,
        args.resume, args.biaffine_controls, args.double_rccx,
        args.pareto_beam)
    payload = {
        "seed": args.seed,
        "beam_width": args.beam,
        "layers": args.layers,
        "preserve_inputs": args.preserve_inputs,
        "proposal_limit": args.proposal_limit,
        "max_parallel": args.max_parallel,
        "exact_top": args.exact_top,
        "affine_controls": args.affine_controls,
        "full_proxy_proposals": args.full_proxy_proposals,
        "resume": str(args.resume) if args.resume else None,
        "biaffine_controls": args.biaffine_controls,
        "double_rccx": args.double_rccx,
        "pareto_beam": args.pareto_beam,
        "proxy_order": args.proxy_order,
        "completed_layer": completed_layer,
        "target_marked_states": TARGET.bit_count(),
        "estimated_depth": result.estimated_depth,
        "residual": result.residual,
        "exact_affine_distance": exact_affine_distance(result.wires)[0],
        "exact_affine_combo": exact_affine_distance(result.wires)[1],
        "affine_solution": affine_span_solution(result.wires),
        "gates": result.gates,
        "elapsed_seconds": time.time() - started,
        "semantic_hash": semantic_hash(result.wires),
    }
    (out / "latest_result.json").write_text(json.dumps(payload, indent=2) + "\n")
    with (out / "checkpoints" / f"beam_{args.beam}_layers_{args.layers}.pkl").open("wb") as handle:
        pickle.dump({"args": vars(args), "state": result}, handle)
    if affine_span_solution(result.wires) is not None:
        classifier = build_circuit(result.gates)
        compiled = transpile(classifier, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3)
        qasm_path = out / "destructive_classifier_candidate.qasm"
        qasm_path.write_text(qasm2.dumps(compiled))
        payload["compiled_forward_depth"] = compiled.depth()
        payload["compiled_forward_cx"] = compiled.count_ops().get("cx", 0)
        (out / "latest_result.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
