"""Deterministic local refinement of the clean-ancilla assignment search."""
import itertools
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit
from ancilla_assignment_search import remap_ancillas, ORDER


def lower(blocks, assignments):
    circuit = QuantumCircuit(18)
    for index in ORDER:
        circuit.compose(remap_ancillas(blocks[index], assignments[index]), inplace=True)
    return transpile(circuit, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def main():
    terms = json.loads(Path("artifacts/pair_terms.json").read_text())
    blocks = [pair_circuit(x, y) for x, y in terms]
    seed = json.loads(Path("artifacts/ancilla_assignment_search.json").read_text())
    assignments = [tuple(row) for row in seed["assignments"]]
    best = lower(blocks, assignments)
    history = [{"round": -1, "depth": best.depth(),
                "cx": best.count_ops().get("cx", 0), "assignments": assignments}]
    for round_index in range(4):
        improved = False
        for block_index in range(len(blocks)):
            trials = []
            for left, right in itertools.combinations(range(6), 2):
                candidate = assignments.copy()
                permutation = list(candidate[block_index])
                permutation[left], permutation[right] = permutation[right], permutation[left]
                candidate[block_index] = tuple(permutation)
                lowered = lower(blocks, candidate)
                trials.append((lowered.depth(), lowered.count_ops().get("cx", 0),
                               left, right, candidate, lowered))
            winner = min(trials, key=lambda row: (row[0], row[1]))
            if (winner[0], winner[1]) < (best.depth(), best.count_ops().get("cx", 0)):
                assignments = winner[4]
                best = winner[5]
                improved = True
                history.append({"round": round_index, "block": block_index,
                                "swap": [winner[2], winner[3]], "depth": best.depth(),
                                "cx": best.count_ops().get("cx", 0),
                                "assignments": assignments})
                print(history[-1], flush=True)
        if not improved:
            break
    directory = Path("artifacts/732")
    directory.mkdir(exist_ok=True)
    output = directory / "ancilla_assignment_732.qasm"
    output.write_text(qasm2.dumps(best))
    result = {"depth": best.depth(), "cx": best.count_ops().get("cx", 0),
              "width": best.num_qubits, "order": ORDER,
              "assignments": assignments, "history": history, "qasm": str(output)}
    Path("artifacts/ancilla_assignment_descent.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ("depth", "cx", "width", "assignments")}, indent=2))


if __name__ == "__main__":
    main()
