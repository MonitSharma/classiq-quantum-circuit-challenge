"""Summarize retention search campaigns without logging every rejected move."""

import json
from pathlib import Path

from phase_retention import exact_retention_schedule, execute_actions, make_pair_graph, phase_edges, score


def main():
    progress = [json.loads(line) for line in Path("artifacts/phase_retention_progress.jsonl").read_text().splitlines()]
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    x, y = terms[6]
    graph, xr, yr, _ = make_pair_graph(x, y, cache)
    edges, constant = phase_edges(xr, yr); edges = sorted(edges)
    actions, explored, status = exact_retention_schedule(graph, edges)
    exact = None
    if actions is not None:
        q, metrics = execute_actions(graph, edges, actions, constant)
        depth, cx = score(q)
        exact = {"status": status, "explored_states": explored, "actions": len(actions),
                 "depth": depth, "cx": cx, **metrics}
    output = {
        "campaigns": {
            "term_6": {"local_order_attempts": 500, "beam_widths": [64, 256, 1024], "exact_state_budget": 2000000},
            "term_7": {"local_order_attempts": 2000, "beam_widths": [64, 256, 1024]},
        },
        "observed_transpiled_candidates": {
            "term_6": sum(r.get("scheduler") == "local_order" and r.get("term_index") == 6 for r in progress),
            "term_7": sum(r.get("scheduler") == "local_order" and r.get("term_index") == 7 for r in progress),
        },
        "best_actual": {
            str(i): min((r for r in progress if r.get("term_index") == i and "depth" in r),
                       key=lambda r: (r["depth"], r["cx"]), default=None)
            for i in (6, 7)
        },
        "exact_term_6": exact,
        "note": "Local-order attempts use structural screening; only screened/improving checkpoints are transpiled and logged."
    }
    Path("artifacts/retention_search_diagnostics.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__": main()
