"""Boundary-aware ordering probe for the three all-pair rank bases."""

import json, random
from pathlib import Path
from qiskit import QuantumCircuit, transpile
from pair_search import pair_circuit


def score(q):
    out = transpile(q, basis_gates=["u3", "cx"], optimization_level=3,
                    qubits_initially_zero=False)
    return out.depth(), out.count_ops().get("cx", 0)


def main():
    results = {}; rng = random.Random(20260910)
    for name in ("pair_terms", "rank_terms", "rank_mc_pareto_terms"):
        terms = json.loads(Path("artifacts/" + name + ".json").read_text())
        blocks = [pair_circuit(x, y) for x, y in terms]
        individual = [b.depth() for b in blocks]
        boundary = [[0 if i == j else score(QuantumCircuit(18).compose(blocks[i]).compose(blocks[j]))[0]
                     for j in range(10)] for i in range(10)]
        # Held-Karp on the measured two-block proxy, retaining only the best
        # predecessor per (subset,last).  Whole-oracle compilation validates it.
        dp = {(1 << i, i): (0, [i]) for i in range(10)}
        for size in range(1, 10):
            for (mask, last), (cost, path) in list(dp.items()):
                if mask.bit_count() != size: continue
                for nxt in range(10):
                    if mask >> nxt & 1: continue
                    key = (mask | (1 << nxt), nxt); candidate = (cost + boundary[last][nxt], path + [nxt])
                    if key not in dp or candidate[0] < dp[key][0]: dp[key] = candidate
        predicted = min((v for (mask, _), v in dp.items() if mask == (1 << 10) - 1), key=lambda x: x[0])
        orders = [list(range(10)), list(reversed(range(10))), predicted[1]]
        orders += [rng.sample(range(10), 10) for _ in range(50)]
        measured = []
        measured_q = []
        for order in orders:
            q = QuantumCircuit(18)
            for i in order: q.compose(blocks[i], inplace=True)
            d, c = score(q); measured.append({"order": order, "depth": d, "cx": c}); measured_q.append((d, c, q))
        winner = min(range(len(measured)), key=lambda i: (measured[i]["depth"], measured[i]["cx"]))
        if name == "pair_terms":
            from qiskit import qasm2
            out = transpile(measured_q[winner][2], basis_gates=["u3", "cx"], optimization_level=3,
                            qubits_initially_zero=False)
            Path("artifacts/pair_boundary_best.qasm").write_text(qasm2.dumps(out))
        results[name] = {"individual_depths": individual, "boundary_costs": boundary,
                         "predicted": {"proxy": predicted[0], "order": predicted[1]},
                         "best": measured[winner],
                         "measured": measured}
    Path("artifacts/rank_boundary_costs.json").write_text(json.dumps(results, indent=2))
    print(json.dumps({k: {"predicted": v["predicted"], "best": v["best"]} for k, v in results.items()}, indent=2))


if __name__ == "__main__": main()
