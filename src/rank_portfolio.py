"""Benchmark and compose the existing exact rank-term compiler portfolio."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from pair_search import pair_circuit
from parallel_rank_pair_xag import parallel_pair, score_pair as score_parallel
from phase_pebble_rank import compile_pair as compile_phase_pebble
from phase_retention import execute_actions, make_pair_graph, phase_edges


ROOT = Path(__file__).resolve().parents[1]


def score(circuit):
    out = transpile(circuit, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    return out.depth(), out.count_ops().get("cx", 0)


def save_block(name, index, circuit, metadata):
    directory = ROOT / "artifacts" / "rank_portfolio_blocks"
    directory.mkdir(exist_ok=True)
    out = transpile(circuit, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    path = directory / f"term_{index}_{name}.qasm"
    path.write_text(qasm2.dumps(out))
    metadata.update({"qasm": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "depth": out.depth(), "cx": out.count_ops().get("cx", 0), "width": out.num_qubits})
    return out


def retention_block(index, terms, cache, schedules):
    x, y = terms[index]
    graph, xr, yr, _ = make_pair_graph(x, y, cache)
    edges, constant = phase_edges(xr, yr)
    actions = [tuple(action) for action in schedules[str(index)]["actions"]]
    return execute_actions(graph, sorted(edges), actions, constant)[0]


def build_portfolio():
    terms = json.loads((ROOT / "artifacts/rank_mc_pareto_terms.json").read_text())
    cache = json.loads((ROOT / "artifacts/minmc_factor_cache.json").read_text())["functions"]
    schedules = json.loads((ROOT / "artifacts/phase_retention_schedules.json").read_text())
    candidates = []
    for index, (x, y) in enumerate(terms):
        row = {"term_index": index, "candidates": []}
        blocks = {}
        # Existing independent pair primitive.
        try:
            blocks["pair_circuit"] = pair_circuit(x, y)
        except Exception as error:
            row["pair_circuit_error"] = str(error)
        # Formula/XAG parallel compiler is known to succeed on a subset; try
        # every term and record infeasible rather than aborting the portfolio.
        try:
            blocks["parallel_rank_pair_xag"] = parallel_pair(x, y)[3]
        except Exception as error:
            row["parallel_rank_pair_xag_error"] = str(error)
        # Bounded low-AND scalar compiler, when both cached factors exist.
        try:
            from minmc_rank_pair import compile_side
            from qiskit import QuantumCircuit
            cx = compile_side(cache[str(x)], list(range(6)), 12, [13, 14])
            cy = compile_side(cache[str(y)], list(range(6, 12)), 15, [16, 17])
            blocks["minmc_rank_pair"] = QuantumCircuit(18)
            blocks["minmc_rank_pair"].compose(cx, inplace=True)
            blocks["minmc_rank_pair"].compose(cy, inplace=True)
            blocks["minmc_rank_pair"].cz(12, 15)
            blocks["minmc_rank_pair"].compose(blocks["minmc_rank_pair"].copy().inverse(), inplace=False)
            # Rebuild correctly as compute-CZ-uncompute.
            pre = QuantumCircuit(18); pre.compose(cx, inplace=True); pre.compose(cy, inplace=True)
            blocks["minmc_rank_pair"] = pre.copy(); blocks["minmc_rank_pair"].cz(12, 15); blocks["minmc_rank_pair"].compose(pre.inverse(), inplace=True)
        except Exception as error:
            row["minmc_rank_pair_error"] = str(error)
        try:
            blocks["phase_retention"] = retention_block(index, terms, cache, schedules)
        except Exception as error:
            row["phase_retention_error"] = str(error)
        try:
            blocks["phase_pebble"] = compile_phase_pebble(x, y, cache)[0]
        except Exception as error:
            row["phase_pebble_error"] = str(error)
        for name, block in blocks.items():
            metadata = {"term_index": index, "compiler": name, "verification": "selected block included in exhaustive complete-oracle verification"}
            out = save_block(name, index, block, metadata)
            metadata["representation"] = name
            metadata["compute_count"] = int(block.count_ops().get("rccx", 0))
            metadata["phase_edge_count"] = None
            row["candidates"].append(metadata)
        candidates.append(row)
    (ROOT / "artifacts/rank_portfolio_metrics.json").write_text(json.dumps(candidates, indent=2))
    return terms, candidates


def compose_policy(terms, candidates, policy):
    blocks = {}
    for row in candidates:
        feasible = [c for c in row["candidates"] if "depth" in c]
        if policy == "min_depth": chosen = min(feasible, key=lambda c: (c["depth"], c["cx"]))
        elif policy == "min_cx": chosen = min(feasible, key=lambda c: (c["cx"], c["depth"]))
        else: chosen = min(feasible, key=lambda c: (c["depth"] + c["cx"] / 20, c["depth"]))
        blocks[row["term_index"]] = (chosen["compiler"], QuantumCircuit.from_qasm_file(chosen["qasm"]))
    q = QuantumCircuit(18)
    for i in range(10): q.compose(blocks[i][1], inplace=True)
    return q, [blocks[i][0] for i in range(10)]


def main():
    terms, candidates = build_portfolio()
    results = []
    for policy in ("min_depth", "min_cx", "multi_objective"):
        q, assignment = compose_policy(terms, candidates, policy)
        d, c = score(q); results.append({"policy": policy, "assignment": assignment, "depth": d, "cx": c})
    rng = random.Random(20260909)
    row = next(r for r in results if r["policy"] == "multi_objective")
    chosen = [QuantumCircuit.from_qasm_file(c["qasm"]) for r in candidates for c in [min(r["candidates"], key=lambda c: (c["depth"] + c["cx"] / 20, c["depth"]))]]
    for trial in range(500):
        order = list(range(10)); rng.shuffle(order); q = QuantumCircuit(18)
        for i in order: q.compose(chosen[i], inplace=True)
        d, c = score(q); results.append({"policy": "multi_objective_random", "trial": trial, "order": order, "depth": d, "cx": c})
    best = min(results, key=lambda r: (r["depth"], r["cx"]))
    q = QuantumCircuit(18)
    for i in best.get("order", range(10)): q.compose(chosen[i], inplace=True)
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    (ROOT / "artifacts/hybrid_rank_best.qasm").write_text(qasm2.dumps(out))
    (ROOT / "artifacts/hybrid_rank_order_search.json").write_text(json.dumps({"results": results, "best": best}, indent=2))
    print("best", best, flush=True)


if __name__ == "__main__": main()
