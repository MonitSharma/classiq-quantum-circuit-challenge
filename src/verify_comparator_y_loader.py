"""Basis-action check for the serialized y code loader."""

import json
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit_aer import AerSimulator

from comparator_oracle_structure import Y_B, Y_M


def main(path):
    q = qasm2.loads(Path(path).read_text())
    backend = AerSimulator(method="statevector", max_parallel_threads=4)
    worst = 0.0; bad = []
    for y in range(64):
        qc = QuantumCircuit(q.num_qubits)
        for bit in range(6):
            if y >> bit & 1: qc.x(6 + bit)
        qc.compose(q, inplace=True); qc.save_statevector()
        state = np.asarray(backend.run(qc).result().get_statevector())
        index = int(np.argmax(np.abs(state)))
        amp = state[index]
        expected_code = (Y_B[y] & 1) | ((Y_M[y] & 7) << 1)
        expected = (y << 6) | (expected_code << 12)
        if index != expected or abs(abs(amp) - 1) > 1e-10:
            bad.append({"y": y, "actual_index": index, "expected_index": expected,
                        "amplitude": [float(amp.real), float(amp.imag)]})
        worst = max(worst, float(abs(abs(amp) - 1)))
    report = {"qasm": str(Path(path).resolve()), "basis_inputs_checked": 64,
              "mismatches": len(bad), "max_amplitude_error": worst,
              "counterexamples": bad,
              "verification": "basis action: y preserved, code in q12..q15, q0..q5 and q16..q17 zero"}
    out = Path(path).with_suffix(".basis.json")
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
