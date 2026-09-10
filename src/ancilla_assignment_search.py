"""Search independent clean-ancilla relabelings for the fixed 753 order."""
import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit

ORDER = [9, 7, 1, 2, 5, 4, 8, 0, 6, 3]
TRIALS = 400


def remap_ancillas(circuit, permutation):
    out = QuantumCircuit(18)
    for instruction in circuit.data:
        indices = [circuit.find_bit(bit).index for bit in instruction.qubits]
        indices = [index if index < 12 else permutation[index - 12] for index in indices]
        out.append(instruction.operation, [out.qubits[index] for index in indices])
    return out


def score(blocks, assignments):
    circuit = QuantumCircuit(18)
    for index in ORDER:
        circuit.compose(remap_ancillas(blocks[index], assignments[index]), inplace=True)
    lowered = transpile(circuit, basis_gates=["u3", "cx"],
                        qubits_initially_zero=False, optimization_level=3)
    return lowered


def main():
    terms = json.loads(Path("artifacts/pair_terms.json").read_text())
    blocks = [pair_circuit(x, y) for x, y in terms]
    identity = tuple(range(12, 18))
    assignments = [identity] * len(blocks)
    best = score(blocks, assignments)
    best_assignments = assignments
    rng = random.Random(20260909)
    history = [{"trial": -1, "depth": best.depth(),
                "cx": best.count_ops().get("cx", 0), "assignments": assignments}]
    for trial in range(TRIALS):
        candidate_assignments = [tuple(rng.sample(range(12, 18), 6)) for _ in blocks]
        candidate = score(blocks, candidate_assignments)
        if (candidate.depth(), candidate.count_ops().get("cx", 0)) < \
                (best.depth(), best.count_ops().get("cx", 0)):
            best = candidate
            best_assignments = candidate_assignments
            history.append({"trial": trial, "depth": best.depth(),
                            "cx": best.count_ops().get("cx", 0),
                            "assignments": best_assignments})
            print(history[-1], flush=True)
    directory = Path("artifacts/739")
    directory.mkdir(exist_ok=True)
    output = directory / "ancilla_assignment_739.qasm"
    output.write_text(qasm2.dumps(best))
    metadata = {"order": ORDER, "trials": TRIALS,
                "depth": best.depth(), "cx": best.count_ops().get("cx", 0),
                "width": best.num_qubits, "assignments": best_assignments,
                "history": history, "qasm": str(output)}
    Path("artifacts/ancilla_assignment_search.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps({k: metadata[k] for k in ("depth", "cx", "width", "assignments")}, indent=2))


if __name__ == "__main__":
    main()
