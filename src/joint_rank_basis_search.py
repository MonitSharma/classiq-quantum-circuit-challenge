"""Bounded search for rank bases that admit joint three-ancilla schedules.

The elementary mutation preserves the XOR of pair products:
 (a_i,b_i),(a_j,b_j) -> (a_i XOR a_j,b_i),(a_j,b_j XOR b_i).
This is a diagnostic search; it does not emit a QASM oracle.
"""

import itertools
import json
import random
from pathlib import Path

from formula import formula, remap
from xag import Graph, plan


def feasible(table_pair, offset, max_states):
    graph = Graph()
    roots = [
        graph.expr(remap(formula(table, 6), range(offset, offset + 6)))
        for table in table_pair
    ]
    try:
        path = plan(graph, set(), roots, limit=3, max_states=max_states)
    except ValueError:
        return None
    return {"toggles": len(path), "nodes": len(graph.nodes)}


def search(steps=40, pairs_per_step=12, seed=20260909, max_states=30_000):
    rng = random.Random(seed)
    current = json.loads(Path("artifacts/rank_terms.json").read_text())
    checked = []
    all_pairs = list(itertools.combinations(range(10), 2))
    for step in range(steps):
        i, j = rng.sample(range(10), 2)
        xi, yi = current[i]
        xj, yj = current[j]
        candidate = [list(term) for term in current]
        candidate[i] = [xi ^ xj, yi]
        candidate[j] = [xj, yi ^ yj]
        current = candidate
        pairs = rng.sample(all_pairs, min(pairs_per_step, len(all_pairs)))
        for pair in pairs:
            x = feasible([current[k][0] for k in pair], 0, max_states)
            y = feasible([current[k][1] for k in pair], 6, max_states)
            row = {"step": step, "indices": pair, "x": x, "y": y}
            checked.append(row)
            if x is not None and y is not None:
                return {"seed": seed, "steps": step + 1, "found": row, "terms": current, "checked": checked}
        if step % 5 == 0:
            print("checked step", step, flush=True)
    return {"seed": seed, "steps": steps, "found": None, "checked": checked}


if __name__ == "__main__":
    result = search()
    Path("artifacts/joint_rank_basis_search_development.json").write_text(
        json.dumps(result, indent=2)
    )
    print(json.dumps({k: result[k] for k in ("seed", "steps", "found")}, indent=2))
