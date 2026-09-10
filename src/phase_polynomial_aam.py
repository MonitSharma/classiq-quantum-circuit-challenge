"""Bounded GraySynth diagnostic for the exact 12-variable logo phase."""

import json
from fractions import Fraction
from pathlib import Path
import math

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis import synth_cnot_phase_aam

from search import MASK


def angle(value):
    value = Fraction(value)
    if value == 0:
        return "0"
    if value.denominator == 1:
        return str(value.numerator) + "*pi"
    return f"{value.numerator}*pi/{value.denominator}"


def main():
    n = 12
    coefficients = []
    for parity in range(1 << n):
        total = 0
        for z in range(1 << n):
            x, y = z & 63, z >> 6
            total += (1 if MASK[y, x] else 0) * (-1 if (parity & z).bit_count() & 1 else 1)
        coefficients.append(Fraction(total, 1 << n))
    parities = list(range(1, 1 << n))
    columns = [[(parity >> row) & 1 for parity in parities] for row in range(n)]
    circuit = synth_cnot_phase_aam(columns,
                                   [float(coefficients[p]) * math.pi for p in parities],
                                   section_size=2)
    circuit.global_phase = float(coefficients[0]) * math.pi
    out = transpile(circuit, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3)
    metrics = {"walsh_terms": sum(c != 0 for c in coefficients),
               "depth": out.depth(), "cx_count": out.count_ops().get("cx", 0),
               "width": out.num_qubits}
    Path("artifacts/phase_polynomial_aam.qasm").write_text(qasm2.dumps(out))
    Path("artifacts/phase_polynomial_aam_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
