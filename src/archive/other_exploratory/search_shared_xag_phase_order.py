"""Search term orders for the shared target-guided XAG phase builder."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from qiskit import qasm2, transpile

from xag import build


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", type=Path, default=Path("artifacts/rank_terms.json"))
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    terms = json.loads(args.terms.read_text())
    rng = random.Random(args.seed)
    orders = [list(range(len(terms)))]
    for _ in range(max(0, args.trials - 1)):
        order = list(range(len(terms)))
        rng.shuffle(order)
        orders.append(order)

    best = None
    records = []
    for trial, order in enumerate(orders):
        try:
            raw, _, _ = build(terms, order=order)
        except ValueError as exc:
            records.append({"trial": trial, "order": order, "status": str(exc)})
            continue
        compiled = transpile(
            raw,
            basis_gates=["u3", "cx"],
            qubits_initially_zero=False,
            optimization_level=3,
        )
        record = {
            "trial": trial,
            "order": order,
            "depth": compiled.depth(),
            "cx_count": compiled.count_ops().get("cx", 0),
            "width": compiled.num_qubits,
        }
        records.append(record)
        if best is None or (record["depth"], record["cx_count"]) < (
            best["depth"], best["cx_count"]
        ):
            best = record | {"circuit": compiled}
            print(json.dumps({k: v for k, v in best.items() if k != "circuit"}), flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(best.pop("circuit")))
    args.out.with_suffix(".metrics.json").write_text(
        json.dumps(
            {
                "source_terms": str(args.terms),
                "seed": args.seed,
                "trials": args.trials,
                "best": best,
                "records": records,
                "qubits_initially_zero": False,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
