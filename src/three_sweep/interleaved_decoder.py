"""Explicit code-conditioned phase decoder for the verified 3+3 loader.

This is a measurement baseline for the genuinely interleaved direction. It
uses exact phase cubes on the loaded code bits, y5, and x ESOP terms; it is not
expected to be competitive, but unlike a Boolean class oracle it preserves the
reachable-code promise throughout the loader/phase/unloader sandwich.
"""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from mcz import phase_cube
from search import esop
from .half_row_loader import build as build_loader, half_codes, tables_from_codes


def append_code_conditioned_phase(circuit: QuantumCircuit, codes: dict):
    for half, feature_start in ((0, 12), (1, 15)):
        masks = codes["lower_masks"] if half == 0 else codes["upper_masks"]
        for class_code, xmask in enumerate(masks):
            for xterm_mask, xterm_value in esop(xmask, 6):
                cube = [
                    bit + 1 if (xterm_value >> bit) & 1 else -(bit + 1)
                    for bit in range(6) if (xterm_mask >> bit) & 1
                ]
                for bit in range(3):
                    cube.append(
                        feature_start + bit + 1
                        if (class_code >> bit) & 1
                        else -(feature_start + bit + 1)
                    )
                # Select the lower or upper bank using the retained y5 bit.
                cube.append(12 if half else -12)
                phase_cube(circuit, frozenset(cube), [])


def build(seed=0):
    codes = half_codes()
    tables = tables_from_codes(codes)
    loader = build_loader(tables, seed)
    circuit = loader.copy()
    append_code_conditioned_phase(circuit, codes)
    circuit.compose(loader.inverse(), inplace=True)
    return transpile(
        circuit,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=seed,
    )


def write(seed=0, path="artifacts/three_sweep/interleaved_decoder.qasm"):
    circuit = build(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    report = {
        "seed": seed,
        "qasm": str(path),
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "width": circuit.num_qubits,
        "phase_cubes": "exact ESOP terms conditioned on reachable 3+3 codes",
    }
    path.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    write()

