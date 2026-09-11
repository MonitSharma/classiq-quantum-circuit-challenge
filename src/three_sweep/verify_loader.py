"""Verify the loader's computational-basis action on all low-five-y inputs."""

import json
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

from .loader5 import compile_loader, tables_from_codebook


def verify(codebook_path="artifacts/three_sweep/codebook_deterministic.json", seed=0):
    tables = tables_from_codebook(codebook_path)
    circuit = compile_loader(tables, seed)
    max_leakage = 0.0
    max_bit_error = 0.0
    for z in range(32):
        code = sum(((tables[bit] >> z) & 1) << bit for bit in range(5))
        for b in range(2):
            initial = (z << 6) | (b << 11)
            state = Statevector.from_int(initial, dims=2 ** circuit.num_qubits)
            output = state.evolve(circuit).data
            index = int(np.argmax(np.abs(output)))
            amplitude = output[index]
            max_leakage = max(max_leakage, 1.0 - float(abs(amplitude) ** 2))
            expected = initial | (code << 12)
            max_bit_error = max(max_bit_error, float(index != expected))
    report = {
        "codebook": str(codebook_path),
        "seed": seed,
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "basis_inputs_checked": 64,
        "max_probability_leakage": max_leakage,
        "max_basis_index_error": max_bit_error,
        "verified": max_leakage < 1e-10 and max_bit_error == 0.0,
    }
    path = Path("artifacts/three_sweep/loader/loader5_verification.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["verified"]:
        raise AssertionError(report)
    return report


if __name__ == "__main__":
    verify()
