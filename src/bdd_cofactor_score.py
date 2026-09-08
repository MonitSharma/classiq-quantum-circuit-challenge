"""Score reversible compute/uncompute of BDD cofactors on their input support."""

import itertools
import json
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from search import esop, mcxr

ORDER = [0, 1, 5, 2, 3, 4, 11, 10, 9, 8, 6, 7]


def support_truth(record):
    support = record["support"]
    mask = int(record["truth_mask"], 16)
    table = 0
    for values in itertools.product((0, 1), repeat=len(support)):
        bits = [0] * 12
        for qubit, value in zip(support, values):
            bits[ORDER.index(qubit)] = value
        full_index = 0
        for bit in bits:
            full_index = (full_index << 1) | bit
        if (mask >> full_index) & 1:
            table |= 1 << sum(value << i for i, value in enumerate(values))
    return table


def mapped_pred(table, support, target=12):
    q = QuantumCircuit(18)
    scratch = [wire for wire in range(13, 18) if wire != target]
    for cube_mask, cube_value in esop(table, len(support)):
        controls = [support[i] for i in range(len(support)) if cube_mask >> i & 1]
        negative = [support[i] for i in range(len(support))
                    if cube_mask >> i & 1 and not (cube_value >> i & 1)]
        if negative:
            q.x(negative)
        mcxr(q, controls, target, scratch)
        if negative:
            q.x(negative)
    return q


def main():
    inventory = json.loads(Path("artifacts/bdd_cofactor_inventory.json").read_text())
    rows = []
    for index, record in enumerate(inventory["cofactors"]):
        if record["support_size"] > 6:
            continue
        table = support_truth(record)
        compute = mapped_pred(table, record["support"])
        circuit = compute.copy()
        circuit.z(12)
        circuit.compose(compute.inverse(), inplace=True)
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3)
        rows.append({
            "inventory_index": index,
            "support": record["support"],
            "support_size": record["support_size"],
            "ones": record["ones"],
            "esop_cubes": len(esop(table, record["support_size"])),
            "compute_uncompute_depth": compiled.depth(),
            "compute_uncompute_cx": compiled.count_ops().get("cx", 0),
        })
    rows.sort(key=lambda row: (row["compute_uncompute_depth"], row["compute_uncompute_cx"]))
    Path("artifacts/bdd_cofactor_scores.json").write_text(json.dumps(rows, indent=2))
    print(json.dumps({"scored": len(rows), "best": rows[:20]}, indent=2))


if __name__ == "__main__":
    main()
