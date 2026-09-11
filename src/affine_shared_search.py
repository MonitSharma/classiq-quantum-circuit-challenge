"""Bounded affine-basis search on the exact shared-rank XAG."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from audit_multiplicative_depth import shared_rank_xag
from md_xag import AndNode, N_INPUTS, logo_truth_table, truth_table_sha256, XAG


ROOT = Path(__file__).resolve().parents[1]
TRUTH = ROOT / "artifacts/multiplicative_depth/logo_truth.hex"
TOOL = ROOT / "tools/mockturtle/build/md_synth"


def substitute(mask: int, mapping: list[int]) -> int:
    result = 0
    while mask:
        bit = mask & -mask
        result ^= mapping[bit.bit_length() - 1]
        mask ^= bit
    return result


def transformed_graph(rows: list[int], offset: int) -> XAG:
    # Original input x_i is the affine row_i(z) plus offset_i.
    mapping = [1]
    for i in range(N_INPUTS):
        value = (1 if (offset >> i) & 1 else 0)
        for j in range(N_INPUTS):
            if (rows[i] >> j) & 1:
                value ^= 1 << (j + 1)
        mapping.append(value)
    base = shared_rank_xag()
    mapping.extend(1 << (13 + index) for index in range(len(base.and_nodes)))
    nodes = [
        AndNode(substitute(node.left_affine_mask, mapping),
                substitute(node.right_affine_mask, mapping))
        for node in base.and_nodes
    ]
    # The internal IDs must still refer to their corresponding substituted node.
    return XAG(nodes, substitute(base.output_affine_mask, mapping))


def transformed_target(rows: list[int], offset: int) -> int:
    target = logo_truth_table()
    return sum(
        ((target >> ((sum(((rows[i] & point).bit_count() & 1) << i for i in range(N_INPUTS)) ^ offset))) & 1) << point
        for point in range(1 << N_INPUTS)
    )


def write_seed(graph: XAG, path: Path) -> None:
    lines = ["# exact affine-substituted XAG"]
    lines.extend(f"AND {node.left_affine_mask} {node.right_affine_mask}" for node in graph.and_nodes)
    lines.append(f"OUTPUT {graph.output_affine_mask}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    rng = random.Random(20260910)
    base_rows = [1 << i for i in range(N_INPUTS)]
    records = []
    seed_dir = ROOT / "artifacts/multiplicative_depth/affine/shared_rank"
    seed_dir.mkdir(parents=True, exist_ok=True)
    for trial in range(129):
        rows = base_rows[:]
        offset = 0
        for _ in range(trial):
            operation = rng.randrange(3)
            a, b = rng.sample(range(N_INPUTS), 2)
            if operation == 0:
                rows[a] ^= rows[b]
            elif operation == 1:
                rows[a], rows[b] = rows[b], rows[a]
            else:
                offset ^= 1 << a
        graph = transformed_graph(rows, offset)
        target = transformed_target(rows, offset)
        seed = seed_dir / f"seed_{trial:03d}.xag"
        write_seed(graph, seed)
        truth = seed.with_suffix(".hex")
        truth.write_text(target.to_bytes(512, "little").hex() + "\n")
        result = subprocess.run(
            [str(TOOL), str(truth), str(seed), "balance"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        tool_result = json.loads(result.stdout)
        records.append({
            "trial": trial,
            "rows": rows,
            "offset": offset,
            "seed": str(seed.relative_to(ROOT)),
            "source_exact": graph.exact(target),
            "source_metrics": graph.metrics(target),
            "tool": tool_result,
        })
    exact = [r for r in records if r["tool"]["exact_after"]]
    best = min(exact, key=lambda r: (
        r["tool"]["md_after"],
        max(r["tool"]["and_layer_widths_after"]),
        r["tool"]["and_count_after"],
    ))
    out = {
        "seed": 20260910,
        "trials": len(records),
        "target_truth_table_sha256": truth_table_sha256(logo_truth_table()),
        "all_source_exact": all(r["source_exact"] for r in records),
        "all_tool_results_exact": len(exact) == len(records),
        "best": best,
        "records": records,
    }
    path = ROOT / "artifacts/multiplicative_depth/affine/shared_rank_search.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("seed", "trials", "all_source_exact", "all_tool_results_exact", "best")}, indent=2))


if __name__ == "__main__":
    main()
