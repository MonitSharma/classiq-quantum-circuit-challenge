"""Checks for the level/comparator oracle decomposition and its emitters."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

import level_oracle as lo


def test_identity_exact():
    assert lo.check_identity() == 0


def test_kernel_matches_staircase():
    ytrip = (0b110010, 0b111100, 0b100100)
    xtrip = (0b100100, 0b111000, 0b001010)
    alpha, _ = lo.code_of(ytrip, lo.LEVEL["u1"])
    beta, _ = lo.code_of(xtrip, lo.LEVEL["v1"])
    terms = lo.kernel_terms(alpha, beta)
    for u in range(6):
        for v in range(6):
            w = alpha[u] | (beta[v] << 3)
            val = sum(1 for t in terms if (t & ~w) == 0) & 1
            assert val == (1 if u + v >= 6 else 0)


def _simulate_encoder(hist, targets):
    """Run emit_encoder on nine wires and read the resulting permutation."""
    wires = list(range(9))
    qc = QuantumCircuit(9)
    regs = lo.emit_encoder(qc, hist, wires, targets)
    # emit_encoder returns the symbolic register contents; check them against a
    # direct simulation of the permutation on all 64 inputs.
    op = Operator(qc).data
    for value in range(64):
        col = value  # ancillas start at |0>, so the basis index is just `value`
        out = np.argmax(np.abs(op[:, col]))
        for slot in (6, 7, 8):
            bit = (int(out) >> slot) & 1
            assert bit == ((regs[slot] >> value) & 1), (value, slot)
    return regs


def test_emit_encoder_replays_a_network():
    # y3 AND y4 into register 6, then a plain copy of y5 into register 7,
    # and the AND of those two into register 8.
    VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]
    hist = [(VARS[3], VARS[4], 6), (VARS[5], VARS[3], 7)]
    targets = [VARS[3] & VARS[4], VARS[5] & VARS[3], 0]
    regs = _simulate_encoder(hist, targets)
    assert regs[6] == VARS[3] & VARS[4]
    assert regs[7] == VARS[5] & VARS[3]


def test_emit_encoder_handles_negated_operands():
    FULL = lo.FULL
    VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]
    hist = [(VARS[0] ^ FULL, VARS[1], 6), (VARS[2] ^ VARS[3], VARS[4] ^ FULL, 7)]
    targets = [(VARS[0] ^ FULL) & VARS[1], (VARS[2] ^ VARS[3]) & (VARS[4] ^ FULL), 0]
    _simulate_encoder(hist, targets)
