"""Nested shell-sharing decoder for the 3+3 row codes."""

import json
from pathlib import Path

from qiskit import qasm2, transpile

from mcz import phase_cube
from search import esop, truth
from .half_row_loader import build as build_loader, half_codes, tables_from_codes


def append_shell(circuit, xmask, allowed_codes, feature_start, y5):
    for xterm_mask, xterm_value in esop(xmask, 6):
        xcube = [
            bit + 1 if (xterm_value >> bit) & 1 else -(bit + 1)
            for bit in range(6) if (xterm_mask >> bit) & 1
        ]
        code_table = truth(allowed_codes)
        for cmask, cvalue in esop(code_table, 3):
            cube = list(xcube)
            cube += [
                feature_start + bit + 1
                if (cvalue >> bit) & 1 else -(feature_start + bit + 1)
                for bit in range(3) if (cmask >> bit) & 1
            ]
            cube.append(12 if y5 else -12)
            phase_cube(circuit, frozenset(cube), [])


def append_nested_phase(circuit, codes):
    lower_labels = {int(k): int(v) for k, v in codes["lower_labels"].items()}
    upper_labels = {int(k): int(v) for k, v in codes["upper_labels"].items()}
    # Lower half: five nested disk masks, plus the separate square class 6.
    previous = 0
    for level in range(1, 6):
        shell = codes["lower_masks"][level] ^ previous
        append_shell(circuit, shell,
                     [lower_labels[i] for i in range(level, 6)], 12, 0)
        previous = codes["lower_masks"][level]
    append_shell(circuit, codes["lower_masks"][6], [lower_labels[6]], 12, 0)

    # Upper half: square base plus four nested upper-disk extensions.
    previous = codes["upper_masks"][0]
    append_shell(circuit, previous, [upper_labels[i] for i in range(0, 5)], 15, 1)
    for level in range(1, 5):
        shell = codes["upper_masks"][level] ^ previous
        append_shell(circuit, shell,
                     [upper_labels[i] for i in range(level, 5)], 15, 1)
        previous = codes["upper_masks"][level]


def build(seed=0, lower_labels=None, upper_labels=None):
    codes = half_codes(lower_labels=lower_labels, upper_labels=upper_labels)
    loader = build_loader(tables_from_codes(codes), seed)
    circuit = loader.copy()
    append_nested_phase(circuit, codes)
    circuit.compose(loader.inverse(), inplace=True)
    return transpile(
        circuit,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=seed,
    )


def write(seed=0, path="artifacts/three_sweep/shell_decoder.qasm"):
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
        "construction": "nested x-shells conditioned on reachable code ranges",
    }
    path.with_suffix(".metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    write()
