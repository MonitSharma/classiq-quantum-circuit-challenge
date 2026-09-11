"""Reproduce the best bounded phase-tap order and verified cleanup result."""

import json
from pathlib import Path

from qiskit import qasm2, transpile
from pytket.passes import FullPeepholeOptimise
from pytket.qasm import circuit_from_qasm_str, circuit_to_qasm_str
from pytket.circuit import OpType

from xag import build


ROOT = Path(__file__).resolve().parents[1]
ORDER = [5, 2, 0, 9, 7, 3, 8, 4, 1, 6]


def main() -> None:
    terms = json.loads((ROOT / "artifacts/rank_terms.json").read_text())
    circuit, _, _ = build(terms, order=ORDER, clear_each=True)
    lowered = transpile(circuit, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    raw = ROOT / "artifacts/multiplicative_depth/md_rank_order_stream.qasm"
    raw.write_text(qasm2.dumps(lowered))
    optimized = circuit_from_qasm_str(raw.read_text())
    FullPeepholeOptimise().apply(optimized)
    out = ROOT / "artifacts/multiplicative_depth/md_rank_order_stream_pytket.qasm"
    out.write_text(circuit_to_qasm_str(optimized))
    print({"order": ORDER, "depth": optimized.depth(), "cx_count": optimized.n_gates_of_type(OpType.CX), "qasm": str(out)})


if __name__ == "__main__":
    main()
