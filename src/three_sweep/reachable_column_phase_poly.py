"""Reachable-state parity phase sharing for the transposed 4-bit loader."""

import json
from pathlib import Path

import numpy as np
from scipy.linalg import qr
from qiskit import qasm2, transpile

from search import logo
from .column_pair_loader import build as build_loader, column_codes, tables_from_codes
from .reachable_phase_poly import synth_exact


WIRES = list(range(6, 12)) + [5] + list(range(12, 16))


def side_basis(codes):
    return [(code, x5) for code in range(codes["class_count"]) for x5 in (0, 1)]


def coefficients(codes):
    side = side_basis(codes)
    side_values = [code | (x5 << 4) for code, x5 in side]
    matrix = np.array([[(-1) ** ((value & feature).bit_count())
                        for feature in range(32)] for value in side_values], float)
    _, _, pivots = qr(matrix, mode="economic", pivoting=True)
    basis = [int(x) for x in pivots[:len(side)]]
    basis_matrix = matrix[:, basis]
    z_for = {int(codes["z_to_code"][str(z)]): z for z in range(32)}
    terms = {}
    for py in range(64):
        target = []
        for code, x5 in side:
            x = z_for[code] + (x5 << 5)
            target.append(sum(int(logo(x, y)) * ((-1) ** ((py & y).bit_count()))
                              for y in range(64)) / 64.0)
        solution = np.linalg.solve(basis_matrix, np.array(target))
        for feature, value in zip(basis, solution):
            # Poly order is y0..y5, x5, then four code bits.
            mask = py | ((feature & 0x0F) << 7) | (((feature >> 4) & 1) << 6)
            if abs(value) > 1e-10:
                terms[mask] = float(value)
    return terms


def build(seed=19, section_size=1):
    codes = column_codes()
    terms = coefficients(codes)
    masks = list(terms)
    columns = [[(mask >> row) & 1 for mask in masks] for row in range(11)]
    angles = [-2 * np.pi * terms[mask] for mask in masks]
    poly = synth_exact(columns, angles, section_size=section_size)
    poly.global_phase = np.pi * sum(terms.values())
    loader = build_loader(tables_from_codes(codes), seed)
    circuit = loader.copy()
    circuit.compose(poly, qubits=WIRES, inplace=True)
    circuit.compose(loader.inverse(), inplace=True)
    return transpile(circuit, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed), terms


def write(seed=19, section_size=1, path="artifacts/three_sweep/reachable_column_phase_poly.qasm"):
    circuit, terms = build(seed, section_size)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    report = {"seed": seed, "section_size": section_size, "qasm": str(path), "phase_terms": len(terms),
              "depth": circuit.depth(), "cx_count": circuit.count_ops().get("cx", 0),
              "width": circuit.num_qubits}
    path.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    write()
