"""3+3 half-row code loader for the secondary three-sweep experiment."""

import json
import random
from collections import OrderedDict
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit import qasm2, transpile

from search import logo


CONTROLS = list(range(6, 11))
TARGETS = list(range(12, 18))


def row_mask(y: int) -> int:
    return sum(1 << x for x in range(64) if logo(x, y))


def half_codes():
    classes = [OrderedDict(), OrderedDict()]
    z_codes = [{}, {}]
    for half in (0, 1):
        for z in range(32):
            mask = row_mask(z + 32 * half)
            if mask not in classes[half]:
                classes[half][mask] = len(classes[half])
            z_codes[half][z] = classes[half][mask]
    return {
        "lower_class_count": len(classes[0]),
        "upper_class_count": len(classes[1]),
        "z_to_lower_code": {str(z): code for z, code in z_codes[0].items()},
        "z_to_upper_code": {str(z): code for z, code in z_codes[1].items()},
        "lower_masks": [mask for mask in classes[0]],
        "upper_masks": [mask for mask in classes[1]],
    }


def tables_from_codes(data: dict) -> list[int]:
    lower = {int(z): int(code) for z, code in data["z_to_lower_code"].items()}
    upper = {int(z): int(code) for z, code in data["z_to_upper_code"].items()}
    return [
        sum(((lower[z] >> bit) & 1) << z for z in range(32))
        for bit in range(3)
    ] + [
        sum(((upper[z] >> bit) & 1) << z for z in range(32))
        for bit in range(3)
    ]


def build(tables: list[int], seed: int = 0):
    if len(tables) != 6:
        raise ValueError("expected six Boolean tables")
    n = len(CONTROLS)
    count = 1 << n
    rng = random.Random(seed)
    base = list(range(n))
    rng.shuffle(base)
    shifts = list(range(n))
    rng.shuffle(shifts)
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


def compile_loader(tables: list[int], seed: int = 0):
    return transpile(
        build(tables, seed),
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=seed,
    )


def write_artifacts(directory="artifacts/three_sweep/half_row_loader"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    codes = half_codes()
    (directory / "half_row_codes.json").write_text(json.dumps(codes, indent=2) + "\n")
    tables = tables_from_codes(codes)
    results = []
    for seed in range(32):
        circuit = compile_loader(tables, seed)
        path = directory / f"loader33_seed{seed}.qasm"
        path.write_text(qasm2.dumps(circuit))
        results.append({
            "seed": seed,
            "depth": circuit.depth(),
            "cx_count": circuit.count_ops().get("cx", 0),
            "width": circuit.num_qubits,
            "qasm": str(path),
        })
    results.sort(key=lambda row: (row["depth"], row["cx_count"], row["seed"]))
    report = {
        "lower_class_count": codes["lower_class_count"],
        "upper_class_count": codes["upper_class_count"],
        "results": results,
    }
    (directory / "screen.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"best": results[0], "worst_depth": max(r["depth"] for r in results)}, indent=2))
    return report


if __name__ == "__main__":
    write_artifacts()
