"""Inventory shared nonlinear predicates across the ten rank factors."""

import json
from collections import Counter, defaultdict
from pathlib import Path


def node_tables(spec):
    full = (1 << 64) - 1
    inputs = [sum(1 << i for i in range(64) if i >> bit & 1) for bit in range(6)]
    signals = [full, *inputs]; result = {}
    for index, node in enumerate(spec["and_nodes"]):
        left = 0; right = 0
        for value in node["left"]: left ^= signals[value]
        for value in node["right"]: right ^= signals[value]
        value = left & right; signals.append(value); result[index] = value
    return result


def main():
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    sides = {"x": [], "y": []}
    for index, (x, y) in enumerate(terms):
        for side, table in (("x", x), ("y", y)):
            spec = cache.get(str(table))
            if spec is None: continue
            for node, truth in node_tables(spec).items():
                sides[side].append({"term_index": index, "node": node, "truth_table": truth})
    counts = {side: Counter(row["truth_table"] for row in rows) for side, rows in sides.items()}
    output = {
        "basis": "rank_mc_pareto_terms",
        "x_total_internal_nodes": len(sides["x"]),
        "y_total_internal_nodes": len(sides["y"]),
        "x_unique_predicates": len(counts["x"]),
        "y_unique_predicates": len(counts["y"]),
        "x_repeated_predicates": sum(v > 1 for v in counts["x"].values()),
        "y_repeated_predicates": sum(v > 1 for v in counts["y"].values()),
        "x_top_repeated": [{"truth_table": k, "uses": v} for k, v in counts["x"].most_common() if v > 1],
        "y_top_repeated": [{"truth_table": k, "uses": v} for k, v in counts["y"].most_common() if v > 1],
        "note": "Internal predicate truth tables are canonicalized over six local variables; missing bounded-XAG factors are omitted and reported by cache state.",
    }
    Path("artifacts/cross_term_predicate_inventory.json").write_text(json.dumps(output, indent=2))
    print(json.dumps({k: output[k] for k in output if k.endswith("predicates") or k.endswith("nodes")}, indent=2))


if __name__ == "__main__": main()
