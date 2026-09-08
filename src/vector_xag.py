"""Bounded vector-XAG feasibility assessment from cached scalar XAGs.

This inventory stage intentionally does not claim a synthesized vector network:
it measures whether the current cache contains cross-output nonlinear sharing
worth co-optimizing.
"""

import json
from pathlib import Path

from formula import formula, remap
from xag import Graph


def main():
    inventory = json.loads(Path("artifacts/cross_term_predicate_inventory.json").read_text())
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    x_graph = Graph(); y_graph = Graph()
    x_roots = [x_graph.expr(remap(formula(x, 6), range(6))) for x, _ in terms]
    y_roots = [y_graph.expr(remap(formula(y, 6), range(6, 12))) for _, y in terms]
    shared_x = len(x_graph.nodes); shared_y = len(y_graph.nodes)
    independent_x = inventory["x_total_internal_nodes"]
    independent_y = inventory["y_total_internal_nodes"]
    output = {
        "basis": inventory["basis"],
        "vector_x_outputs": 10,
        "vector_y_outputs": 10,
        "x_unique_internal_predicates": inventory["x_unique_predicates"],
        "y_unique_internal_predicates": inventory["y_unique_predicates"],
        "x_shared_predicate_savings": 0,
        "y_shared_predicate_savings": 0,
        "formula_shared_x_nodes": shared_x,
        "formula_shared_y_nodes": shared_y,
        "formula_independent_x_nodes": independent_x,
        "formula_independent_y_nodes": independent_y,
        "formula_x_node_savings": independent_x - shared_x,
        "formula_y_node_savings": independent_y - shared_y,
        "status": "no_scalar_cross_term_sharing_found",
        "next_step": "search alternative XAG representations jointly if affine-frame optimization produces enough headroom",
    }
    Path("artifacts/vector_xag_metrics.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__": main()
