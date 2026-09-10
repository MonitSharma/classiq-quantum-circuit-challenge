"""Build an exact phase-history oracle from the ten verified rank products.

Each block computes one x factor and one y factor into q12/q13, computes their
product into q14, deposits Z on q14, and then exactly clears the block. The
blocks therefore form an identity computational trajectory with the desired
logo phase accumulated in history. This is a correctness baseline for the
new route, not yet a depth-optimized construction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from search import pred


ROOT = Path(__file__).resolve().parents[1]
TERMS = ROOT / "artifacts" / "rank_terms.json"


def build(terms_path: Path = TERMS) -> QuantumCircuit:
    terms = json.loads(terms_path.read_text())
    circuit = QuantumCircuit(18)
    for x_table, y_table in terms:
        x_compute = pred(x_table, 0, 12, [13, 14, 15, 16, 17])
        y_compute = pred(y_table, 6, 13, [14, 15, 16, 17])
        circuit.compose(x_compute, inplace=True)
        circuit.compose(y_compute, inplace=True)
        circuit.rccx(12, 13, 14)
        circuit.z(14)
        circuit.rccx(12, 13, 14)
        circuit.compose(y_compute.inverse(), inplace=True)
        circuit.compose(x_compute.inverse(), inplace=True)
    return circuit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms", type=Path, default=TERMS)
    parser.add_argument(
        "--out", type=Path,
        default=Path("artifacts/phase_history/rank_product_seed.qasm"),
    )
    args = parser.parse_args()
    compiled = transpile(
        build(args.terms), basis_gates=["u3", "cx"],
        qubits_initially_zero=False, optimization_level=3,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(compiled))
    print(json.dumps({
        "qasm": str(args.out),
        "depth": compiled.depth(),
        "cx_count": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "terms": len(json.loads(args.terms.read_text())),
        "terms_path": str(args.terms),
        "qubits_initially_zero": False,
    }, indent=2))


if __name__ == "__main__":
    main()
