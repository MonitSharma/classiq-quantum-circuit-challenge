"""Verify the 3+3 half-row loader on every clean-ancilla input."""

import json
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

from .half_row_loader import compile_loader, half_codes, tables_from_codes


def verify(seed=0):
    codes = half_codes()
    tables = tables_from_codes(codes)
    circuit = compile_loader(tables, seed)
    max_leakage = 0.0
    max_index_error = 0
    for z in range(32):
        for y5 in range(2):
            lower = int(codes["z_to_lower_code"][str(z)])
            upper = int(codes["z_to_upper_code"][str(z)])
            # Both banks are loaded simultaneously; y5 selects which bank the
            # eventual middle phase will use.
            expected_code = lower | (upper << 3)
            initial = (z << 6) | (y5 << 11)
            output = Statevector.from_int(initial, dims=2 ** 18).evolve(circuit).data
            index = int(np.argmax(np.abs(output)))
            amplitude = output[index]
            expected = initial | (expected_code << 12)
            max_leakage = max(max_leakage, 1.0 - float(abs(amplitude) ** 2))
            max_index_error = max(max_index_error, int(index != expected))
    report = {
        "seed": seed,
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "basis_inputs_checked": 64,
        "max_probability_leakage": max_leakage,
        "max_basis_index_error": max_index_error,
        "verified": max_leakage < 1e-10 and max_index_error == 0,
    }
    path = Path("artifacts/three_sweep/half_row_loader/verification.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["verified"]:
        raise AssertionError(report)
    return report


if __name__ == "__main__":
    verify()
