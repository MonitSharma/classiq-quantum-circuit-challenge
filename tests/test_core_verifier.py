"""Unit tests for classiq_synth core oracle, circuit analysis, and verification modules."""

import numpy as np
from classiq_synth.core.oracle import logo, get_target_array, MASK
from classiq_synth.core.circuit import get_circuit_metrics
from qiskit import QuantumCircuit


def test_oracle_predicate():
    """Check logo predicate on boundary and interior points."""
    # Point outside
    assert not logo(0, 0)
    assert not logo(63, 63)

    # Box 1 interior: 2<=x<=26 and 29<=y<=53
    assert logo(2, 29)
    assert logo(26, 53)
    assert logo(10, 40)

    # Box 2 interior: 26<=x<=49 and 39<=y<=43
    assert logo(30, 40)

    # Circle 1: (x-55)^2 + (y-41)^2 <= 42
    assert logo(55, 41)

    # Circle 2: (x-40)^2 + (y-19)^2 <= 72
    assert logo(40, 19)


def test_target_array_structure():
    """Check that get_target_array returns 4096 values of +1 and -1 matching MASK."""
    arr = get_target_array()
    assert len(arr) == 4096
    assert set(np.unique(arr)) == {-1, 1}
    assert MASK.shape == (64, 64)
    # Check consistency
    for y in range(64):
        for x in range(64):
            expected = -1 if MASK[y, x] else 1
            assert arr[y * 64 + x] == expected


def test_circuit_analysis_synthetic():
    """Verify get_circuit_metrics on a synthetic circuit."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    metrics = get_circuit_metrics(qc)

    assert metrics["width"] == 3
    assert metrics["cx_count"] == 2
    assert metrics["depth"] == 3
    assert metrics["total_gates"] == 3
