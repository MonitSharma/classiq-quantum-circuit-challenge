"""Finite-size Lupanov-style branch pilot.

This is the literal q=1 instance of the paper's rich-ancilla decomposition.
It is intentionally a bounded feasibility experiment, not a claim that the
asymptotic construction has useful constants at n=8 and m=10.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from conditionally_clean_cofactor import cofactor_table, residual_coordinates


SELECTOR = (("x", 5), ("y", 3), ("y", 4), ("y", 5))
ASSIGNMENT = 3


def build_q1():
    coordinates = residual_coordinates(SELECTOR)
    table = cofactor_table(SELECTOR, ASSIGNMENT, coordinates)
    q = QuantumCircuit(18)
    prefix = list(range(7))
    suffix = 7
    flag = 8
    function_value = 9
    mcx_ancillas = list(range(10, 15))
    target = 17

    for prefix_value in range(1 << len(prefix)):
        negative = [wire for i, wire in enumerate(prefix) if not (prefix_value >> i) & 1]
        for wire in negative:
            q.x(wire)
        q.mcx(prefix, flag, ancilla_qubits=mcx_ancillas, mode="v-chain")
        for wire in negative:
            q.x(wire)

        f0 = int(table[prefix_value])
        f1 = int(table[prefix_value | (1 << 7)])
        if f0:
            q.x(function_value)
        if f0 ^ f1:
            q.cx(suffix, function_value)
        q.ccx(flag, function_value, target)
        if f0 ^ f1:
            q.cx(suffix, function_value)
        if f0:
            q.x(function_value)

        for wire in negative:
            q.x(wire)
        q.mcx(prefix, flag, ancilla_qubits=mcx_ancillas, mode="v-chain")
        for wire in negative:
            q.x(wire)

    # Convert the Boolean output oracle into the competition's phase oracle.
    # The compute/uncompute wrapper is required because q17 must finish clean.
    phase = QuantumCircuit(18)
    phase.compose(q, inplace=True)
    phase.z(target)
    phase.compose(q.inverse(), inplace=True)
    out = transpile(phase, basis_gates=["u3", "cx"], qubits_initially_zero=False,
                    optimization_level=3, seed_transpiler=0)
    return out, table


def verify(path, table):
    """Sparse exhaustive check for eight input wires and ten clean ancillas."""
    from qiskit import qasm2

    q = qasm2.loads(Path(path).read_text())
    n = 1 << 8
    indices = np.arange(n, dtype=np.int32)[:, None]
    amp = np.ones((n, 1), complex)
    tol = 2e-15

    def compress(idx, values):
        order = np.argsort(idx, axis=1)
        idx = np.take_along_axis(idx, order, axis=1)
        values = np.take_along_axis(values, order, axis=1)
        first = np.ones(idx.shape, bool)
        first[:, 1:] = idx[:, 1:] != idx[:, :-1]
        group = np.cumsum(first, axis=1) - 1
        width = int(group[:, -1].max()) + 1
        target = (np.arange(n)[:, None] * width + group).ravel()
        sums = (np.bincount(target, weights=values.real.ravel(), minlength=n * width)
                + 1j * np.bincount(target, weights=values.imag.ravel(), minlength=n * width)).reshape(n, width)
        outidx = np.zeros((n, width), np.int32)
        rows = np.broadcast_to(np.arange(n)[:, None], idx.shape)[first]
        cols = group[first]
        outidx[rows, cols] = idx[first]
        keep = np.abs(sums) > tol
        count = keep.sum(1)
        outwidth = int(count.max())
        dest = np.cumsum(keep, axis=1) - 1
        rows = np.broadcast_to(np.arange(n)[:, None], sums.shape)[keep]
        cols = dest[keep]
        newidx = np.zeros((n, outwidth), np.int32)
        newamp = np.zeros((n, outwidth), complex)
        newidx[rows, cols] = outidx[keep]
        newamp[rows, cols] = sums[keep]
        return newidx, newamp

    for inst in q.data:
        wires = [q.find_bit(v).index for v in inst.qubits]
        if inst.operation.name == "cx":
            indices ^= (((indices >> wires[0]) & 1) << wires[1])
        else:
            theta, phi, lam = map(float, inst.operation.params)
            c = np.cos(theta / 2)
            s = np.sin(theta / 2)
            bit = (indices >> wires[0]) & 1
            if abs(s) < tol:
                amp *= np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            elif abs(c) < tol:
                amp *= np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices ^= 1 << wires[0]
            else:
                aa = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
                bb = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices, amp = compress(
                    np.concatenate([indices, indices ^ (1 << wires[0])], axis=1),
                    np.concatenate([aa, bb], axis=1),
                )

    expected = np.array([-1 if table[i] else 1 for i in range(n)])
    same = indices == np.arange(n)[:, None]
    diagonal = np.sum(amp * same, axis=1)
    phase = diagonal[0] / expected[0]
    phase /= abs(phase)
    error = max(float(np.max(np.abs(diagonal - phase * expected))),
                float(np.max(np.abs(amp) * ~same, initial=0)))
    leakage = float(np.max(np.abs(amp) * (indices >= n), initial=0))
    if error >= 1e-10 or leakage >= 1e-10:
        raise AssertionError((error, leakage))
    return {"max_error": error, "ancilla_error": leakage, "inputs_checked": n}


def main():
    circuit, table = build_q1()
    path = Path("artifacts/lupanov_branch_q1.qasm")
    path.write_text(qasm2.dumps(circuit))
    report = {
        "q": 1,
        "p": 7,
        "workspace": 10,
        "depth": circuit.depth(),
        "cx_count": circuit.count_ops().get("cx", 0),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verification": verify(path, table),
    }
    Path("artifacts/lupanov_branch_q1.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
