"""Bounded clean-pebble feasibility scan over screened output bases."""

from __future__ import annotations

import json
from pathlib import Path

from xag import plan
from vector_reversible_pebble import ARTIFACTS, PlanGraph, parse


def minimum_pebbles(graph, form, max_states=100_000):
    for limit in range(1, 7):
        try:
            path = plan(graph, frozenset(), [form], limit=limit,
                        max_states=max_states)
            return {"pebbles": limit, "toggle_count": len(path)}
        except ValueError:
            continue
    return {"pebbles": None, "toggle_count": None}


def main() -> None:
    records = []
    for path in sorted(ARTIFACTS.glob("vector_basis_*.bench")):
        graph = parse(path)
        adapter = PlanGraph(graph)
        outputs = {
            name: minimum_pebbles(adapter, form)
            for name, form in graph.outputs.items()
        }
        records.append({
            "source": str(path.relative_to(path.parents[1])),
            "product_nodes": len(graph.nodes),
            "outputs": outputs,
        })
    result = {
        "basis_networks": len(records),
        "clean_workspace_limit": 6,
        "target_accumulator_reservation": 1,
        "screened_with_max_states": 100_000,
        "all_outputs_fit_with_five_or_fewer": sum(
            all(item["pebbles"] is not None and item["pebbles"] <= 5
                for item in record["outputs"].values())
            for record in records
        ),
        "records": records,
        "note": "A clean output target would leave at most five graph pebbles; this is a feasibility screen, not a complete loader compiler.",
    }
    out = ARTIFACTS / "vector_feature_reversible_schedule.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "basis_networks": result["basis_networks"],
        "all_outputs_fit_with_five_or_fewer": result["all_outputs_fit_with_five_or_fewer"],
    }, indent=2))


if __name__ == "__main__":
    main()
