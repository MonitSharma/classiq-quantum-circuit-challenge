"""Reachable-state phase polynomial with exact numeric phase angles.

Qiskit's bundled GraySynth helper reduces numeric phase angles modulo pi. That
is unsuitable for the real Walsh coefficients of a Boolean exponent, so this
module retains its parity-network algorithm but emits the numeric P angles
without that reduction.
"""

import copy
import json
from pathlib import Path

import numpy as np
from scipy.linalg import qr
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis.linear import synth_cnot_count_full_pmh

from search import logo
from .half_row_loader import build as build_loader, half_codes, tables_from_codes


WIRES = list(range(6)) + [11] + list(range(12, 18))


def synth_exact(cnots, angles, section_size=2):
    num_qubits = len(cnots)
    qcir = QuantumCircuit(num_qubits)
    if len(cnots[0]) != len(angles):
        raise ValueError("parity/angle size mismatch")
    range_list = list(range(num_qubits))
    epsilon = num_qubits
    sta = []
    cnots_copy = np.transpose(np.array(copy.deepcopy(cnots)))
    state = np.eye(num_qubits).astype("int")
    angles = list(angles)
    labels = list(range(len(angles)))
    for qubit in range(num_qubits):
        index = 0
        for icnots in cnots_copy:
            if np.array_equal(icnots, state[qubit]):
                qcir.p(float(angles[index]), qubit)
                del angles[index]
                del labels[index]
                cnots_copy = np.delete(cnots_copy, index, axis=0)
                if index == len(cnots_copy):
                    break
                index -= 1
            index += 1
    sta.append([cnots, range_list, epsilon])
    while sta:
        cnots, ilist, qubit = sta.pop()
        if not cnots:
            continue
        if 0 <= qubit < num_qubits:
            condition = True
            while condition:
                condition = False
                for j in range(num_qubits):
                    if j != qubit and sum(cnots[j]) == len(cnots[j]):
                        condition = True
                        qcir.cx(j, qubit)
                        state[qubit] ^= state[j]
                        index = 0
                        for icnots in cnots_copy:
                            if np.array_equal(icnots, state[qubit]):
                                qcir.p(float(angles[index]), qubit)
                                del angles[index]
                                del labels[index]
                                cnots_copy = np.delete(cnots_copy, index, axis=0)
                                if index == len(cnots_copy):
                                    break
                                index -= 1
                            index += 1
                        for item in _remove_duplicates(sta + [[cnots, ilist, qubit]]):
                            cnots_p, _, _ = item
                            if not cnots_p:
                                continue
                            for t in range(len(cnots_p[j])):
                                cnots_p[j][t] ^= cnots_p[qubit][t]
        if not ilist:
            continue
        j = ilist[np.argmax([[max(row.count(0), row.count(1)) for row in cnots][k]
                             for k in ilist])]
        cnots0 = []
        cnots1 = []
        for y in list(map(list, zip(*cnots))):
            (cnots0 if y[j] == 0 else cnots1).append(y)
        cnots0 = list(map(list, zip(*cnots0))) if cnots0 else []
        cnots1 = list(map(list, zip(*cnots1))) if cnots1 else []
        if qubit == epsilon:
            sta.append([cnots1, list(set(ilist).difference([j])), j])
        else:
            sta.append([cnots1, list(set(ilist).difference([j])), qubit])
        sta.append([cnots0, list(set(ilist).difference([j])), qubit])
    qcir &= synth_cnot_count_full_pmh(state, section_size).inverse()
    if angles:
        print("unplaced phase labels", [labels[i] for i in range(len(labels))], flush=True)
    return qcir


def _remove_duplicates(items):
    unique = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return unique


def side_basis(codes):
    classes = []
    for z in range(32):
        code = int(codes["z_to_lower_code"][str(z)]) | (int(codes["z_to_upper_code"][str(z)]) << 3)
        if code not in classes:
            classes.append(code)
    return [(code, b) for code in classes for b in (0, 1)]


def coefficients(codes):
    side = side_basis(codes)
    side_bits = [code | (b << 6) for code, b in side]
    matrix = np.array([[(-1) ** ((value & feature).bit_count())
                        for feature in range(128)] for value in side_bits], float)
    _, _, pivots = qr(matrix, mode="economic", pivoting=True)
    basis = [int(x) for x in pivots[:len(side)]]
    basis_matrix = matrix[:, basis]
    z_for = {}
    for z in range(32):
        code = int(codes["z_to_lower_code"][str(z)]) | (int(codes["z_to_upper_code"][str(z)]) << 3)
        z_for.setdefault(code, z)
    out = {}
    for px in range(64):
        target = []
        for code, b in side:
            z = z_for[code]
            target.append(sum(int(logo(x, z + 32 * b)) *
                              ((-1) ** ((px & x).bit_count()))
                              for x in range(64)) / 64.0)
        solution = np.linalg.solve(basis_matrix, np.array(target))
        for feature, value in zip(basis, solution):
            # The side basis is encoded as code bits 0..5 plus y5 at bit 6,
            # while poly-wire order is x0..x5, y5, then six code bits.
            mask = px | ((feature & 0x3F) << 7) | (((feature >> 6) & 1) << 6)
            if abs(value) > 1e-10:
                out[mask] = float(value)
    return out


def build(seed=0):
    codes = half_codes()
    terms = coefficients(codes)
    masks = [mask for mask in terms if mask != 0]
    columns = [[(mask >> row) & 1 for mask in masks] for row in range(13)]
    angles = [-2 * np.pi * terms[mask] for mask in masks]
    poly = synth_exact(columns, angles, section_size=1)
    poly.global_phase = np.pi * sum(terms.values())
    loader = build_loader(tables_from_codes(codes), seed)
    circuit = loader.copy()
    circuit.compose(poly, qubits=WIRES, inplace=True)
    circuit.compose(loader.inverse(), inplace=True)
    return transpile(circuit, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed), terms


def write(seed=0, path="artifacts/three_sweep/reachable_phase_poly.qasm"):
    circuit, terms = build(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    report = {"seed": seed, "qasm": str(path), "phase_terms": len(terms),
              "depth": circuit.depth(), "cx_count": circuit.count_ops().get("cx", 0),
              "width": circuit.num_qubits}
    path.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    write()
