"""Transposed four-bit loader for ordered x-column pairs."""

import json
import random
from collections import OrderedDict
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from search import logo


CONTROLS = list(range(0, 5))
TARGETS = list(range(12, 16))


def column_mask(x: int) -> int:
    return sum(1 << y for y in range(64) if logo(x, y))


def column_codes():
    classes = OrderedDict()
    z_codes = {}
    for z in range(32):
        pair = (column_mask(z), column_mask(z + 32))
        class_index = classes.setdefault(pair, len(classes))
        z_codes[z] = class_index
    return {
        "class_count": len(classes),
        "z_to_code": {str(z): code for z, code in z_codes.items()},
        "class_masks": [
            {"lower_mask": pair[0], "upper_mask": pair[1]}
            for pair in classes
        ],
    }


def tables_from_codes(codes):
    z_codes = {int(z): int(code) for z, code in codes["z_to_code"].items()}
    return [sum(((z_codes[z] >> bit) & 1) << z for z in range(32))
            for bit in range(4)]


def build(tables, seed=0):
    n = 5
    count = 1 << n
    rng = random.Random(seed)
    base = list(range(n))
    rng.shuffle(base)
    orders = [base[s % n:] + base[:s % n] for s in range(len(tables))]
    coefficients = []
    for table, order in zip(tables, orders):
        values = np.array([
            np.pi * ((table >> sum(((k >> j) & 1) << v
                                   for j, v in enumerate(order))) & 1)
            for k in range(count)
        ])
        h = 1
        while h < count:
            for i in range(0, count, 2 * h):
                low = values[i:i + h].copy()
                high = values[i + h:i + 2 * h].copy()
                values[i:i + h] = low + high
                values[i + h:i + 2 * h] = low - high
            h *= 2
        coefficients.append(values / count)
    circuit = QuantumCircuit(18)
    for index in range(count):
        for coefficient, target in zip(coefficients, TARGETS):
            angle = float(coefficient[index ^ (index >> 1)])
            if abs(angle) > 1e-14:
                circuit.ry(angle, target)
        position = ((index + 1) & -(index + 1)).bit_length() - 1 \
            if index < count - 1 else n - 1
        for order, target in zip(orders, TARGETS):
            circuit.cx(CONTROLS[order[position]], target)
    return circuit


def compile_loader(tables, seed=0):
    return transpile(build(tables, seed), basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def write_artifacts(directory="artifacts/three_sweep/column_pair_loader"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    codes = column_codes()
    (directory / "column_pair_codes.json").write_text(json.dumps(codes, indent=2) + "\n")
    tables = tables_from_codes(codes)
    results = []
    for seed in range(32):
        circuit = compile_loader(tables, seed)
        path = directory / f"loader4_seed{seed}.qasm"
        path.write_text(qasm2.dumps(circuit))
        results.append({"seed": seed, "depth": circuit.depth(),
                        "cx_count": circuit.count_ops().get("cx", 0),
                        "width": circuit.num_qubits, "qasm": str(path)})
    results.sort(key=lambda row: (row["depth"], row["cx_count"], row["seed"]))
    report = {"class_count": codes["class_count"], "results": results}
    (directory / "screen.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"best": results[0], "worst_depth": max(r["depth"] for r in results)}, indent=2))
    return report


if __name__ == "__main__":
    write_artifacts()
