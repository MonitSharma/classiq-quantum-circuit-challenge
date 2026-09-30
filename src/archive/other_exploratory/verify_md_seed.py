"""Independently verify a serialized XAG seed and print its MD metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

from md_xag import AndNode, XAG


def load(path: Path) -> XAG:
    nodes = []
    output = 0
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "AND":
            nodes.append(AndNode(int(fields[1]), int(fields[2])))
        elif fields[0] == "OUTPUT":
            output = int(fields[1])
        else:
            raise ValueError(f"unknown XAG record: {line}")
    return XAG(nodes, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", type=Path)
    parser.add_argument("truth_hex", type=Path)
    args = parser.parse_args()
    graph = load(args.seed)
    target = int.from_bytes(bytes.fromhex(args.truth_hex.read_text().strip()), "little")
    print(graph.metrics(target))


if __name__ == "__main__":
    main()
