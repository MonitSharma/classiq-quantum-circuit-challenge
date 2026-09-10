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
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import logo


N_INPUTS = 4096
N_WIRES = 18
ALL_ONES = (1 << N_INPUTS) - 1
TARGET_WIRE = 12
RCCX_ESTIMATED_DEPTH = 4


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


def affine_distance_proxy(wires: tuple[int, ...], target: int = TARGET):
    """Cheap residual distance using constants, singles, and wire pairs."""
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
    residual, combo = affine_distance_proxy(wires)
    return State(wires, (0,) * N_WIRES, (), 0, residual, combo)


def apply_rccx_state(state: State, a: int, b: int, target: int) -> State | None:
    wires = apply_rccx_semantic(state.wires, a, b, target)
    if wires == state.wires:
        return None
    start = max(state.arrivals[a], state.arrivals[b], state.arrivals[target])
    end = start + RCCX_ESTIMATED_DEPTH
    arrivals = list(state.arrivals)
    arrivals[a] = arrivals[b] = arrivals[target] = end
    residual, combo = affine_distance_proxy(wires)
    return State(
        wires,
        tuple(arrivals),
        state.gates + (("rccx", a, b, target),),
        max(state.estimated_depth, end),
        residual,
        combo,
    )


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


def build_circuit(gates: tuple[tuple[str, int, int, int], ...]) -> QuantumCircuit:
    q = QuantumCircuit(N_WIRES)
    for kind, a, b, target in gates:
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


def proposal_gates(state: State, preserve_inputs: bool, limit: int, rng: random.Random):
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
                proposals.append((min(direct, pair_hint), rng.random(), a, b, target))
    proposals.sort()
    return [(a, b, target) for _, _, a, b, target in proposals[:limit]]


def search(beam_width: int, layers: int, seed: int, preserve_inputs: bool,
           checkpoint_dir: Path | None = None, proposal_limit: int = 128):
    rng = random.Random(seed)
    beam = [initial_state()]
    best = beam[0]
    for layer in range(1, layers + 1):
        children: dict[str, State] = {}
        for state in beam:
            for a, b, target in proposal_gates(
                    state, preserve_inputs, proposal_limit, rng):
                child = apply_rccx_state(state, a, b, target)
                if child is None:
                    continue
                key = semantic_hash(child.wires)
                old = children.get(key)
                if old is None or score_state(child) < score_state(old):
                    children[key] = child
        beam = sorted(children.values(), key=score_state)[:beam_width]
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
    parser.add_argument("--out", default="artifacts/destructive_semantic")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(exist_ok=True)
    if TARGET.bit_count() != 1097:
        raise AssertionError(TARGET.bit_count())
    started = time.time()
    result, completed_layer = search(
        args.beam, args.layers, args.seed, args.preserve_inputs,
        out / "checkpoints", args.proposal_limit)
    payload = {
        "seed": args.seed,
        "beam_width": args.beam,
        "layers": args.layers,
        "preserve_inputs": args.preserve_inputs,
        "proposal_limit": args.proposal_limit,
        "completed_layer": completed_layer,
        "target_marked_states": TARGET.bit_count(),
        "estimated_depth": result.estimated_depth,
        "residual": result.residual,
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
