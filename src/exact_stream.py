"""Exact one-live-pair factor streaming for the rank decompositions.

Each transition toggles the live x/y factor by the XOR delta between adjacent
truth tables.  The transition uses clean scratch wires on its own side and
exact-control MCX synthesis, so the live factor can be discarded only by one
final transition back to zero.  This module deliberately contains no
relative-phase transition; that is a separate follow-up if this exact
baseline is competitive.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis import synth_mcx_1_clean_kg24, synth_mcx_2_clean_kg24

from search import esop


ROOT = Path(__file__).resolve().parents[1]
TERMS = ("pair_terms", "rank_terms", "rank_mc_pareto_terms")


def append_exact_mcx(circuit: QuantumCircuit, controls: list[int], target: int,
                    scratch: list[int]) -> None:
    """Append an exact MCX with the explicitly clean scratch supplied."""
    count = len(controls)
    if count == 0:
        circuit.x(target)
    elif count == 1:
        circuit.cx(controls[0], target)
    elif count == 2:
        circuit.ccx(*controls, target)
    elif count == 3:
        if not scratch:
            raise ValueError("three-control transition needs one clean scratch")
        sub = synth_mcx_1_clean_kg24(count)
        circuit.compose(sub, qubits=controls + [target] + scratch[:1],
                        inplace=True)
    elif count <= 6:
        if len(scratch) < 2:
            raise ValueError(f"{count}-control transition needs two clean scratch")
        sub = synth_mcx_2_clean_kg24(count)
        circuit.compose(sub, qubits=controls + [target] + scratch[:2],
                        inplace=True)
    else:
        raise ValueError(f"unsupported transition control count {count}")


def toggle_truth(circuit: QuantumCircuit, old: int, new: int, offset: int,
                 target: int, scratch: list[int]) -> None:
    """Toggle target by ``old XOR new`` using an exact ESOP implementation."""
    delta = old ^ new
    for mask, value in esop(delta, 6):
        controls = [offset + bit for bit in range(6) if mask >> bit & 1]
        negative = [offset + bit for bit in range(6)
                    if mask >> bit & 1 and not (value >> bit & 1)]
        if negative:
            circuit.x(negative)
        append_exact_mcx(circuit, controls, target, scratch)
        if negative:
            circuit.x(negative)


def raw_transition(old_pair: tuple[int, int], new_pair: tuple[int, int]) -> QuantumCircuit:
    """Build an exact transition on q12/q13 with clean q14..q17 scratch."""
    circuit = QuantumCircuit(18)
    # x and y transitions use disjoint controls, targets, and scratch banks.
    toggle_truth(circuit, old_pair[0], new_pair[0], 0, 12, [14, 15])
    toggle_truth(circuit, old_pair[1], new_pair[1], 6, 13, [16, 17])
    return circuit


def compile_transition(old_pair: tuple[int, int], new_pair: tuple[int, int],
                       seed: int = 0) -> QuantumCircuit:
    raw = raw_transition(old_pair, new_pair)
    return transpile(raw, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def edge_matrix(terms: list[tuple[int, int]], seed: int = 0):
    """Compile every nontrivial directed edge from zero or a term state."""
    states = [(0, 0), *terms]
    edges = {}
    for left in range(len(states)):
        for right in range(left + 1, len(states)):
            compiled = compile_transition(states[left], states[right], seed)
            score = (compiled.depth(), compiled.count_ops().get("cx", 0))
            edges[(left, right)] = {"depth": score[0], "cx": score[1],
                                   "qasm": qasm2.dumps(compiled)}
            print("edge", left, right, score, flush=True)
    return states, edges


def edge_score(edges, left: int, right: int):
    if left == right:
        return (0, 0)
    key = (min(left, right), max(left, right))
    row = edges[key]
    return row["depth"], row["cx"]


def held_karp(edges, count: int):
    """Find the minimum-depth zero -> all terms -> zero path."""
    # Terms are nodes 1..count; node 0 is the zero state.
    dp = {}
    parent = {}
    for last in range(1, count + 1):
        d, c = edge_score(edges, 0, last)
        dp[(1 << (last - 1), last)] = (d, c)
    for size in range(2, count + 1):
        for mask in range(1 << count):
            if mask.bit_count() != size:
                continue
            for last in range(1, count + 1):
                bit = 1 << (last - 1)
                if not mask & bit:
                    continue
                previous = mask ^ bit
                best = None
                for prior in range(1, count + 1):
                    if not previous & (1 << (prior - 1)):
                        continue
                    prev_score = dp[(previous, prior)]
                    ed, ec = edge_score(edges, prior, last)
                    candidate = (prev_score[0] + ed, prev_score[1] + ec)
                    if best is None or candidate < best[0]:
                        best = (candidate, prior)
                        parent[(mask, last)] = prior
                if best is not None:
                    dp[(mask, last)] = best[0]
    full = (1 << count) - 1
    best = None
    last_best = None
    for last in range(1, count + 1):
        d, c = dp[(full, last)]
        ed, ec = edge_score(edges, last, 0)
        candidate = (d + ed, c + ec)
        if best is None or candidate < best:
            best, last_best = candidate, last
    order = []
    mask, last = full, last_best
    while True:
        order.append(last - 1)
        if mask == (1 << (last - 1)):
            break
        prior = parent[(mask, last)]
        mask ^= 1 << (last - 1)
        last = prior
    order.reverse()
    return order, best


def raw_stream(terms: list[tuple[int, int]], order: list[int]) -> QuantumCircuit:
    circuit = QuantumCircuit(18)
    current = (0, 0)
    for index in order:
        next_pair = terms[index]
        circuit.compose(raw_transition(current, next_pair), inplace=True)
        circuit.cz(12, 13)
        current = next_pair
    circuit.compose(raw_transition(current, (0, 0)), inplace=True)
    return circuit


def compile_stream(terms: list[tuple[int, int]], order: list[int], seed: int = 0):
    raw = raw_stream(terms, order)
    return transpile(raw, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def main() -> None:
    for basis in TERMS:
        terms = [tuple(pair) for pair in
                 json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())]
        print("BASIS", basis, flush=True)
        states, edges = edge_matrix(terms, seed=0)
        order, path_score = held_karp(edges, len(terms))
        result = {"basis": basis, "order": order,
                  "edge_path_score": {"depth": path_score[0],
                                       "cx": path_score[1]}}
        edge_path = ROOT / "artifacts" / f"exact_stream_{basis}_edges_development.json"
        serial_edges = {f"{left},{right}": value
                        for (left, right), value in edges.items()}
        edge_path.write_text(json.dumps({"states": states, "edges": serial_edges,
                                         "result": result}, indent=2))
        circuit = compile_stream(terms, order, seed=0)
        name = f"exact_stream_{basis}_development"
        qasm_path = ROOT / "artifacts" / f"{name}.qasm"
        qasm_path.write_text(qasm2.dumps(circuit))
        result.update({"depth": circuit.depth(),
                       "cx": circuit.count_ops().get("cx", 0),
                       "width": circuit.num_qubits, "qasm": str(qasm_path)})
        (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
