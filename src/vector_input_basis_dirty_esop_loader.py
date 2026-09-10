"""Benchmark an exact dirty-ancilla version of the shared input-basis ESOP loader.

The five output wires are dirty ancillas while q17 is the temporary monomial
target.  Qiskit's ``synth_mcx_n_dirty_i15`` is used directly because the
deprecated MCXVChain wrapper has a malformed three-control definition in the
installed Qiskit version.  This is a loader-only diagnostic, not the complete
logo oracle.
"""

from __future__ import annotations

import json
from collections import defaultdict

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis import synth_mcx_n_dirty_i15, synth_mcx_noaux_v24

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows
from vector_input_basis_search import INPUT_MATRIX, INPUT_OFFSET, invert, transform_y

Y = [6 + bit for bit in range(6)]
TARGET = 17
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


def append_dirty_mcx(q: QuantumCircuit, controls: list[int]) -> None:
    """Append an exact MCX using output wires as restored dirty ancillas."""
    degree = len(controls)
    if degree < 3:
        raise ValueError("dirty synthesis is only used for degree >= 3")
    if degree == 3:
        # Qiskit's dirty-i15 helper has a three-control special case with a
        # four-qubit circuit, i.e. no dirty ancilla slot.  Use its exact
        # no-auxiliary equivalent for that case.
        q.compose(synth_mcx_noaux_v24(degree),
                  qubits=controls + [TARGET], inplace=True)
        return
    ancillas = OUT[: degree - 2]
    dirty = synth_mcx_n_dirty_i15(degree, relative_phase=False)
    q.compose(dirty, qubits=controls + [TARGET] + ancillas, inplace=True)


def compute_monomial(q: QuantumCircuit, monomial: int) -> None:
    controls = [Y[bit] for bit in range(6) if monomial & (1 << bit)]
    if len(controls) == 0:
        q.x(TARGET)
    elif len(controls) == 1:
        q.cx(controls[0], TARGET)
    elif len(controls) == 2:
        q.rccx(controls[0], controls[1], TARGET)
    else:
        append_dirty_mcx(q, controls)


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


def main() -> None:
    raw = build()
    compiled = transpile(
        raw,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
    )
    path = ARTIFACTS / "vector_input_basis_dirty_esop_loader.qasm"
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
        "classical_inputs_verified": 0,
        "note": "Loader-only exact dirty-ancilla ESOP diagnostic; exhaustive QASM verification required before use.",
    }
    (ARTIFACTS / "vector_input_basis_dirty_esop_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
