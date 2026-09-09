"""Extract and independently verify the endpoint functions of the 12-edge probe."""

from __future__ import annotations

import json
from pathlib import Path

from global_phase_retention import build
from phase_pebble_rank import _eval_form
from search import logo


def truth_table(graph, signal: int, side: str) -> int:
    table = 0
    for value in range(64):
        assignment = {bit: (value >> bit) & 1 for bit in range(6)}
        if side == "y":
            assignment = {6 + bit: (value >> bit) & 1 for bit in range(6)}
        if signal == -1:
            result = 1
        else:
            result = _eval_form(graph, frozenset((signal,)), assignment, {})
        if result:
            table |= 1 << value
    return table


def main():
    graph, edges, constant = build()
    rows = []
    for index, (x_signal, y_signal) in enumerate(edges):
        x_tt = truth_table(graph, x_signal, "x")
        y_tt = truth_table(graph, y_signal, "y")
        rows.append({
            "index": index,
            "x_truth_table": x_tt,
            "y_truth_table": y_tt,
            "x_source_node": x_signal,
            "y_source_node": y_signal,
        })

    mismatches = []
    for x in range(64):
        for y in range(64):
            reconstructed = int(constant)
            for row in rows:
                reconstructed ^= ((row["x_truth_table"] >> x) & 1) & ((row["y_truth_table"] >> y) & 1)
            if reconstructed != int(logo(x, y)):
                mismatches.append([x, y, reconstructed, int(logo(x, y))])
    payload = {
        "edges": rows,
        "unique_x_functions": sorted({r["x_truth_table"] for r in rows}),
        "unique_y_functions": sorted({r["y_truth_table"] for r in rows}),
        "constant": bool(constant),
        "inputs_checked": 4096,
        "mismatches": mismatches,
    }
    Path("artifacts/global_12_edge_endpoints.json").write_text(json.dumps(payload, indent=2))
    # Keep the direct expansion check in a separate, machine-readable artifact.
    check = {"inputs_checked": 4096, "mismatches": len(mismatches), "constant": bool(constant),
             "verified_against": "search.logo"}
    Path("artifacts/global_12_edge_identity_check.json").write_text(json.dumps(check, indent=2))
    print(json.dumps({"edges": len(rows), "unique_x": len(payload["unique_x_functions"]),
                      "unique_y": len(payload["unique_y_functions"]), **check}, indent=2))


if __name__ == "__main__":
    main()
