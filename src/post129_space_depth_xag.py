"""Phase-0 audit and no-recompute storage screen for repository XAGs."""

from __future__ import annotations

import argparse
import glob
import json
import random
from pathlib import Path

from md_xag import AndNode, XAG, logo_truth_table, mask_indices

ROOT = Path(__file__).resolve().parents[1]
BASE = 13
MAX_NONLINEAR_LIVE = 6


def load(path: Path) -> tuple[list[AndNode], int]:
    nodes, output = [], None
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "AND":
            nodes.append(AndNode(int(fields[1]), int(fields[2])))
        elif fields[0] == "OUTPUT":
            output = int(fields[1])
    if output is None:
        raise ValueError(f"missing OUTPUT: {path}")
    return nodes, output


def dependencies(nodes: list[AndNode]) -> list[set[int]]:
    result = []
    for node in nodes:
        result.append({signal - BASE for mask in (node.left_affine_mask, node.right_affine_mask)
                       for signal in mask_indices(mask) if signal >= BASE})
    return result


def no_recompute_screen(nodes: list[AndNode], output: int, restarts: int = 64) -> dict:
    deps = dependencies(nodes)
    n = len(nodes)
    consumers = [set() for _ in range(n)]
    for node, needed in enumerate(deps):
        for parent in needed:
            consumers[parent].add(node)
    roots = {node for node in range(n) if output >> (BASE + node) & 1}
    best = None
    best_order = None
    for restart in range(restarts):
        rng = random.Random(restart)
        done, live, remaining = set(), set(), [set(x) for x in consumers]
        order = []
        while len(done) < n:
            ready = [node for node in range(n) if node not in done and deps[node] <= done]
            if not ready:
                raise ValueError("invalid non-topological XAG")
            def key(node):
                unlock = sum(1 for child in range(n) if node in deps[child] and child not in done)
                keep = int(bool(consumers[node])) and node not in roots
                return (len(live) + keep - unlock * 0.25, -unlock, rng.random(), node)
            node = min(ready, key=key)
            done.add(node); order.append(node)
            if consumers[node] and node not in roots:
                live.add(node)
            for parent in deps[node]:
                remaining[parent].discard(node)
                if not remaining[parent] and parent in live:
                    live.remove(parent)
        peak = max((len(set(order[:i+1]) & set()), 0) for i in range(0)) if False else 0
        # Replay the order to measure exact liveness, including immediate root phase.
        live, remaining = set(), [set(x) for x in consumers]
        for node in order:
            if consumers[node] and node not in roots:
                live.add(node)
            for parent in deps[node]:
                remaining[parent].discard(node)
                if not remaining[parent]:
                    live.discard(parent)
            peak = max(peak, len(live))
        if best is None or peak < best:
            best, best_order = peak, order
    return {"best_peak_live_no_recompute": best, "wires_needed": 12 + best,
            "within_six_pebbles": best <= MAX_NONLINEAR_LIVE,
            "order": [BASE + node for node in best_order]}


def audit(path: Path) -> dict:
    nodes, output = load(path)
    graph = XAG(nodes, output)
    signals = graph._signals()
    target = logo_truth_table()
    depths = graph.node_layers()
    deps = dependencies(nodes)
    level_counts = [depths.count(level) for level in range(1, max(depths, default=0) + 1)]
    fanout = graph.fanouts()
    screen = no_recompute_screen(nodes, output)
    display_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {"path": display_path, "exact_logo": graph.evaluate() == target,
            "and_count": len(nodes), "multiplicative_depth": max(depths, default=0),
            "and_layer_widths": level_counts, "output_affine_mask": output,
            "output_signal_count": sum(1 for _ in mask_indices(output)),
            "max_fanout": max(fanout, default=0),
            "nonlinear_dependency_counts": [len(dep) for dep in deps],
            "max_nonlinear_dependency_count": max((len(dep) for dep in deps), default=0),
            "live_width_estimate": graph.live_width(), "screen": screen}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts/post129_space_depth_xag/xag_inventory.json")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or [Path(path) for path in glob.glob(str(ROOT / "artifacts/**/*.xag"), recursive=True)]
    rows, failures = [], []
    for path in sorted(set(paths)):
        try:
            rows.append(audit(path))
        except Exception as exc:
            display_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            failures.append({"path": display_path, "error": repr(exc)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"status": "complete", "graphs": rows,
                                    "failures": failures}, indent=2) + "\n")
    print(json.dumps({"graphs": len(rows), "exact": sum(row["exact_logo"] for row in rows),
                      "failures": len(failures)}, indent=2))


if __name__ == "__main__":
    main()
