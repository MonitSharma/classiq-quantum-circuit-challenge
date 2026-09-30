"""Test the unified single-pass frame on all 4096 inputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from disjoint_hybrid_geometry import logo, logo_disjoint

def test_unified_disjoint_logic():
    for x in range(64):
        for y in range(64):
            sq, bp, d1, d2 = logo_disjoint(x, y)
            expected = logo(x, y)
            actual = sq or bp or d1 or d2
            assert actual == expected, f'Mismatch at {x}, {y}'

if __name__ == '__main__':
    test_unified_disjoint_logic()
    print('Unified disjoint logic verified successfully!')
