"""Re-basis the coordinate wires before the lookup to rebalance the loader frames.

The loader's cost is not the number of Walsh terms but how they fall into the
twenty-four (host, frame) slots of `structured_ucry`.  Which slot a term lands in
is decided by its mask's coordinates in the *wire* basis, so a CNOT circuit
applied to the six coordinate wires before the lookup -- and undone by the
loader's own inverse at the far end of the oracle -- relabels every mask and can
rebalance the frames.

Crucially it changes nothing else: the loaded code values are untouched, so the
class cells, the kernel truth table and the kernel's phase lift are all
identical.  The only price is the depth of the CNOT circuit, paid twice.

`loader_floor` in `post196_frame_balance` already minimises over the twenty
axis-aligned high/low splits; a general basis explores the full `GL(6,2)` orbit
of those splits, which is far larger.  One basis vector is pinned to the raw
parity so the kernel still finds it on its own wire.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.synthesis.linear import synth_cnot_count_full_pmh

from post196_frame_balance import loader_floor

RAW_WIRE = 5


def invert(basis):
    """Coordinate map: coords[m] has bit j set iff basis[j] is used to build m."""
    piv = {}
    for j, row in enumerate(basis):
        value, comb = row, 1 << j
        while value:
            top = value.bit_length() - 1
            if top in piv:
                a, b = piv[top]
                value ^= a
                comb ^= b
            else:
                piv[top] = (value, comb)
                break
        else:
            return None
    coords = []
    for m in range(64):
        value, out = m, 0
        while value:
            top = value.bit_length() - 1
            if top not in piv:
                return None
            a, b = piv[top]
            value ^= a
            out ^= b
        coords.append(out)
    return coords


def rebased_tables(tables, coords):
    """Angle tables whose Walsh mask `m` is moved to position `coords[m]`."""
    from post196_frame_balance import H6
    spectrum = tables @ H6.T
    moved = np.zeros_like(spectrum)
    for m in range(64):
        moved[:, coords[m]] = spectrum[:, m]
    return moved @ H6.T * 64.0 / 64.0, moved


def basis_circuit_depth(basis):
    """Depth of the CNOT circuit that puts `basis[j]` on wire j."""
    matrix = np.array([[(basis[j] >> i) & 1 for i in range(6)] for j in range(6)], dtype=bool)
    best = None
    for section in (1, 2, 3):
        q = synth_cnot_count_full_pmh(matrix, section_size=section)
        if best is None or (q.depth(), q.size()) < (best.depth(), best.size()):
            best = q
    return best.depth(), best


def floor_of(spectrum_moved):
    """Frame floor of a spectrum already expressed in the new wire basis."""
    from post196_frame_balance import H6
    tables = moved_to_tables(spectrum_moved)
    return loader_floor(tables)


def moved_to_tables(moved):
    from post196_frame_balance import H6
    # inverse Walsh: tables = moved @ H6 * 64  (H6 is the forward transform / 64)
    return moved @ np.linalg.inv(H6)


def search(tables, steps, seed, raw_mask):
    """Anneal over wire bases; one wire is pinned to the raw parity."""
    rng = random.Random(seed)
    basis = [1 << j for j in range(6)]
    basis[RAW_WIRE] = raw_mask
    if invert(basis) is None:
        basis = [1 << j for j in range(6)]
        basis[RAW_WIRE] = raw_mask
        for j in range(6):
            if j != RAW_WIRE and invert(basis) is None:
                basis[j] ^= 1 << RAW_WIRE
    coords = invert(basis)
    assert coords is not None

    def cost(b):
        c = invert(b)
        if c is None:
            return None
        _, moved = rebased_tables(tables, c)
        floor, high = loader_floor(moved_to_tables(moved))
        depth, _ = basis_circuit_depth(b)
        return floor + depth, floor, depth, high

    state = cost(basis)
    best, best_basis, best_state = state[0], list(basis), state
    cur = state[0]
    for step in range(steps):
        j = rng.choice([k for k in range(6) if k != RAW_WIRE])
        k = rng.choice([k for k in range(6) if k != j])
        trial = list(basis)
        trial[j] ^= basis[k]
        got = cost(trial)
        if got is None:
            continue
        temp = 0.5 + 5.0 * (1 - (step % 800) / 800)
        if got[0] <= cur or rng.random() < math.exp((cur - got[0]) / temp):
            basis, cur = trial, got[0]
            if got[0] < best:
                best, best_basis, best_state = got[0], list(trial), got
    return best, best_basis, best_state
