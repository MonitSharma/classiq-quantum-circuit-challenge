"""Apply a bounded pytket peephole rewrite, then restore the scored basis.

The input must be a standalone oracle QASM.  The final artifact is always
re-lowered by Qiskit to the challenge's required u3/cx basis with arbitrary
input wires preserved during transpilation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pytket import OpType
from pytket.passes import FullPeepholeOptimise
from pytket.qasm import circuit_from_qasm, circuit_to_qasm_str
from qiskit import qasm2, transpile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-qasm", type=Path, required=True)
    parser.add_argument("--out-qasm", type=Path, required=True)
    parser.add_argument("--out-metrics", type=Path, required=True)
    args = parser.parse_args()

    input_bytes = args.input_qasm.read_bytes()
    circuit = circuit_from_qasm(str(args.input_qasm))
    input_stats = {
        "depth": circuit.depth(),
        "gate_count": circuit.n_gates,
        "cx_count": circuit.n_gates_of_type(OpType.CX),
    }
    FullPeepholeOptimise().apply(circuit)
    rewritten_stats = {
        "depth": circuit.depth(),
        "gate_count": circuit.n_gates,
        "cx_count": circuit.n_gates_of_type(OpType.CX),
    }

    lowered = qasm2.loads(circuit_to_qasm_str(circuit))
    final = transpile(
        lowered,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=0,
    )
    args.out_qasm.parent.mkdir(parents=True, exist_ok=True)
    args.out_qasm.write_text(qasm2.dumps(final))
    metrics = {
        "input_qasm": str(args.input_qasm),
        "input_qasm_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "rewrite": "pytket.FullPeepholeOptimise",
        "input_pytket": input_stats,
        "rewritten_pytket": rewritten_stats,
        "compiled_forward_depth": final.depth(),
        "compiled_forward_cx": final.count_ops().get("cx", 0),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
            "seed_transpiler": 0,
        },
        "oracle_qasm_sha256": hashlib.sha256(args.out_qasm.read_bytes()).hexdigest(),
    }
    args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
    args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
