"""Apply bounded global pytket rewrites and retain the best exact U3/CX result."""
import json
import tempfile
from pathlib import Path

from pytket.qasm import circuit_from_qasm, circuit_to_qasm
from pytket.passes import CliffordSimp, FullPeepholeOptimise
from qiskit import QuantumCircuit, qasm2, transpile


def lower(path, pass_type):
    circuit = circuit_from_qasm(str(path))
    pass_type().apply(circuit)
    with tempfile.NamedTemporaryFile(suffix=".qasm") as handle:
        circuit_to_qasm(circuit, handle.name)
        qiskit_circuit = QuantumCircuit.from_qasm_file(handle.name)
    return transpile(qiskit_circuit, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def main():
    source = Path("artifacts/732/ancilla_assignment_732.qasm")
    candidates = [(name, lower(source, pass_type)) for name, pass_type in
                  (("full_peephole", FullPeepholeOptimise),
                   ("clifford_simp", CliffordSimp))]
    name, best = min(candidates, key=lambda item: (item[1].depth(),
                                                    item[1].count_ops().get("cx", 0)))
    directory = Path("artifacts/718")
    directory.mkdir(exist_ok=True)
    output = directory / "tket_ancilla_assignment_718.qasm"
    output.write_text(qasm2.dumps(best))
    result = {"source": str(source), "pass": name, "depth": best.depth(),
              "cx": best.count_ops().get("cx", 0), "width": best.num_qubits,
              "qasm": str(output),
              "candidates": [{"pass": label, "depth": circuit.depth(),
                              "cx": circuit.count_ops().get("cx", 0),
                              "width": circuit.num_qubits}
                             for label, circuit in candidates]}
    Path("artifacts/tket_global_optimize.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
