"""Try deterministic Qiskit native reserializations of the protected oracle.

The protected QASM is read-only input. Every output is written under a new
name and must be exhaustively verified before it can be considered useful.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import qasm2, transpile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("artifacts/524/full_mux_feature_linear_tket_524.qasm"),
    )
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source = qasm2.load(str(args.source))
    best = None
    records = []
    for seed in range(args.seeds):
        candidate = transpile(
            source,
            basis_gates=["u3", "cx"],
            qubits_initially_zero=False,
            optimization_level=3,
            seed_transpiler=seed,
        )
        record = {
            "seed": seed,
            "depth": candidate.depth(),
            "cx_count": candidate.count_ops().get("cx", 0),
            "width": candidate.num_qubits,
        }
        records.append(record)
        if best is None or (record["depth"], record["cx_count"]) < (
            best["depth"], best["cx_count"]
        ):
            best = record | {"circuit": candidate}
            print(json.dumps({k: v for k, v in best.items() if k != "circuit"}), flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(best.pop("circuit")))
    args.out.with_suffix(".metrics.json").write_text(
        json.dumps(
            {
                "source": str(args.source),
                "seeds": args.seeds,
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
