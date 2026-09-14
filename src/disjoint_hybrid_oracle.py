"""Disjoint Geometric Hybrid Quantum Oracle with Corner Pruning for Classiq Challenge.

Standalone U3/CX oracle on 18 qubits (12 coordinates q[0:11], 6 clean ancillas q[12:18]).
Pairwise disjoint geometric decomposition:
    logo(x, y) = Square(x, y) XOR Bar'(x, y) XOR Disk(x, y)
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from disjoint_hybrid_geometry import (
    logo,
    logo_disjoint,
    D1_CORNERS,
    D2_CORNERS,
)
from distributed_frame_search import native


def tree_mcxr(qc: QuantumCircuit, controls: list[int], negs: list[int], target: int, scratch: list[int]) -> None:
    """Relative-phase multi-controlled X gate using an explicit binary tree of RCCX gates.
    
    Safe for use when enclosed by exact unitary inverse uncompute around diagonal phase action.
    """
    if negs:
        qc.x(negs)
    n = len(controls)
    if n == 0:
        qc.x(target)
    elif n == 1:
        qc.cx(controls[0], target)
    elif n == 2:
        qc.rccx(controls[0], controls[1], target)
    elif n == 3:
        qc.rccx(controls[0], controls[1], scratch[0])
        qc.rccx(scratch[0], controls[2], target)
        qc.rccx(controls[0], controls[1], scratch[0])
    elif n == 4:
        qc.rccx(controls[0], controls[1], scratch[0])
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(scratch[0], scratch[1], target)
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(controls[0], controls[1], scratch[0])
    elif n == 5:
        qc.rccx(controls[0], controls[1], scratch[0])
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(scratch[0], scratch[1], scratch[2])
        qc.rccx(scratch[2], controls[4], target)
        qc.rccx(scratch[0], scratch[1], scratch[2])
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(controls[0], controls[1], scratch[0])
    elif n == 6:
        qc.rccx(controls[0], controls[1], scratch[0])
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(controls[4], controls[5], scratch[2])
        qc.rccx(scratch[0], scratch[1], scratch[3])
        qc.rccx(scratch[3], scratch[2], target)
        qc.rccx(scratch[0], scratch[1], scratch[3])
        qc.rccx(controls[4], controls[5], scratch[2])
        qc.rccx(controls[2], controls[3], scratch[1])
        qc.rccx(controls[0], controls[1], scratch[0])
    else:
        pre = QuantumCircuit(18)
        pre.rccx(controls[0], controls[1], scratch[0])
        for i, c in enumerate(controls[2:-1]):
            pre.rccx(scratch[i], c, scratch[i+1])
        qc.compose(pre, inplace=True)
        qc.rccx(scratch[len(controls)-3], controls[-1], target)
        qc.compose(pre.inverse(), inplace=True)
    if negs:
        qc.x(negs)


def build_square_block() -> QuantumCircuit:
    """Phase oracle for Square: x in [2..26] and y in [29..53]."""
    qc = QuantumCircuit(18)
    # ESOP cubes for x in [2..26] on q[0:6], target q12:
    tree_mcxr(qc, [5], [5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [2, 3, 4, 5], [5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [2, 5], 12, [14, 15, 16, 17])

    # ESOP cubes for y in [29..53] on q[6:12], target q13:
    tree_mcxr(qc, [11], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [9, 10, 11], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [7, 8, 10, 11], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [7, 8, 9, 10], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [6, 7, 8, 9, 10, 11], [7, 11], 13, [14, 15, 16, 17])

    # Phase kickback on Square:
    qc.cz(12, 13)

    # Invert indicators to restore q12, q13:
    tree_mcxr(qc, [6, 7, 8, 9, 10, 11], [7, 11], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [7, 8, 9, 10], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [7, 8, 10, 11], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [9, 10, 11], [], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [11], [], 13, [14, 15, 16, 17])

    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [2, 5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [2, 3, 4, 5], [5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [5], [5], 12, [14, 15, 16, 17])

    return qc


def build_bar_block() -> QuantumCircuit:
    """Phase oracle for Bar': x in [27..48] and y in [39..43]."""
    qc = QuantumCircuit(18)
    # ESOP cubes for x in [27..48] on q[0:6], target q12:
    tree_mcxr(qc, [4, 5], [4], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [0, 1, 2, 3], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [2, 5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [2, 3, 4, 5], [5], 12, [14, 15, 16, 17])

    # ESOP cubes for y in [39..43] on q[6:12], target q13:
    tree_mcxr(qc, [8, 9, 10, 11], [8, 10], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [6, 7, 8, 9, 10, 11], [9, 10], 13, [14, 15, 16, 17])

    # Phase kickback on Bar':
    qc.cz(12, 13)

    # Invert indicators:
    tree_mcxr(qc, [6, 7, 8, 9, 10, 11], [9, 10], 13, [14, 15, 16, 17])
    tree_mcxr(qc, [8, 9, 10, 11], [8, 10], 13, [14, 15, 16, 17])

    tree_mcxr(qc, [2, 3, 4, 5], [5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [2, 5], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [0, 1, 2, 3, 4, 5], [0, 1, 2, 3], 12, [14, 15, 16, 17])
    tree_mcxr(qc, [4, 5], [4], 12, [14, 15, 16, 17])

    return qc


def build_disk_block() -> QuantumCircuit:
    """Phase oracle for Disk C XOR D using the verified parallel prefix comparator."""
    from post196_prefix_comparator import build as build_comp
    score, comp_qc, seed, kdepth = build_comp(enabled=True)

    disk = QuantumCircuit(18)

    # Step 1: Reversible x reflection and fold around shared center (q11 is y5):
    for i in range(5):
        disk.cx(11, i)
    disk.x(3)
    disk.cx(3, 4)
    for i in range(4):
        disk.cx(4, i)

    # Step 2: Radius loader from y (q6..q11) into q12..q15:
    # 30 non-zero rows in y. We load the 4-bit radius into q12..q15 using tree_mcxr.
    # We use q16, q17 as scratch.
    def r_table(y: int) -> int:
        y5 = (y >> 5) & 1
        if y5:
            dy = abs(y - 41)
            r2 = 42 - dy**2
            return int(r2**0.5) if r2 >= 0 else 0
        else:
            dy = abs(y - 19)
            r2 = 72 - dy**2
            return int(r2**0.5) if r2 >= 0 else 0

    from search import esop
    radii = [r_table(y) for y in range(64)]
    for b in range(4):
        tb = sum(((radii[y] >> b) & 1) << y for y in range(64))
        for mask, val in esop(tb, 6):
            cs = [6 + i for i in range(6) if (mask >> i) & 1]
            negs = [6 + i for i in range(6) if ((mask >> i) & 1) and not ((val >> i) & 1)]
            tree_mcxr(disk, cs, negs, 12 + b, [16, 17])

    # Step 3: Apply the verified 36-depth parallel prefix comparator:
    # Comparator wires:
    # [0..3]: r (q12..q15)
    # [4..7]: v (q0..q3)
    # [8]: s (q4)
    # [9]: flag (q5, x5=1)
    # [10, 11]: helpers (q16, q17)
    comp_wires = [12, 13, 14, 15, 0, 1, 2, 3, 4, 5, 16, 17]
    disk.compose(comp_qc, comp_wires, inplace=True)

    # Step 4: Uncompute radius on q12..q15:
    for b in reversed(range(4)):
        tb = sum(((radii[y] >> b) & 1) << y for y in range(64))
        for mask, val in reversed(esop(tb, 6)):
            cs = [6 + i for i in range(6) if (mask >> i) & 1]
            negs = [6 + i for i in range(6) if ((mask >> i) & 1) and not ((val >> i) & 1)]
            tree_mcxr(disk, cs, negs, 12 + b, [16, 17])

    # Step 5: Invert x reflection and fold:
    for i in reversed(range(4)):
        disk.cx(4, i)
    disk.cx(3, 4)
    disk.x(3)
    for i in reversed(range(5)):
        disk.cx(11, i)

    return disk


def build_oracle(outdir: Path = None) -> tuple[QuantumCircuit, Path]:
    """Assemble and transpile the complete disjoint hybrid oracle."""
    full = QuantumCircuit(18)
    full.compose(build_square_block(), inplace=True)
    full.compose(build_bar_block(), inplace=True)
    full.compose(build_disk_block(), inplace=True)

    compiled = native(full)

    if outdir is not None:
        outdir.mkdir(parents=True, exist_ok=True)
        qasm_path = outdir / 'disjoint_hybrid_sub100.qasm'
        text = qasm2.dumps(compiled)
        qasm_path.write_text(text)
        manifest = {
            'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'depth': compiled.depth(),
            'cx': compiled.count_ops().get('cx', 0),
            'width': compiled.num_qubits,
        }
        (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        return compiled, qasm_path

    return compiled, None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', type=Path, default=Path('artifacts/sub100_candidate'))
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()

    qc, path = build_oracle(args.outdir)
    cx_count = qc.count_ops().get('cx', 0)
    print(f'Compiled Oracle: depth={qc.depth()}, CX={cx_count}, width={qc.num_qubits}')

    if args.verify and path is not None:
        from exhaustive_verify import exhaustive
        exhaustive(path)
