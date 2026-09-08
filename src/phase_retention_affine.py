"""Benchmark affine-frame accounting for selected retained schedules.

The frame model is intentionally staged: it verifies the linear-frame
primitive and reports the current retained circuit's parity/phase overhead
without changing nonlinear scheduling. This prevents an unverified frame
rewrite from being mistaken for a circuit improvement.
"""

import json
from pathlib import Path

from phase_retention import execute_actions, make_pair_graph, phase_edges, score
from affine_frame import AffineFrame


def main():
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    schedules = json.loads(Path("artifacts/phase_retention_schedules.json").read_text())
    rows = []
    for index in (6, 7):
        x, y = terms[index]
        graph, xr, yr, representation = make_pair_graph(x, y, cache)
        edges, constant = phase_edges(xr, yr); edges = sorted(edges)
        actions = [tuple(a) for a in schedules[str(index)]["actions"]]
        circuit, metrics = execute_actions(graph, edges, actions, constant)
        depth, cx = score(circuit)
        frame = AffineFrame()
        for operation in [("cx", 0, 1), ("cx", 1, 2), ("x", 2, 2), ("cx", 2, 1), ("cx", 1, 0)]:
            frame = frame.cnot(operation[1], operation[2]) if operation[0] == "cx" else frame.x(operation[1])
        assert frame.invertible()
        rows.append({"term_index": index, "representation": representation,
                     "depth": depth, "cx": cx, "raw_cx": circuit.count_ops().get("cx", 0),
                     "raw_rccx": circuit.count_ops().get("rccx", 0),
                     "raw_cz": circuit.count_ops().get("cz", 0),
                     "raw_x": circuit.count_ops().get("x", 0), **metrics,
                     "affine_frame_unit_test": "passed"})
    Path("artifacts/affine_frame_cost_breakdown.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
