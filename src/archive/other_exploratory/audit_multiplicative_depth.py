"""Audit exact XAG-style networks already reconstructible in the repository."""

from __future__ import annotations

import json
from pathlib import Path

from md_xag import XAG, AndNode, logo_truth_table
from xag import make_graph


ROOT = Path(__file__).resolve().parents[1]


def convert_form(form: frozenset[int], node_map: dict[int, int]) -> int:
    mask = 0
    for signal in form:
        if signal == -1:
            mask |= 1
        elif signal < 12:
            mask |= 1 << (signal + 1)
        else:
            mask |= 1 << node_map[signal]
    return mask


def shared_rank_xag() -> XAG:
    terms = json.loads((ROOT / "artifacts/rank_terms.json").read_text())
    graph, roots = make_graph(terms)
    node_map = {signal: signal + 1 for signal in sorted(graph.nodes)}
    nodes = [
        AndNode(
            convert_form(graph.nodes[signal][0], node_map),
            convert_form(graph.nodes[signal][1], node_map),
        )
        for signal in sorted(graph.nodes)
    ]
    output_mask = 0
    for left, right in roots:
        nodes.append(AndNode(convert_form(left, node_map), convert_form(right, node_map)))
        output_mask ^= 1 << (1 + 12 + len(nodes) - 1)
    return XAG(nodes, output_mask)


def main() -> None:
    networks = {
        "balanced_anf": XAG([], 0),
        "shared_rank_formula": shared_rank_xag(),
    }
    from md_xag import build_balanced_anf_xag
    networks["balanced_anf"] = build_balanced_anf_xag()
    result = {
        "target_truth_table_sha256": __import__("md_xag").truth_table_sha256(logo_truth_table()),
        "networks": {
            name: graph.metrics() for name, graph in networks.items()
        },
    }
    out = ROOT / "artifacts/multiplicative_depth/existing_xag_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
