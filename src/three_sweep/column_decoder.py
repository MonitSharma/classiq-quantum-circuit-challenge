"""Reachable-code decoder for the transposed four-bit x-column loader."""

import json
from pathlib import Path

from qiskit import qasm2, transpile

from mcz import phase_cube
from search import esop
from .column_pair_loader import build as build_loader, column_codes, tables_from_codes


def append_column_phase(circuit, codes):
    for class_code, pair in enumerate(codes["class_masks"]):
        for x5, ymask in enumerate((pair["lower_mask"], pair["upper_mask"])):
            for yterm_mask, yterm_value in esop(ymask, 6):
                cube = [
                    bit + 7 if (yterm_value >> bit) & 1 else -(bit + 7)
                    for bit in range(6) if (yterm_mask >> bit) & 1
                ]
                for bit in range(4):
                    cube.append(
                        bit + 13 if (class_code >> bit) & 1
                        else -(bit + 13)
                    )
                cube.append(6 if x5 else -6)
                phase_cube(circuit, frozenset(cube), [])


def build(seed=19):
    codes = column_codes()
    loader = build_loader(tables_from_codes(codes), seed)
    circuit = loader.copy()
    append_column_phase(circuit, codes)
    circuit.compose(loader.inverse(), inplace=True)
    return transpile(circuit, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3,
                     seed_transpiler=seed)


def write(seed=19, path="artifacts/three_sweep/column_decoder.qasm"):
    circuit = build(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(qasm2.dumps(circuit))
    report = {"seed": seed, "qasm": str(path), "depth": circuit.depth(),
              "cx_count": circuit.count_ops().get("cx", 0),
              "width": circuit.num_qubits,
              "construction": "reachable 4-bit column-pair code decoder"}
    path.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    write()

