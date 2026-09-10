"""Compile the best sampled y-input basis into a shared exact ESOP loader."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows
from vector_input_basis_search import INPUT_MATRIX, INPUT_OFFSET, invert, transform_y

Y = [6 + bit for bit in range(6)]
TARGET = 17
OUT = [12 + bit for bit in range(5)]


def matrix_ops(matrix: tuple[int, ...]) -> list[tuple[int, int]]:
    """Return CNOT/SWAP row operations mapping identity to matrix."""
    rows = list(matrix)
    reduce_ops: list[tuple[int, int]] = []
    for bit in range(6):
        pivot = next(i for i in range(bit, 6) if rows[i] & (1 << bit))
        if pivot != bit:
            # Swap rows using three reversible row XORs.
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
    return {name: [original[name][transform_y(z, inv, INPUT_OFFSET)] for z in range(64)]
            for name in FEATURES}


def compute_monomial(q: QuantumCircuit, monomial: int) -> None:
    controls = [Y[bit] for bit in range(6) if monomial & (1 << bit)]
    if len(controls) == 0:
        q.x(TARGET)
    elif len(controls) == 1:
        q.cx(controls[0], TARGET)
    elif len(controls) == 2:
        q.rccx(controls[0], controls[1], TARGET)
    else:
        q.mcx(controls, TARGET, mode="noancilla")


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
        compute_monomial(q, monomial)
        for output in masks[monomial]:
            q.cx(TARGET, OUT[output])
        compute_monomial(q, monomial)
    for bit in range(6):
        if INPUT_OFFSET & (1 << bit):
            q.x(Y[bit])
    apply_matrix(q, invert(INPUT_MATRIX))
    return q


def replay_check(q: QuantumCircuit) -> None:
    for row in truth_rows():
        bits = [0] * 18
        for bit in range(6):
            bits[6 + bit] = (row["y"] >> bit) & 1
        for instruction, qargs, _ in q.data:
            name = instruction.name
            indexes = [qubit._index for qubit in qargs]
            if name == "mcx":
                controls, target = indexes[:-1], indexes[-1]
            elif name == "rccx":
                controls, target = indexes[:2], indexes[2]
            elif name == "cx":
                controls, target = indexes[:1], indexes[1]
            elif name == "x":
                controls, target = [], indexes[0]
            else:
                raise AssertionError(name)
            if all(bits[index] for index in controls):
                bits[target] ^= 1
        actual_y = sum(bits[6 + bit] << bit for bit in range(6))
        actual_out = [bits[12 + bit] for bit in range(5)]
        wanted = [row[name] for name in FEATURES]
        if actual_y != row["y"] or actual_out != wanted or bits[TARGET]:
            raise AssertionError((row["y"], actual_y, actual_out, wanted, bits[TARGET]))


def main() -> None:
    tables = transformed_tables()
    raw = build()
    replay_check(raw)
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3)
    path = ARTIFACTS / "vector_input_basis_esop_loader.qasm"
    path.write_text(qasm2.dumps(compiled))
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
        "note": "Loader-only input-basis ESOP fallback; not integrated into the logo oracle.",
    }
    (ARTIFACTS / "vector_input_basis_esop_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
