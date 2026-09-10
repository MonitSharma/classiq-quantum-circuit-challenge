"""Shared multi-output ANF/ESOP loader fallback.

Each unique ANF monomial is computed once into q17, fanned out to every
feature output whose ANF contains that monomial, and uncomputed.  Relative-
phase Toffolis are safe here because the compute and exact inverse surround
only CNOT fanout operations that do not touch the compute wires.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials, truth_rows

INPUTS = [6 + bit for bit in range(6)]
OUT = [12 + bit for bit in range(5)]
TARGET = 17


def compute_monomial(q: QuantumCircuit, monomial: int) -> None:
    controls = [INPUTS[bit] for bit in range(6) if monomial & (1 << bit)]
    degree = len(controls)
    if degree == 0:
        q.x(TARGET)
    elif degree == 1:
        q.cx(controls[0], TARGET)
    elif degree == 2:
        q.rccx(controls[0], controls[1], TARGET)
    else:
        # q15/q16 are output wires, so they cannot be used as clean v-chain
        # scratch.  Use the exact no-ancilla construction for every degree-3+
        # monomial; this is slower but preserves the shared-output invariant.
        q.mcx(controls, TARGET, mode="noancilla")


def feature_tables() -> dict[str, list[int]]:
    rows = truth_rows()
    return {name: anf_monomials([row[name] for row in rows]) for name in FEATURES}


def build() -> QuantumCircuit:
    tables = feature_tables()
    masks: defaultdict[int, list[int]] = defaultdict(list)
    for output, monomials in enumerate(tables.values()):
        for monomial in monomials:
            masks[monomial].append(output)
    q = QuantumCircuit(18)
    for monomial in sorted(masks):
        compute_monomial(q, monomial)
        for output in masks[monomial]:
            q.cx(TARGET, OUT[output])
        compute_monomial(q, monomial)
    return q


def expected_outputs() -> list[dict[str, int]]:
    return truth_rows()


def verify_classical(raw: QuantumCircuit) -> None:
    for row in expected_outputs():
        bits = [0] * 18
        for bit in range(6):
            bits[6 + bit] = (row["y"] >> bit) & 1
        for instruction, qargs, _ in raw.data:
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
                raise AssertionError(f"unexpected raw gate {name}")
            if all(bits[index] for index in controls):
                bits[target] ^= 1
        actual = [bits[12 + index] for index in range(5)]
        wanted = [row[name] for name in FEATURES]
        # q15/q16 are outputs, so only q17 is required clean here.
        if actual != wanted or bits[17] != 0:
            raise AssertionError((row["y"], actual, wanted, bits[17]))


def main() -> None:
    tables = feature_tables()
    raw = build()
    verify_classical(raw)
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3)
    qasm_path = ARTIFACTS / "vector_esop_loader.qasm"
    qasm_path.write_text(qasm2.dumps(compiled))
    distribution = defaultdict(int)
    for monomial, outputs in ((m, [name for name in FEATURES if m in tables[name]])
                              for m in sorted(set().union(*tables.values()))):
        distribution[len(outputs)] += 1
    metrics = {
        "kind": "shared_vector_anf_esop",
        "outputs": list(FEATURES),
        "unique_monomials": len(set().union(*tables.values())),
        "output_mask_histogram": dict(sorted(distribution.items())),
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "loader_truth_rows": len(expected_outputs()),
        "note": "Loader-only shared ESOP fallback; not integrated into the logo oracle.",
    }
    (ARTIFACTS / "vector_esop_loader_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
