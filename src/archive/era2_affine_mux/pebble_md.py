"""Bounded nonlinear-pebble feasibility check for an exact XAG seed."""

from __future__ import annotations

import json
from pathlib import Path

from xag import plan


ROOT = Path(__file__).resolve().parents[1]


class SeedGraph:
    def __init__(self, path: Path):
        self.nodes: dict[int, tuple[frozenset[int], frozenset[int]]] = {}
        self.output = 0
        for line in path.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "AND":
                index = 13 + len(self.nodes)
                self.nodes[index] = (self.form(int(parts[1])), self.form(int(parts[2])))
            elif parts[0] == "OUTPUT":
                self.output = int(parts[1])
            else:
                raise ValueError(f"unknown record: {line}")

    @staticmethod
    def form(mask: int) -> frozenset[int]:
        values = set()
        while mask:
            bit = mask & -mask
            index = bit.bit_length() - 1
            values.add(-1 if index == 0 else index - 1 if index <= 12 else index)
            mask ^= bit
        return frozenset(values)

    def ancestors(self, forms):
        out = {v for form in forms for v in form if v >= 12}
        stack = list(out)
        while stack:
            value = stack.pop()
            for form in self.nodes[value]:
                for parent in form:
                    if parent >= 12 and parent not in out:
                        out.add(parent)
                        stack.append(parent)
        return out


def main() -> None:
    seed = ROOT / "artifacts/multiplicative_depth/affine/shared_rank/seed_118.xag"
    graph = SeedGraph(seed)
    outputs = [index for index in range(13, 13 + len(graph.nodes)) if graph.output & (1 << index)]
    live: set[int] = set()
    toggles = 0
    peak = 0
    steps = []
    for output in outputs:
        path = plan(graph, frozenset(live), [frozenset([output])], limit=6)
        for value in path:
            if value in live:
                live.remove(value)
            else:
                live.add(value)
            peak = max(peak, len(live))
        toggles += len(path)
        steps.append({"output_signal": output, "compute_toggles": len(path), "live_after_tap": len(live)})
        clear = plan(graph, frozenset(live), [], limit=6)
        for value in clear:
            if value in live:
                live.remove(value)
            else:
                live.add(value)
            peak = max(peak, len(live))
        toggles += len(clear)
    result = {
        "seed": str(seed.relative_to(ROOT)),
        "exact_seed": True,
        "output_taps": len(outputs),
        "clean_ancilla_limit": 6,
        "feasible": not live and peak <= 6,
        "peak_live_nonlinear_values": peak,
        "nonlinear_toggle_count": toggles,
        "steps": steps,
    }
    out = ROOT / "artifacts/multiplicative_depth/quantum_pebble_feasibility.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
