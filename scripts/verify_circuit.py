#!/usr/bin/env python3
"""Exhaustive, dependency-light verification of a logo phase-oracle circuit.

The oracle acts on 18 qubits: x on q0-q5, y on q6-q11 (little endian) and six
ancillas q12-q17 that must start and end in |0>.  For every one of the 4096
computational-basis inputs |x, y, 0> the circuit must return
(-1)^logo(x, y) |x, y, 0> up to one global phase shared by all inputs.
Linearity then covers every superposition of clean-ancilla inputs.

The simulation is exact up to floating point: each input is propagated as a
sparse vector (the oracle never spreads a basis state over more than a few
dozen amplitudes), so all 4096 inputs are checked in about a second with numpy
alone.

Usage:
    python scripts/verify_circuit.py artifacts/115/conditional_loader_115_cx567.qasm
    python scripts/verify_circuit.py --json report.json circuit1.qasm circuit2.qasm
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

N_INPUTS = 4096
TOL = 1e-12


def logo(x: int, y: int) -> bool:
    """The challenge predicate (identical to src/classiq_synth/core/oracle.py)."""
    return bool(
        (2 <= x <= 26 and 29 <= y <= 53)
        or (26 <= x <= 49 and 39 <= y <= 43)
        or ((x - 55) ** 2 + (y - 41) ** 2 <= 42)
        or ((x - 40) ** 2 + (y - 19) ** 2 <= 72)
    )


def target_phases() -> np.ndarray:
    """(-1)^logo for input index i = x + 64 y."""
    return np.array([-1.0 if logo(i % 64, i // 64) else 1.0 for i in range(N_INPUTS)])


def _angle(expr: str) -> float:
    return float(eval(expr.replace("pi", "math.pi"), {"math": math}))


def parse_qasm(path: str | Path):
    """Parse an OpenQASM 2 file restricted to u3/u/cx gates."""
    text = Path(path).read_text()
    n = int(re.search(r"qreg\s+\w+\[(\d+)\]", text).group(1))
    gates = []
    body = re.sub(r"//[^\n]*", "", text)
    for stmt in (s.strip() for s in body.split(";")):
        if not stmt or stmt.startswith(("OPENQASM", "include", "qreg", "creg", "barrier")):
            continue
        qubits = [int(q) for q in re.findall(r"\[(\d+)\]", stmt)]
        if stmt.startswith("cx"):
            gates.append(("cx", qubits[0], qubits[1], None))
        elif stmt.startswith(("u3", "u(")):
            params = [_angle(p) for p in stmt[stmt.index("(") + 1: stmt.index(")")].split(",")]
            gates.append(("u3", qubits[-1], None, params[:3]))
        else:
            raise ValueError(f"unsupported gate: {stmt!r}")
    return n, gates, text


def depth_and_counts(n: int, gates) -> dict:
    front = [0] * n
    for g in gates:
        wires = (g[1], g[2]) if g[0] == "cx" else (g[1],)
        t = max(front[w] for w in wires) + 1
        for w in wires:
            front[w] = t
    return {
        "depth": max(front) if gates else 0,
        "cx": sum(g[0] == "cx" for g in gates),
        "u3": sum(g[0] == "u3" for g in gates),
    }


def _compress(idx: np.ndarray, amp: np.ndarray, tol: float):
    """Merge equal basis indices per row and drop amplitudes below tol."""
    rows = idx.shape[0]
    order = np.argsort(idx, axis=1)
    idx = np.take_along_axis(idx, order, 1)
    amp = np.take_along_axis(amp, order, 1)
    first = np.ones(idx.shape, bool)
    first[:, 1:] = idx[:, 1:] != idx[:, :-1]
    group = np.cumsum(first, axis=1) - 1
    width = int(group[:, -1].max()) + 1
    flat = (np.arange(rows)[:, None] * width + group).ravel()
    sums = (np.bincount(flat, amp.real.ravel(), rows * width)
            + 1j * np.bincount(flat, amp.imag.ravel(), rows * width)).reshape(rows, width)
    uniq = np.zeros((rows, width), np.int64)
    r = np.broadcast_to(np.arange(rows)[:, None], idx.shape)[first]
    uniq[r, group[first]] = idx[first]
    keep = np.abs(sums) > tol
    dropped = np.sum(np.abs(sums) * ~keep, axis=1)
    new_w = int(keep.sum(1).max())
    dest = np.cumsum(keep, axis=1) - 1
    r = np.broadcast_to(np.arange(rows)[:, None], sums.shape)[keep]
    out_i = np.zeros((rows, new_w), np.int64)
    out_a = np.zeros((rows, new_w), complex)
    out_i[r, dest[keep]] = uniq[keep]
    out_a[r, dest[keep]] = sums[keep]
    return out_i, out_a, dropped


def simulate_basis_inputs(gates, tol: float = 1e-15):
    """Propagate all 4096 clean-ancilla basis inputs; returns (indices, amplitudes, dropped, peak)."""
    idx = np.arange(N_INPUTS, dtype=np.int64)[:, None]
    amp = np.ones((N_INPUTS, 1), complex)
    dropped = np.zeros(N_INPUTS)
    peak = 1
    for kind, a, b, params in gates:
        if kind == "cx":
            idx = idx ^ (((idx >> a) & 1) << b)
            continue
        theta, phi, lam = params
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        bit = (idx >> a) & 1
        if abs(s) < tol:                       # diagonal
            amp = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            dropped += abs(s)
        elif abs(c) < tol:                     # anti-diagonal
            amp = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            idx = idx ^ (1 << a)
            dropped += abs(c)
        else:                                  # splits every basis state in two
            stay = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            flip = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            idx, amp, lost = _compress(np.concatenate([idx, idx ^ (1 << a)], 1),
                                       np.concatenate([stay, flip], 1), tol)
            dropped += lost
            peak = max(peak, amp.shape[1])
    return idx, amp, dropped, peak


def verify(path: str | Path) -> dict:
    """Verify one circuit; returns a report with per-input errors under 'per_input_error'."""
    t0 = time.time()
    n, gates, text = parse_qasm(path)
    info = depth_and_counts(n, gates)
    if n > 18:
        raise ValueError(f"{path}: {n} qubits exceeds the 18-qubit limit")
    idx, amp, dropped, peak = simulate_basis_inputs(gates)
    expected = target_phases()
    home = idx == np.arange(N_INPUTS)[:, None]
    diag = np.sum(amp * home, axis=1)
    phase = diag[0] / expected[0]
    phase /= abs(phase)
    off = np.sqrt(np.sum(np.abs(amp * ~home) ** 2, axis=1))      # weight outside |x,y,0>
    per_input = np.maximum(np.abs(diag - phase * expected), off)
    leak = float(np.max(np.abs(amp) * (idx >= N_INPUTS), initial=0.0))
    report = {
        "circuit": str(path),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "width": n,
        **info,
        "basis_inputs_checked": N_INPUTS,
        "max_error": float(per_input.max()),
        "ancilla_leakage": leak,
        "discarded_amplitude_bound": float(dropped.max()),
        "peak_sparse_support": int(peak),
        "passed": bool(per_input.max() + dropped.max() < 1e-10),
        "seconds": round(time.time() - t0, 3),
        "per_input_error": per_input,
    }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuits", nargs="+", help="OpenQASM 2 files (u3/cx)")
    ap.add_argument("--json", help="write the reports (without per-input arrays) to this file")
    args = ap.parse_args(argv)
    reports, ok = [], True
    for c in args.circuits:
        r = verify(c)
        ok &= r["passed"]
        print(f"{'PASS' if r['passed'] else 'FAIL'}  depth {r['depth']:>4}  cx {r['cx']:>4}  u3 {r['u3']:>4}  "
              f"width {r['width']}  max error {r['max_error']:.2e}  ({r['seconds']} s)  {c}")
        reports.append({k: v for k, v in r.items() if k != "per_input_error"})
    if args.json:
        Path(args.json).write_text(json.dumps(reports, indent=2) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
