import json
import math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, transpile, qasm2
from qiskit.quantum_info import Statevector

from disjoint_hybrid_geometry import logo, D1_CORNERS, D2_CORNERS
from search import esop, truth
from distributed_frame_search import native

def tree_mcxr(qc: QuantumCircuit, controls: list[int], negs: list[int], target: int, scratch: list[int]) -> None:
    if negs: qc.x(negs)
    n = len(controls)
    if n == 0:
        qc.x(target)
    elif n == 1:
        qc.cx(controls[0], target)
    elif n == 2:
        qc.rccx(controls[0], controls[1], target)
    elif n == 3:
        s0 = scratch[0]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s0, controls[2], target)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 4:
        s0, s1 = scratch[0], scratch[1]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(s0, s1, target)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 5:
        s0, s1, s2 = scratch[0], scratch[1], scratch[2]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(s0, s1, s2)
        qc.rccx(s2, controls[4], target)
        qc.rccx(scratch[0], scratch[1], scratch[2])
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 6:
        s0, s1, s2, s3 = scratch[0], scratch[1], scratch[2], scratch[3]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s0, s1, s3)
        qc.rccx(s3, s2, target)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 7:
        s0, s1, s2, s3 = scratch[:4]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s2, controls[6], s0)
        qc.rccx(s3, s0, target)
        qc.rccx(s2, controls[6], s0)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 8:
        s0, s1, s2, s3 = scratch[:4]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s2, controls[6], s0)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s0, controls[7], s2)
        qc.rccx(s3, s2, target)
        qc.rccx(s0, controls[7], s2)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s2, controls[6], s0)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    elif n == 9:
        s0, s1, s2, s3 = scratch[:4]
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(controls[6], controls[7], s0)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(s2, s0, s1)
        qc.rccx(controls[6], controls[7], s0)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(s3, s1, s0)
        qc.rccx(s0, controls[8], target)
        qc.rccx(s3, s1, s0)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(controls[6], controls[7], s0)
        qc.rccx(s2, s0, s1)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[6], controls[7], s0)
        qc.rccx(controls[0], controls[1], s0)
        qc.rccx(s0, s1, s3)
        qc.rccx(controls[4], controls[5], s2)
        qc.rccx(controls[2], controls[3], s1)
        qc.rccx(controls[0], controls[1], s0)
    if negs: qc.x(negs)

def build_box(qc: QuantumCircuit, x_range, y_range):
    tx = truth(x_range)
    ty = truth(y_range)
    cubes_x = list(esop(tx, 6))
    cubes_y = list(esop(ty, 6))
    
    # Compute X on q12 using scratch [14, 15, 16, 17]
    for m, v in cubes_x:
        cs = [j for j in range(6) if (m >> j) & 1]
        negs = [j for j in range(6) if ((m >> j) & 1) and not ((v >> j) & 1)]
        tree_mcxr(qc, cs, negs, 12, [14, 15, 16, 17])
        
    # Compute Y on q13 using scratch [14, 15, 16, 17]
    for m, v in cubes_y:
        cs = [6 + j for j in range(6) if (m >> j) & 1]
        negs = [6 + j for j in range(6) if ((m >> j) & 1) and not ((v >> j) & 1)]
        tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
        
    qc.cz(12, 13)
    
    # Invert Y
    for m, v in reversed(cubes_y):
        cs = [6 + j for j in range(6) if (m >> j) & 1]
        negs = [6 + j for j in range(6) if ((m >> j) & 1) and not ((v >> j) & 1)]
        tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
        
    # Invert X
    for m, v in reversed(cubes_x):
        cs = [j for j in range(6) if (m >> j) & 1]
        negs = [j for j in range(6) if ((m >> j) & 1) and not ((v >> j) & 1)]
        tree_mcxr(qc, cs, negs, 12, [14, 15, 16, 17])

def build_corners_1(qc: QuantumCircuit):
    c1_8bit = 0
    for x in range(49, 62):
        for y in range(35, 48):
            if (abs(x - 55), abs(y - 41)) in D1_CORNERS:
                xl = x - 48
                yl = y - 32
                idx = xl | (yl << 4)
                c1_8bit |= 1 << idx

    cubes_c1 = list(esop(c1_8bit, 8))
    
    # Compute guard onto q12: q12 = q5 * q4 * q11 * ~q10
    tree_mcxr(qc, [5, 4, 11, 10], [10], 12, [14, 15, 16, 17])
    
    bit_wires = [0, 1, 2, 3, 6, 7, 8, 9]
    for m, v in cubes_c1:
        cs = [12] + [bit_wires[i] for i in range(8) if (m >> i) & 1]
        negs = [bit_wires[i] for i in range(8) if ((m >> i) & 1) and not ((v >> i) & 1)]
        tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
        qc.z(13)
        tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
        
    # Uncompute guard
    tree_mcxr(qc, [5, 4, 11, 10], [10], 12, [14, 15, 16, 17])

def build_corners_2(qc: QuantumCircuit):
    bit_wires = [0, 1, 2, 3, 6, 7, 8, 9]
    for x4 in (0, 1):
        for y4 in (0, 1):
            t = 0
            for x in range(32, 49):
                if ((x >> 4) & 1) != x4: continue
                for y in range(11, 28):
                    if ((y >> 4) & 1) != y4: continue
                    if (abs(x - 40), abs(y - 19)) in D2_CORNERS:
                        xl = x & 15
                        yl = y & 15
                        t |= 1 << (xl | (yl << 4))
            if t:
                # Compute quadrant guard into q12: q5=1, q11=0, q4==x4, q10==y4
                negs_guard = [11]
                if x4 == 0: negs_guard.append(4)
                if y4 == 0: negs_guard.append(10)
                tree_mcxr(qc, [5, 11, 4, 10], negs_guard, 12, [14, 15, 16, 17])
                
                cubes = list(esop(t, 8))
                for m, v in cubes:
                    cs = [12] + [bit_wires[i] for i in range(8) if (m >> i) & 1]
                    negs = [bit_wires[i] for i in range(8) if ((m >> i) & 1) and not ((v >> i) & 1)]
                    tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
                    qc.z(13)
                    tree_mcxr(qc, cs, negs, 13, [14, 15, 16, 17])
                    
                # Uncompute quadrant guard
                tree_mcxr(qc, [5, 11, 4, 10], negs_guard, 12, [14, 15, 16, 17])

def assemble_full_circuit():
    qc = QuantumCircuit(18)
    # 1. Square
    build_box(qc, range(2, 27), range(29, 54))
    # 2. Bar'
    build_box(qc, range(27, 49), range(39, 44))
    # 3. Box 1 (D1 box)
    build_box(qc, range(49, 62), range(35, 48))
    # 4. Box 2 (D2 box)
    build_box(qc, range(32, 49), range(11, 28))
    # 5. Corners 1
    build_corners_1(qc)
    # 6. Corners 2
    build_corners_2(qc)
    return qc

if __name__ == '__main__':
    print('Assembling full hybrid circuit...')
    qc = assemble_full_circuit()
    print('Circuit assembled. Transpiling with native()...')
    compiled = native(qc)
    cx_count = compiled.count_ops().get('cx', 0)
    print(f'Compiled metrics: Depth = {compiled.depth()}, CX = {cx_count}, Width = {compiled.num_qubits}')
    outpath = Path('scratch/test_hybrid.qasm')
    outpath.write_text(qasm2.dumps(compiled))
    print(f'Wrote to {outpath}')
