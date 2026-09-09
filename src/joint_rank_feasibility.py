"""Diagnostic scan for joint rank-factor pebbling under a small ancilla limit.

This does not generate a scored oracle.  It records whether the existing
truth-table rank bases admit simultaneous computation of two or three
same-side factors with the repository's exact XAG planner.
"""

import itertools
import json
from pathlib import Path
import sys

from formula import formula, remap
from xag import Graph, plan


def side_feasible(tables, offset, limit, max_states=300_000):
    graph = Graph()
    roots = [
        graph.expr(remap(formula(table, 6), range(offset, offset + 6)))
        for table in tables
    ]
    try:
        path = plan(graph, set(), roots, limit=limit, max_states=max_states)
    except ValueError:
        return None
    return {"toggle_count": len(path), "graph_nodes": len(graph.nodes)}


def scan_basis(path, limits=(3, 4, 5, 6), arities=(2, 3)):
    terms = json.loads(Path(path).read_text())
    result = {"basis": str(path), "terms": len(terms), "limits": {}}
    for limit in limits:
        limit_result = {}
        for arity in arities:
            feasible = []
            for combo in itertools.combinations(range(len(terms)), arity):
                x = side_feasible([terms[i][0] for i in combo], 0, limit)
                y = side_feasible([terms[i][1] for i in combo], 6, limit)
                if x is not None and y is not None:
                    feasible.append({"indices": combo, "x": x, "y": y})
            limit_result[str(arity)] = feasible
        result["limits"][str(limit)] = limit_result
    return result


if __name__ == "__main__":
    output = {}
    for name in ("rank_terms", "pair_terms", "rank_mc_pareto_terms"):
        output[name] = scan_basis(f"artifacts/{name}.json")
    print(json.dumps(output, indent=2))
