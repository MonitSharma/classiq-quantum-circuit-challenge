"""Compile a direct-output ESOP loader with dirty output accumulators.

Unlike the q17 compute/fanout/uncompute loader, each shared ANF cube toggles
its output targets directly.  Other output wires are restored dirty ancillas
for relative-phase MCX synthesis.  The loader is intended to be paired with
its exact inverse around a diagonal phase computation; its classical output
bits are exact, while its internal relative phase need not be global.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit_aer import AerSimulator
from qiskit.synthesis import synth_mcx_n_dirty_i15, synth_mcx_noaux_v24

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows
from vector_input_basis_search import INPUT_MATRIX, INPUT_OFFSET, invert, transform_y

Y = [6 + bit for bit in range(6)]
OUT = [12 + bit for bit in range(5)]


def matrix_ops(matrix: tuple[int, ...]) -> list[tuple[int, int]]:
    rows = list(matrix)
    reduce_ops: list[tuple[int, int]] = []
    for bit in range(6):
        pivot = next(i for i in range(bit, 6) if rows[i] & (1 << bit))
        if pivot != bit:
            reduce_ops.extend([(pivot, bit), (bit, pivot), (pivot, bit)])
            rows[pivot], rows[bit] = rows[bit], rows[pivot]
        for i in range(6):
            if i != bit and rows[i] & (1 << bit):
                reduce_ops.append((bit, i))
                rows[i] ^= rows[bit]
    return list(reversed(reduce_ops))


def apply_matrix(q: QuantumCircuit, matrix: tuple[int, ...]) -> None:
    for control, target in matrix_ops(matrix):
        q.cx(Y[control], Y[target])


def transformed_tables() -> dict[str, list[int]]:
    original = {name: [row[name] for row in truth_rows()] for name in FEATURES}
    inv = invert(INPUT_MATRIX)
    return {
        name: [original[name][transform_y(z, inv, INPUT_OFFSET)] for z in range(64)]
        for name in FEATURES
    }


def append_target_mcx(q: QuantumCircuit, controls: list[int], target: int) -> None:
    degree = len(controls)
    if degree == 0:
        q.x(target)
    elif degree == 1:
        q.cx(controls[0], target)
    elif degree == 2:
        q.rccx(controls[0], controls[1], target)
    elif degree == 3:
        q.compose(synth_mcx_noaux_v24(degree),
                  qubits=controls + [target], inplace=True)
    else:
        ancillas = [wire for wire in OUT if wire != target][: degree - 2]
        q.compose(synth_mcx_n_dirty_i15(degree, relative_phase=True),
                  qubits=controls + [target] + ancillas, inplace=True)


def build() -> QuantumCircuit:
    tables = transformed_tables()
    masks: defaultdict[int, list[int]] = defaultdict(list)
    for output, name in enumerate(FEATURES):
        for monomial in anf_monomials(tables[name]):
            masks[monomial].append(output)

    q = QuantumCircuit(18)
    apply_matrix(q, INPUT_MATRIX)
    for bit in range(6):
        if INPUT_OFFSET & (1 << bit):
            q.x(Y[bit])
    for monomial in sorted(masks):
        controls = [Y[bit] for bit in range(6) if monomial & (1 << bit)]
        for output in masks[monomial]:
            append_target_mcx(q, controls, OUT[output])
    for bit in range(6):
        if INPUT_OFFSET & (1 << bit):
            q.x(Y[bit])
    apply_matrix(q, invert(INPUT_MATRIX))
    return q


def verify(compiled: QuantumCircuit) -> int:
    simulator = AerSimulator(method="statevector")
    phases: list[complex] = []
    for row in truth_rows():
        circuit = QuantumCircuit(18)
        for bit in range(6):
            if (row["y"] >> bit) & 1:
                circuit.x(6 + bit)
        circuit.compose(compiled, inplace=True)
        circuit.save_statevector()
        state = simulator.run(circuit, shots=1).result().get_statevector()
        support = np.flatnonzero(np.abs(state) > 1e-7)
        if len(support) != 1:
            raise AssertionError((row["y"], "support", len(support)))
        index = int(support[0])
        actual_y = sum(((index >> (6 + bit)) & 1) << bit for bit in range(6))
        actual_out = [(index >> (12 + bit)) & 1 for bit in range(5)]
        wanted = [row[name] for name in FEATURES]
        if actual_y != row["y"] or actual_out != wanted or (index >> 17) & 1:
            raise AssertionError((row["y"], actual_y, actual_out, wanted, index))
        phases.append(complex(state[index]))
    normalized = {complex(round((p / abs(p)).real, 7),
                           round((p / abs(p)).imag, 7)) for p in phases}
    return len(normalized)


def main() -> None:
    raw = build()
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3)
    phase_classes = verify(compiled)
    path = ARTIFACTS / "vector_input_basis_direct_target_loader.qasm"
    path.write_text(qasm2.dumps(compiled))
    tables = transformed_tables()
    unique = set().union(*(set(anf_monomials(tables[name])) for name in FEATURES))
    metrics = {
        "input_matrix_rows": list(INPUT_MATRIX),
        "input_offset": INPUT_OFFSET,
        "unique_monomials": len(unique),
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "classical_inputs_verified": 64,
        "relative_phase_classes": phase_classes,
        "verification": "All 64 y inputs mapped to exact feature bits with y and q17 restored; loader is intended for inverse pairing.",
        "note": "Loader-only direct-output ESOP diagnostic; not integrated into the logo oracle.",
    }
    (ARTIFACTS / "vector_input_basis_direct_target_loader_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
