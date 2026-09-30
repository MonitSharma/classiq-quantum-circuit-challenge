"""Bounded safe post-processing for the verified disjoint candidate."""

import json
import tempfile
from pathlib import Path

from pytket.passes import CliffordSimp
from pytket.qasm import circuit_from_qasm, circuit_to_qasm
from qiskit import QuantumCircuit, qasm2, transpile


def build(source: Path = Path("artifacts/disjoint_shared_rectangle_candidate.qasm")):
    circuit = circuit_from_qasm(str(source))
    CliffordSimp().apply(circuit)
    with tempfile.NamedTemporaryFile(suffix=".qasm") as handle:
        circuit_to_qasm(circuit, handle.name)
        q = QuantumCircuit.from_qasm_file(handle.name)
    return transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)


def main() -> None:
    q = build()
    path = Path("artifacts/disjoint_postprocessed_649.qasm")
    path.write_text(qasm2.dumps(q))
    result = {
        "source": str(Path("artifacts/disjoint_shared_rectangle_candidate.qasm").resolve()),
        "pass": "pytket.CliffordSimp + Qiskit optimization_level=3",
        "depth": q.depth(),
        "cx_count": q.count_ops().get("cx", 0),
        "width": q.num_qubits,
        "qasm": str(path.resolve()),
    }
    Path("artifacts/disjoint_postprocess_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
