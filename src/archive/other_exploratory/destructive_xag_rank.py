"""GF(2) affine live-rank audit for the destructive-XAG experiment."""

from __future__ import annotations

import json
from pathlib import Path

from md_xag import FULL, XAG, mask_indices
from destructive_xag import load_xag


ROOT = Path(__file__).resolve().parents[1]


def gf2_rank(values: list[int]) -> int:
    basis: dict[int, int] = {}
    for value in values:
        value = int(value)
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


def independent_signals(values: dict[int, int], signals: list[int]) -> list[int]:
    basis: dict[int, int] = {}
    for value in (FULL,):
        basis[value.bit_length() - 1] = value
    result = []
    for signal in signals:
        value = values[signal]
        reduced = value
        while reduced:
            pivot = reduced.bit_length() - 1
            if pivot in basis:
                reduced ^= basis[pivot]
            else:
                basis[pivot] = reduced
                result.append(signal)
                break
    return result


def rank_profile(path: Path) -> dict:
    parsed = load_xag(path)
    graph: XAG = parsed.graph
    signals = graph._signals()
    uses: dict[int, list[int]] = {signal: [] for signal in range(graph.signal_count)}
    for node_index, node in enumerate(parsed.nodes, start=13):
        for mask in (node.left_affine_mask, node.right_affine_mask):
            for signal in mask_indices(mask):
                if signal:
                    uses.setdefault(signal, []).append(node_index)

    profiles = []
    end = 13 + len(parsed.nodes)
    for cut in range(13, end + 1):
        live = []
        for signal in range(1, 13):
            if any(use >= cut for use in uses[signal]):
                live.append(signal)
        for signal in range(13, cut):
            if any(use >= cut for use in uses[signal]):
                live.append(signal)
        vectors = {signal: signals[signal] for signal in live}
        profiles.append({
            "cut": cut,
            "naive_live_count": len(live),
            "affine_rank_including_constant": gf2_rank([FULL, *(vectors[s] for s in live)]),
            "rank_increasing_signals": independent_signals(vectors, live),
            "live_signals": live,
            "future_use_counts": {
                str(signal): sum(use >= cut for use in uses[signal]) for signal in live
            },
        })

    return {
        "xag": str(path.relative_to(ROOT)),
        "exact": graph.exact(),
        "and_count": len(parsed.nodes),
        "cuts": profiles,
        "maximum_naive_live_count": max(row["naive_live_count"] for row in profiles),
        "maximum_affine_rank_including_constant": max(
            row["affine_rank_including_constant"] for row in profiles
        ),
        "available_physical_wires": 18,
        "predicate_wire_reserved": False,
        "affine_packing_alone_fits_current_order": max(
            row["affine_rank_including_constant"] for row in profiles
        ) <= 18,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xag", type=Path, default=ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/destructive_xag_affine_rank.json")
    args = parser.parse_args()
    report = rank_profile(args.xag)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cuts"}, indent=2))


if __name__ == "__main__":
    main()
