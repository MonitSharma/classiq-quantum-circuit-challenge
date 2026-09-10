"""Export the reconstructible shared rank XAG for the C++ pilot."""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from audit_multiplicative_depth import shared_rank_xag
from md_xag import build_balanced_anf_xag


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=("shared_rank", "balanced_anf"), default="shared_rank")
    args = parser.parse_args()
    graph = shared_rank_xag() if args.network == "shared_rank" else build_balanced_anf_xag()
    out = ROOT / "artifacts/multiplicative_depth/seeds/{0}.xag".format(args.network)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# signal masks use md_xag IDs: bit 0=constant-one, bits 1..12=inputs",
        f"# and_count {len(graph.and_nodes)}",
    ]
    for node in graph.and_nodes:
        lines.append(f"AND {node.left_affine_mask} {node.right_affine_mask}")
    lines.append(f"OUTPUT {graph.output_affine_mask}")
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps({"path": str(out), **graph.metrics()}, indent=2))


if __name__ == "__main__":
    main()
