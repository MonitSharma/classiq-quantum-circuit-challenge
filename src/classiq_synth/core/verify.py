"""Exhaustive sparse simulation and dense Aer verification for Classiq circuits."""

import json
import time
from pathlib import Path
from typing import Dict, Any, Union, Optional
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from classiq_synth.core.oracle import logo, get_target_array
from classiq_synth.core.circuit import load_circuit


def exhaustive_verify(
    path: Union[str, Path],
    max_width: int = 18,
    write_report: bool = True,
    tol: float = 2e-15,
) -> Dict[str, Any]:
    """Verify every clean-ancilla computational-basis input (all 4096 states) via sparse batched simulation.

    Args:
        path: Path to QASM file
        max_width: Maximum allowed qubits (challenge requires <= 18)
        write_report: If True, writes `<path>.exhaustive.json`
        tol: Numerical floating point tolerance

    Returns:
        Verification dictionary with metrics and errors
    """
    path = Path(path)
    q, source, sha256 = load_circuit(path)

    assert 12 <= q.num_qubits <= max_width <= 30, f"Qubits {q.num_qubits} out of range [12, {max_width}]"
    assert set(q.count_ops()) <= {"u3", "cx", "u"}, f"Unexpected gates: {set(q.count_ops())}"

    n = 4096
    indices = np.arange(n, dtype=np.int32)[:, None]
    amp = np.ones((n, 1), complex)
    dropped = np.zeros(n)
    peak = 1
    start = time.time()

    def compress(idx, a):
        order = np.argsort(idx, axis=1)
        idx = np.take_along_axis(idx, order, 1)
        a = np.take_along_axis(a, order, 1)
        first = np.ones(idx.shape, bool)
        first[:, 1:] = idx[:, 1:] != idx[:, :-1]
        group = np.cumsum(first, axis=1) - 1
        w = int(group[:, -1].max()) + 1
        target = (np.arange(n)[:, None] * w + group).ravel()
        sums = (
            np.bincount(target, weights=a.real.ravel(), minlength=n * w)
            + 1j * np.bincount(target, weights=a.imag.ravel(), minlength=n * w)
        ).reshape(n, w)
        outidx = np.zeros((n, w), np.int32)
        rr = np.broadcast_to(np.arange(n)[:, None], idx.shape)[first]
        cc = group[first]
        outidx[rr,cc] = idx[first]
        keep = np.abs(sums) > tol
        lost = np.sum(np.abs(sums) * ~keep, axis=1)
        count = keep.sum(1)
        width = int(count.max())
        dest = np.cumsum(keep, axis=1) - 1
        rr = np.broadcast_to(np.arange(n)[:, None], sums.shape)[keep]
        cc = dest[keep]
        oo = np.zeros((n, width), np.int32)
        aa = np.zeros((n, width), complex)
        oo[rr, cc] = outidx[keep]
        aa[rr, cc] = sums[keep]
        return oo, aa, lost

    for step, inst in enumerate(q.data):
        vs = [q.find_bit(v).index for v in inst.qubits]
        if inst.operation.name == "cx":
            indices ^= (((indices >> vs[0]) & 1) << vs[1])
        else:
            # u3 or u gate
            params = inst.operation.params
            theta, phi, lam = map(float, params[:3])
            c = np.cos(theta / 2)
            s = np.sin(theta / 2)
            bit = (indices >> vs[0]) & 1
            if abs(s) < tol:
                amp *= np.where(bit, np.exp(1j * (phi + lam)) * c, c)
                dropped += abs(s) * np.sqrt(np.sum(np.abs(amp) ** 2, axis=1))
            elif abs(c) < tol:
                amp *= np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices ^= 1 << vs[0]
                dropped += abs(c) * np.sqrt(np.sum(np.abs(amp) ** 2, axis=1))
            else:
                aa = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
                bb = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
                indices, amp, lost = compress(
                    np.concatenate([indices, indices ^ (1 << vs[0])], axis=1),
                    np.concatenate([aa, bb], axis=1),
                )
                dropped += lost
                peak = max(peak, amp.shape[1])
                if peak > 2048:
                    raise RuntimeError("Sparse support too large; use blocked dense verifier")

    expected = get_target_array()
    same = indices == np.arange(n)[:, None]
    diagonal = np.sum(amp * same, axis=1)
    phase = diagonal[0] / expected[0]
    phase /= abs(phase)
    residual = np.abs(amp * ~same)
    err = max(float(np.max(np.abs(diagonal - phase * expected))), float(np.max(residual, initial=0)))
    leak = float(np.max(np.abs(amp) * (indices >= 4096), initial=0))
    bound = float(dropped.max())

    assert err + bound < 1e-10, f"Verification failed: err={err}, bound={bound}"

    report = {
        "qasm": str(path.resolve()),
        "sha256": sha256,
        "basis_inputs_checked": n,
        "width": q.num_qubits,
        "depth": q.depth(),
        "cx_count": q.count_ops().get("cx", 0),
        "max_error": err,
        "ancilla_error": leak,
        "discarded_amplitude_bound": bound,
        "peak_sparse_support": peak,
        "elapsed_seconds": time.time() - start,
        "verification": (
            "Exhaustive numerical verification of all 4096 clean-ancilla basis inputs, "
            "with one shared global phase; by linearity covers arbitrary superpositions"
        ),
        "challenge_width_eligible": q.num_qubits <= 18,
    }
    if max_width > 18:
        report["diagnostic_width_limit"] = max_width

    if write_report:
        report_path = path.with_suffix(".exhaustive.json")
        report_path.write_text(json.dumps(report, indent=2))

    return report


def dense_verify(
    path: Union[str, Path],
    tests: int = 5,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Dense random-state verification using Qiskit Aer statevector simulator."""
    path = Path(path)
    q, source, sha256 = load_circuit(path)

    assert 12 <= q.num_qubits <= 18, f"Qubits {q.num_qubits} out of range [12, 18]"
    assert set(q.count_ops()) <= {"u3", "cx", "u"}, f"Unexpected gates: {set(q.count_ops())}"
    assert len(q.qregs) == 1 and q.qregs[0].name == "q", "Expected single qreg 'q'"

    rng = np.random.default_rng(20260908)
    backend = AerSimulator(method="statevector", max_parallel_threads=4)
    target = get_target_array()
    maxerr = leak = normerr = 0.0
    globalphase = None

    for k in range(tests):
        a = rng.normal(size=4096) + 1j * rng.normal(size=4096)
        a /= np.linalg.norm(a)
        initial = np.zeros(1 << q.num_qubits, complex)
        initial[:4096] = a
        qc = QuantumCircuit(q.num_qubits)
        qc.set_statevector(initial)
        qc.compose(q, inplace=True)
        qc.save_statevector()
        v = np.asarray(backend.run(qc).result().get_statevector())
        expect = initial.copy()
        expect[:4096] *= target
        overlap = np.vdot(expect, v)
        if globalphase is None:
            globalphase = overlap / abs(overlap)
        err = float(np.max(np.abs(v - globalphase * expect)))
        maxerr = max(maxerr, err)
        leak = max(leak, float(np.max(np.abs(v[4096:]), initial=0)))
        normerr = max(normerr, float(abs(np.vdot(v, v).real - 1)))

    assert maxerr < 1e-10 and leak < 1e-10 and normerr < 1e-10, (maxerr, leak, normerr)

    report = {
        "qasm": str(path.resolve()),
        "sha256": sha256,
        "width": q.num_qubits,
        "depth": q.depth(),
        "cx_count": q.count_ops().get("cx", 0),
        "random_dense_states": tests,
        "max_error": maxerr,
        "ancilla_error": leak,
        "normalization_error": normerr,
        "verification": "Dense random inputs supported on all 4096 coordinates; probabilistic numerical check",
    }
    if write_report:
        report_path = path.with_suffix(".verification.json")
        report_path.write_text(json.dumps(report, indent=2))

    return report
