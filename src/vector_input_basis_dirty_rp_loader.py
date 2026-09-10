"""Benchmark relative-phase dirty-ancilla synthesis for the shared y loader.

The relative phases are safe for this loader because each monomial gate is
computed, fanout is applied, and the same gate is uncomputed.  The generated
QASM is still checked by a basis-state simulation before it is treated as a
usable building block.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit_aer import AerSimulator
from qiskit.synthesis import synth_mcx_n_dirty_i15

import vector_input_basis_dirty_esop_loader as base
from vector_feature_analysis import ARTIFACTS, FEATURES, anf_monomials


def append_relative_phase_dirty_mcx(q, controls):
    degree = len(controls)
    if degree == 3:
        # The n-dirty helper has no dirty slot in its 3-control special case;
        # this exact no-auxiliary synthesis is the compatible fallback.
        q.compose(base.synth_mcx_noaux_v24(degree),
                  qubits=controls + [base.TARGET], inplace=True)
        return
    gate = synth_mcx_n_dirty_i15(degree, relative_phase=True)
    q.compose(gate,
              qubits=controls + [base.TARGET] + base.OUT[: degree - 2],
              inplace=True)


def build():
    original = base.append_dirty_mcx
    base.append_dirty_mcx = append_relative_phase_dirty_mcx
    try:
        return base.build()
    finally:
        base.append_dirty_mcx = original


def verify_compiled(compiled) -> None:
    """Check all 64 y inputs, including the dirty-output restoration."""
    simulator = AerSimulator(method="statevector")
    phases = []
    for row in base.truth_rows():
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
        if actual_y != row["y"] or actual_out != wanted or ((index >> 17) & 1):
            raise AssertionError((row["y"], actual_y, actual_out, wanted, index))
        phases.append(complex(state[index]))
    normalized = [phase / abs(phase) for phase in phases]
    if max(abs(phase - normalized[0]) for phase in normalized) > 1e-7:
        raise AssertionError("input-dependent relative phase")


def main() -> None:
    raw = build()
    compiled = transpile(raw, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False, optimization_level=3)
    verify_compiled(compiled)
    path = ARTIFACTS / "vector_input_basis_dirty_rp_loader.qasm"
    path.write_text(qasm2.dumps(compiled))
    tables = base.transformed_tables()
    unique = set().union(*(set(anf_monomials(tables[name])) for name in FEATURES))
    metrics = {
        "input_matrix_rows": list(base.INPUT_MATRIX),
        "input_offset": base.INPUT_OFFSET,
        "unique_monomials": len(unique),
        "depth": compiled.depth(),
        "cx": compiled.count_ops().get("cx", 0),
        "width": compiled.num_qubits,
        "basis": ["u3", "cx"],
        "qubits_initially_zero": False,
        "classical_inputs_verified": 64,
        "verification": "All 64 y basis states mapped exactly with zero q17 leakage and one shared global phase.",
        "note": "Loader-only relative-phase dirty-ancilla diagnostic; not integrated into the logo oracle.",
    }
    (ARTIFACTS / "vector_input_basis_dirty_rp_loader_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
