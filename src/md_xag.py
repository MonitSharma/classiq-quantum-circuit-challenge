"""Independent exact XOR--AND graph representation and metrics.

Signal 0 is constant one, signals 1..12 are the repository's input bits, and
subsequent signal IDs are two-input AND nodes.  An affine mask is a Python
integer whose set bits select signals to XOR.  The module intentionally does
not lower an XAG to a quantum circuit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from search import logo


N_INPUTS = 12
N_POINTS = 1 << N_INPUTS
FULL = (1 << N_POINTS) - 1


def input_truth_tables() -> list[int]:
    return [
        sum(1 << point for point in range(N_POINTS) if point & (1 << bit))
        for bit in range(N_INPUTS)
    ]


def logo_truth_table() -> int:
    return sum(
        1 << point
        for point in range(N_POINTS)
        if logo(point & 63, (point >> 6) & 63)
    )


def truth_table_sha256(table: int) -> str:
    return hashlib.sha256(table.to_bytes(N_POINTS // 8, "little")).hexdigest()


@dataclass(frozen=True)
class AndNode:
    left_affine_mask: int
    right_affine_mask: int


@dataclass
class XAG:
    and_nodes: list[AndNode]
    output_affine_mask: int

    @property
    def signal_count(self) -> int:
        return 1 + N_INPUTS + len(self.and_nodes)

    def _signals(self) -> list[int]:
        signals = [FULL, *input_truth_tables()]
        for node in self.and_nodes:
            left = xor_mask(node.left_affine_mask, signals)
            right = xor_mask(node.right_affine_mask, signals)
            signals.append(left & right)
        return signals

    def evaluate(self) -> int:
        signals = self._signals()
        return xor_mask(self.output_affine_mask, signals)

    def exact(self, target: int | None = None) -> bool:
        return self.evaluate() == (logo_truth_table() if target is None else target)

    def depths(self) -> list[int]:
        depths = [0] * (1 + N_INPUTS)
        for node in self.and_nodes:
            left_depth = max((depths[i] for i in mask_indices(node.left_affine_mask)), default=0)
            right_depth = max((depths[i] for i in mask_indices(node.right_affine_mask)), default=0)
            depths.append(1 + max(left_depth, right_depth))
        return depths

    def node_layers(self) -> list[int]:
        depths = self.depths()
        return depths[1 + N_INPUTS:]

    def fanouts(self) -> list[int]:
        fanout = [0] * self.signal_count
        for node in self.and_nodes:
            for index in mask_indices(node.left_affine_mask):
                fanout[index] += 1
            for index in mask_indices(node.right_affine_mask):
                fanout[index] += 1
        for index in mask_indices(self.output_affine_mask):
            fanout[index] += 1
        return fanout

    def live_width(self) -> int:
        """Peak live nonlinear values under topological node order."""
        last_use = [0] * self.signal_count
        for node_index, node in enumerate(self.and_nodes, start=1 + N_INPUTS):
            for index in mask_indices(node.left_affine_mask):
                last_use[index] = max(last_use[index], node_index)
            for index in mask_indices(node.right_affine_mask):
                last_use[index] = max(last_use[index], node_index)
        end = len(self.and_nodes) + 1 + N_INPUTS
        for index in mask_indices(self.output_affine_mask):
            last_use[index] = max(last_use[index], end)
        live = 0
        peak = 0
        for signal_id in range(1 + N_INPUTS, self.signal_count):
            live += 1
            peak = max(peak, live)
            if last_use[signal_id] <= signal_id:
                live -= 1
        return peak

    def metrics(self, target: int | None = None) -> dict:
        layers = self.node_layers()
        widths = [layers.count(depth) for depth in range(1, max(layers, default=0) + 1)]
        fanout = self.fanouts()
        return {
            "exact": self.exact(target),
            "and_count": len(self.and_nodes),
            "multiplicative_depth": max(layers, default=0),
            "and_layer_widths": widths,
            "nonlinear_live_width_estimate": self.live_width(),
            "max_fanout": max(fanout, default=0),
            "truth_table_sha256": truth_table_sha256(
                logo_truth_table() if target is None else target
            ),
        }

    def to_json(self) -> dict:
        return {
            "and_nodes": [
                {
                    "left_affine_mask": node.left_affine_mask,
                    "right_affine_mask": node.right_affine_mask,
                }
                for node in self.and_nodes
            ],
            "output_affine_mask": self.output_affine_mask,
        }


def mask_indices(mask: int) -> Iterable[int]:
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def xor_mask(mask: int, signals: list[int]) -> int:
    result = 0
    for index in mask_indices(mask):
        result ^= signals[index]
    return result


def anf_coefficients(values: list[int]) -> list[int]:
    coefficients = values[:]
    for bit in range(N_INPUTS):
        for mask in range(N_POINTS):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    return coefficients


def logo_anf() -> tuple[list[int], dict[int, int]]:
    values = [
        int(logo(point & 63, (point >> 6) & 63))
        for point in range(N_POINTS)
    ]
    coefficients = anf_coefficients(values)
    by_degree: dict[int, int] = {}
    for mask, coefficient in enumerate(coefficients):
        if coefficient:
            by_degree[mask.bit_count()] = by_degree.get(mask.bit_count(), 0) + 1
    return coefficients, by_degree


def _balanced_product(signals: list[int], nodes: list[AndNode]) -> int:
    current = signals[:]
    while len(current) > 1:
        next_level: list[int] = []
        for index in range(0, len(current) - 1, 2):
            left, right = current[index], current[index + 1]
            nodes.append(AndNode(1 << left, 1 << right))
            next_level.append(1 + N_INPUTS + len(nodes) - 1)
        if len(current) & 1:
            next_level.append(current[-1])
        current = next_level
    return current[0]


def build_balanced_anf_xag() -> XAG:
    coefficients, _ = logo_anf()
    nodes: list[AndNode] = []
    output_mask = 0
    for monomial, coefficient in enumerate(coefficients):
        if not coefficient:
            continue
        if monomial == 0:
            output_mask ^= 1
            continue
        variables = [1 + bit for bit in mask_indices(monomial)]
        root = _balanced_product(variables, nodes)
        output_mask ^= 1 << root
    return XAG(nodes, output_mask)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--include-network", action="store_true")
    parser.add_argument("--truth-hex", type=Path)
    args = parser.parse_args()
    xag = build_balanced_anf_xag()
    target = logo_truth_table()
    if args.truth_hex:
        args.truth_hex.parent.mkdir(parents=True, exist_ok=True)
        args.truth_hex.write_text(target.to_bytes(N_POINTS // 8, "little").hex() + "\n")
    result = {
        "target": {
            "variables": N_INPUTS,
            "points": N_POINTS,
            "marked_points": target.bit_count(),
            "truth_table_sha256": truth_table_sha256(target),
        },
        "anf_terms_by_degree": {
            str(degree): count for degree, count in logo_anf()[1].items()
        },
        "network": xag.metrics(target),
    }
    if args.include_network:
        result["xag"] = xag.to_json()
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
