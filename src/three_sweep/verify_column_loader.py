"""Verify the transposed four-bit loader on all 64 x inputs."""

import json
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

from .column_pair_loader import column_codes, compile_loader, tables_from_codes


def verify(seed=19):
    codes = column_codes()
    circuit = compile_loader(tables_from_codes(codes), seed)
    max_leakage = 0.0
    max_index_error = 0
    for z in range(32):
        for x5 in range(2):
            code = int(codes["z_to_code"][str(z)])
            initial = z | (x5 << 5)
            output = Statevector.from_int(initial, dims=2 ** 18).evolve(circuit).data
            index = int(np.argmax(np.abs(output)))
            amplitude = output[index]
            expected = initial | (code << 12)
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
    path = Path("artifacts/three_sweep/column_pair_loader/verification.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["verified"]:
        raise AssertionError(report)
    return report


if __name__ == "__main__":
    verify()

