"""Build a transformed-coordinate XAG node dictionary for Direct-E guidance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from direct_e_v2 import TARGET
from md_xag import build_balanced_anf_xag


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AFFINE = ROOT / "artifacts/direct_e_v2_affine_reproduced.json"


def build(affine_path: Path) -> dict:
    affine = json.loads(affine_path.read_text())
    mapping = affine["mapping_old_input_for_new_coordinate"]
    values = [((TARGET >> point) & 1) for point in mapping]
    transformed_table = sum(value << point for point, value in enumerate(values))
    xag = build_balanced_anf_xag(values)
    new_signals = xag._signals()
    inverse = [0] * len(mapping)
    for new_point, old_point in enumerate(mapping):
        inverse[old_point] = new_point
    nodes = []
    for node_id in range(13, len(new_signals)):
        table = sum(((new_signals[node_id] >> inverse[point]) & 1) << point
                    for point in range(4096))
        nodes.append({"signal_id": node_id, "truth_table": table,
                      "layer": xag.node_layers()[node_id - 13]})
    return {"status": "complete", "source": str(affine_path),
            "transformed_anf_terms": affine["terms"],
            "node_count": len(nodes), "metrics": xag.metrics(transformed_table),
            "nodes": nodes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--affine", type=Path, default=DEFAULT_AFFINE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.affine)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "nodes"}, indent=2))


if __name__ == "__main__":
    main()
