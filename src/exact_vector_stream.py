"""Exact two-live-pair vector streaming control experiment."""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from exact_stream import append_exact_mcx, toggle_truth


ROOT = Path(__file__).resolve().parents[1]
TERMS = ("pair_terms", "rank_terms", "rank_mc_pareto_terms")


def raw_vector_transition(old_state, new_state):
    """Toggle two x and two y live outputs using q16/q17 as clean scratch."""
    circuit = QuantumCircuit(18)
    for slot in range(2):
        toggle_truth(circuit, old_state[slot][0], new_state[slot][0],
                     0, 12 + slot, [16, 17])
        toggle_truth(circuit, old_state[slot][1], new_state[slot][1],
                     6, 14 + slot, [16, 17])
    return circuit


def compile_transition(old_state, new_state, seed=0):
    raw = raw_vector_transition(old_state, new_state)
    return transpile(raw, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def edge_score(edges, left, right):
    if left == right:
        return (0, 0)
    return edges[(min(left, right), max(left, right))]["depth"], edges[
        (min(left, right), max(left, right))]["cx"]


def held_karp(edges, count):
    dp = {}
    parent = {}
    for last in range(1, count + 1):
        dp[(1 << (last - 1), last)] = edge_score(edges, 0, last)
    for size in range(2, count + 1):
        for mask in range(1 << count):
            if mask.bit_count() != size:
                continue
            for last in range(1, count + 1):
                last_bit = 1 << (last - 1)
                if not mask & last_bit:
                    continue
                previous = mask ^ last_bit
                best = None
                for prior in range(1, count + 1):
                    if not previous & (1 << (prior - 1)):
                        continue
                    old = dp[(previous, prior)]
                    edge = edge_score(edges, prior, last)
                    candidate = (old[0] + edge[0], old[1] + edge[1])
                    if best is None or candidate < best[0]:
                        best = (candidate, prior)
                        parent[(mask, last)] = prior
                if best is not None:
                    dp[(mask, last)] = best[0]
    full = (1 << count) - 1
    best = None
    last_best = None
    for last in range(1, count + 1):
        candidate = tuple(a + b for a, b in zip(
            dp[(full, last)], edge_score(edges, last, 0)))
        if best is None or candidate < best:
            best, last_best = candidate, last
    order = []
    mask, last = full, last_best
    while True:
        order.append(last - 1)
        if mask == 1 << (last - 1):
            break
        prior = parent[(mask, last)]
        mask ^= 1 << (last - 1)
        last = prior
    return list(reversed(order)), best


def compile_basis(terms, basis, seed=0):
    groups = [tuple(terms[i:i + 2]) for i in range(0, len(terms), 2)]
    states = [tuple((0, 0) for _ in range(2))]
    states.extend(groups)
    edges = {}
    for left in range(len(states)):
        for right in range(left + 1, len(states)):
            compiled = compile_transition(states[left], states[right], seed)
            edges[(left, right)] = {
                "depth": compiled.depth(),
                "cx": compiled.count_ops().get("cx", 0),
                "qasm": qasm2.dumps(compiled),
            }
            print("edge", basis, left, right,
                  (edges[(left, right)]["depth"], edges[(left, right)]["cx"]),
                  flush=True)
    order, path_score = held_karp(edges, len(groups))
    raw = QuantumCircuit(18)
    current = states[0]
    for node in order:
        next_state = states[node + 1]
        raw.compose(raw_vector_transition(current, next_state), inplace=True)
        raw.cz(12, 14)
        raw.cz(13, 15)
        current = next_state
    raw.compose(raw_vector_transition(current, states[0]), inplace=True)
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3,
                         seed_transpiler=seed)
    result = {"basis": basis, "groups": [[list(pair) for pair in group]
                                           for group in groups],
              "order": order,
              "edge_path_score": {"depth": path_score[0], "cx": path_score[1]},
              "depth": compiled.depth(), "cx": compiled.count_ops().get("cx", 0),
              "width": compiled.num_qubits}
    return compiled, result, edges, states


def main():
    for basis in TERMS:
        terms = [tuple(pair) for pair in
                 json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())]
        circuit, result, edges, states = compile_basis(terms, basis)
        name = f"exact_vector_stream_{basis}_development"
        qasm_path = ROOT / "artifacts" / f"{name}.qasm"
        qasm_path.write_text(qasm2.dumps(circuit))
        result["qasm"] = str(qasm_path)
        (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        serialized_edges = {f"{a},{b}": value for (a, b), value in edges.items()}
        (ROOT / "artifacts" / f"{name}_edges.json").write_text(
            json.dumps({"states": states, "edges": serialized_edges}, indent=2)
        )
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
