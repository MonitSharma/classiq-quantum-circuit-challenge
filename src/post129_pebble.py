"""Bounded reversible six-pebble feasibility search for exact XAG graphs."""

from __future__ import annotations

import argparse
import heapq
import json
from pathlib import Path

from post129_space_depth_xag import BASE, MAX_NONLINEAR_LIVE, dependencies, load


def solve(path: Path, max_states: int = 250_000) -> dict:
    nodes, output = load(path)
    deps = dependencies(nodes)
    n = len(nodes)
    dep_masks = [sum(1 << parent for parent in dep) for dep in deps]
    roots = sum(1 << node for node in range(n) if output >> (BASE + node) & 1)
    consumers = [sum(1 << child for child in range(n) if node in deps[child]) for node in range(n)]
    start = (0, 0, 0)  # live, phased roots, toggles
    queue = [(0, 0, start)]
    best = {start: 0}
    parent = {}
    expanded = 0

    def heuristic(live, phased):
        return (roots & ~phased).bit_count() + live.bit_count()

    while queue and expanded < max_states:
        _, toggles, state = heapq.heappop(queue)
        live, phased, _ = state
        if best.get(state) != toggles:
            continue
        expanded += 1
        if phased == roots and live == 0:
            actions = []
            cursor = state
            while cursor != start:
                previous, action = parent[cursor]
                actions.append(action)
                cursor = previous
            actions.reverse()
            return {"status": "SAT", "peak_live": MAX_NONLINEAR_LIVE,
                    "toggle_count": toggles, "expanded_states": expanded,
                    "actions": actions}
        candidates = []
        for node in range(n):
            bit = 1 << node
            if not live & bit and dep_masks[node] & ~live == 0 and live.bit_count() < MAX_NONLINEAR_LIVE:
                next_live = live | bit
                next_phased = phased | (bit & roots)
                candidates.append((next_live, next_phased, f"COMPUTE({BASE + node})"))
            if live & bit and consumers[node] & live == 0:
                candidates.append((live ^ bit, phased, f"UNCOMPUTE({BASE + node})"))
        for next_live, next_phased, action in candidates:
            next_state = (next_live, next_phased, 0)
            next_toggles = toggles + 1
            if next_toggles < best.get(next_state, 10**9):
                best[next_state] = next_toggles
                parent[next_state] = (state, action)
                heapq.heappush(queue, (next_toggles + heuristic(next_live, next_phased), next_toggles, next_state))
    return {"status": "UNKNOWN", "expanded_states": expanded,
            "max_states": max_states, "peak_limit": MAX_NONLINEAR_LIVE}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xag", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-states", type=int, default=250_000)
    args = parser.parse_args()
    result = solve(args.xag, args.max_states)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
