"""Exhaustively verify a standalone rank-product phase term.

The target is (-1)**(a(x) & b(y)), where a and b are six-bit truth-table
integers encoded with bit zero as input value zero.  This deliberately does
not compare against the complete logo predicate.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from qiskit import qasm2


def verify(path, x_table, y_table=None):
    q = qasm2.loads(Path(path).read_text())
    assert 12 <= q.num_qubits <= 18 and set(q.count_ops()) <= {"u3", "cx"}
    n = 4096
    indices = np.arange(n, dtype=np.int32)[:, None]
    amp = np.ones((n, 1), complex)
    tol = 2e-15
    dropped = np.zeros(n)

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
        lost = np.sum(np.abs(sums) * ~keep, axis=1)
        count = keep.sum(1)
        new_width = int(count.max())
        dest = np.cumsum(keep, axis=1) - 1
        rows = np.broadcast_to(np.arange(n)[:, None], sums.shape)[keep]
        cols = dest[keep]
        result_idx = np.zeros((n, new_width), np.int32)
        result_amp = np.zeros((n, new_width), complex)
        result_idx[rows, cols] = outidx[keep]
        result_amp[rows, cols] = sums[keep]
        return result_idx, result_amp, lost

    for inst in q.data:
        vs = [q.find_bit(v).index for v in inst.qubits]
        if inst.operation.name == "cx":
            indices ^= (((indices >> vs[0]) & 1) << vs[1])
            continue
        theta, phi, lam = map(float, inst.operation.params)
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        bit = (indices >> vs[0]) & 1
        if abs(s) < tol:
            amp *= np.where(bit, np.exp(1j * (phi + lam)) * c, c)
        elif abs(c) < tol:
            amp *= np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            indices ^= 1 << vs[0]
        else:
            aa = amp * np.where(bit, np.exp(1j * (phi + lam)) * c, c)
            bb = amp * np.where(bit, -np.exp(1j * lam) * s, np.exp(1j * phi) * s)
            indices, amp, lost = compress(
                np.concatenate([indices, indices ^ (1 << vs[0])], axis=1),
                np.concatenate([aa, bb], axis=1),
            )
            dropped += lost
    pairs = x_table if y_table is None else [(x_table, y_table)]
    expected = np.array([
        -1 if sum(((a >> x) & 1) and ((b >> y) & 1) for a, b in pairs) & 1 else 1
        for y in range(64) for x in range(64)
    ])
    same = indices == np.arange(n)[:, None]
    diagonal = np.sum(amp * same, axis=1)
    phase = diagonal[0] / expected[0]
    phase /= abs(phase)
    residual = np.abs(amp * ~same)
    err = max(float(np.max(np.abs(diagonal - phase * expected))),
              float(np.max(residual, initial=0)))
    leak = float(np.max(np.abs(amp) * (indices >= 4096), initial=0))
    assert err < 1e-10, (err, leak)
    report = {
        "qasm": str(Path(path).resolve()),
        "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "basis_inputs_checked": n,
        "depth": q.depth(),
        "cx_count": q.count_ops().get("cx", 0),
        "width": q.num_qubits,
        "max_error": err,
        "ancilla_error": leak,
        "verification": "Exhaustive product-term phase verification",
    }
    out = Path(path).with_suffix(".product.exhaustive.json")
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 4 and not Path(sys.argv[2]).exists():
        verify(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    else:
        source = json.loads(Path(sys.argv[2]).read_text())
        indices = [int(value) for value in sys.argv[3:]]
        verify(sys.argv[1], [source[index] for index in indices])
